import base64
import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from cryptography.hazmat.primitives.hashes import SHA256

from app.core_utils import get_now
from app.gcs_helper import get_bucket

PASSKEY_CREDENTIALS_BLOB = "auth/passkeys.json"
PASSKEY_CHALLENGE_BYTES = 32
PASSKEY_SESSION_BYTES = 32
PASSKEY_CHALLENGE_TTL_SECONDS = 300
PASSKEY_SESSION_TTL_SECONDS = 60 * 60 * 12


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _now_iso() -> str:
    return get_now().isoformat()


def _iso_to_ts(value: str) -> float:
    return get_now().fromisoformat(value).timestamp()


def _load_store() -> dict[str, Any]:
    bucket = get_bucket()
    blob = bucket.blob(PASSKEY_CREDENTIALS_BLOB)
    if not blob.exists():
        return {"credentials": [], "challenges": {}, "sessions": {}}
    try:
        data = json.loads(blob.download_as_text(encoding="utf-8"))
    except Exception:
        return {"credentials": [], "challenges": {}, "sessions": {}}
    if not isinstance(data, dict):
        return {"credentials": [], "challenges": {}, "sessions": {}}
    data.setdefault("credentials", [])
    data.setdefault("challenges", {})
    data.setdefault("sessions", {})
    return data


def _save_store(data: dict[str, Any]):
    bucket = get_bucket()
    blob = bucket.blob(PASSKEY_CREDENTIALS_BLOB)
    blob.upload_from_string(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )


def _cleanup_expired(data: dict[str, Any]):
    now_ts = get_now().timestamp()
    data["challenges"] = {
        key: item
        for key, item in data.get("challenges", {}).items()
        if _iso_to_ts(item.get("expires_at", _now_iso())) > now_ts
    }
    data["sessions"] = {
        key: item
        for key, item in data.get("sessions", {}).items()
        if _iso_to_ts(item.get("expires_at", _now_iso())) > now_ts
    }


def _new_challenge(data: dict[str, Any], purpose: str, email: str) -> str:
    challenge = b64url_encode(secrets.token_bytes(PASSKEY_CHALLENGE_BYTES))
    expires_at = (get_now() + timedelta(seconds=PASSKEY_CHALLENGE_TTL_SECONDS)).isoformat()
    data["challenges"][challenge] = {
        "purpose": purpose,
        "email": email,
        "expires_at": expires_at,
        "created_at": _now_iso(),
    }
    return challenge


def _consume_challenge(data: dict[str, Any], challenge: str, purpose: str, email: str):
    item = data.get("challenges", {}).pop(challenge, None)
    if not item:
        raise ValueError("challenge가 없거나 만료되었습니다.")
    if item.get("purpose") != purpose:
        raise ValueError("challenge 목적이 일치하지 않습니다.")
    if item.get("email") != email:
        raise ValueError("challenge 사용자 정보가 일치하지 않습니다.")
    if _iso_to_ts(item.get("expires_at", _now_iso())) <= get_now().timestamp():
        raise ValueError("challenge가 만료되었습니다.")


class CborReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self):
        if self.pos >= len(self.data):
            raise ValueError("CBOR 데이터가 너무 짧습니다.")
        initial = self.data[self.pos]
        self.pos += 1
        major = initial >> 5
        addl = initial & 0x1F
        value = self._read_len(addl)
        if major == 0:
            return value
        if major == 1:
            return -1 - value
        if major == 2:
            payload = self.data[self.pos : self.pos + value]
            self.pos += value
            return payload
        if major == 3:
            payload = self.data[self.pos : self.pos + value]
            self.pos += value
            return payload.decode("utf-8")
        if major == 4:
            return [self.read() for _ in range(value)]
        if major == 5:
            return {self.read(): self.read() for _ in range(value)}
        if major == 7:
            if addl == 20:
                return False
            if addl == 21:
                return True
            if addl == 22:
                return None
        raise ValueError(f"지원하지 않는 CBOR major type: {major}")

    def _read_len(self, addl: int) -> int:
        if addl < 24:
            return addl
        if addl == 24:
            size = 1
        elif addl == 25:
            size = 2
        elif addl == 26:
            size = 4
        elif addl == 27:
            size = 8
        else:
            raise ValueError("indefinite CBOR length는 지원하지 않습니다.")
        payload = self.data[self.pos : self.pos + size]
        self.pos += size
        return int.from_bytes(payload, "big")


def _parse_auth_data(auth_data: bytes) -> dict[str, Any]:
    if len(auth_data) < 37:
        raise ValueError("authenticatorData가 너무 짧습니다.")
    flags = auth_data[32]
    sign_count = int.from_bytes(auth_data[33:37], "big")
    parsed = {"flags": flags, "sign_count": sign_count}
    attested_credential_data = bool(flags & 0x40)
    if not attested_credential_data:
        return parsed
    offset = 37
    aaguid = auth_data[offset : offset + 16]
    offset += 16
    credential_id_len = int.from_bytes(auth_data[offset : offset + 2], "big")
    offset += 2
    credential_id = auth_data[offset : offset + credential_id_len]
    offset += credential_id_len
    cose_key = CborReader(auth_data[offset:]).read()
    parsed.update(
        {
            "aaguid": b64url_encode(aaguid),
            "credential_id": b64url_encode(credential_id),
            "cose_key": cose_key,
        }
    )
    return parsed


def _public_key_from_cose(cose_key: dict):
    if cose_key.get(1) != 2 or cose_key.get(3) != -7 or cose_key.get(-1) != 1:
        raise ValueError("ES256 passkey만 지원합니다.")
    x = int.from_bytes(cose_key[-2], "big")
    y = int.from_bytes(cose_key[-3], "big")
    numbers = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())
    return numbers.public_key()


def _client_data(payload: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    client_data_json = b64url_decode(payload["response"]["clientDataJSON"])
    return json.loads(client_data_json.decode("utf-8")), client_data_json


from app.config import get_config

# ... inside _rp_id, _rp_name, _origin ...
def _rp_id() -> str:
    return get_config("PASSKEY_RP_ID", "cloud.jisong.dev")


def _rp_name() -> str:
    return get_config("PASSKEY_RP_NAME", "Jisong Cloud")


def _origin() -> str:
    return get_config("PASSKEY_ORIGIN", f"https://{_rp_id()}")


def registration_options(email: str) -> dict[str, Any]:
    data = _load_store()
    _cleanup_expired(data)
    challenge = _new_challenge(data, "registration", email)
    user_id = b64url_encode(hashlib.sha256(email.encode("utf-8")).digest()[:16])
    excluded = [
        {"type": "public-key", "id": item["credential_id"]}
        for item in data.get("credentials", [])
        if item.get("email") == email
    ]
    _save_store(data)
    return {
        "publicKey": {
            "challenge": challenge,
            "rp": {"name": _rp_name(), "id": _rp_id()},
            "user": {"id": user_id, "name": email, "displayName": email},
            "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
            "timeout": PASSKEY_CHALLENGE_TTL_SECONDS * 1000,
            "attestation": "none",
            "authenticatorSelection": {
                "residentKey": "preferred",
                "userVerification": "required",
            },
            "excludeCredentials": excluded,
        }
    }


def verify_registration(email: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = _load_store()
    _cleanup_expired(data)
    client_data, _ = _client_data(payload)
    challenge = client_data.get("challenge")
    if client_data.get("type") != "webauthn.create":
        raise ValueError("등록 응답 type이 올바르지 않습니다.")
    if client_data.get("origin") != _origin():
        raise ValueError("등록 origin이 일치하지 않습니다.")
    _consume_challenge(data, challenge, "registration", email)

    attestation = CborReader(b64url_decode(payload["response"]["attestationObject"])).read()
    auth_data = _parse_auth_data(attestation["authData"])
    credential_id = auth_data["credential_id"]
    cose_key = auth_data["cose_key"]
    if any(item.get("credential_id") == credential_id for item in data["credentials"]):
        raise ValueError("이미 등록된 passkey입니다.")
    data["credentials"].append(
        {
            "email": email,
            "credential_id": credential_id,
            "public_key_cose": b64url_encode(json.dumps(_jsonable_cose(cose_key)).encode("utf-8")),
            "sign_count": auth_data["sign_count"],
            "created_at": _now_iso(),
            "last_used_at": "",
        }
    )
    _save_store(data)
    return {"credential_id": credential_id}


def _jsonable_cose(cose_key: dict) -> dict[str, Any]:
    return {str(key): b64url_encode(value) if isinstance(value, bytes) else value for key, value in cose_key.items()}


def _restore_cose(raw: str) -> dict:
    data = json.loads(b64url_decode(raw).decode("utf-8"))
    restored = {}
    for key, value in data.items():
        int_key = int(key)
        if int_key in {-2, -3}:
            restored[int_key] = b64url_decode(value)
        else:
            restored[int_key] = value
    return restored


def authentication_options(email: str) -> dict[str, Any]:
    data = _load_store()
    _cleanup_expired(data)
    credentials = [item for item in data["credentials"] if item.get("email") == email]
    if not credentials:
        raise ValueError("등록된 passkey가 없습니다.")
    challenge = _new_challenge(data, "authentication", email)
    _save_store(data)
    return {
        "publicKey": {
            "challenge": challenge,
            "rpId": _rp_id(),
            "timeout": PASSKEY_CHALLENGE_TTL_SECONDS * 1000,
            "userVerification": "required",
            "allowCredentials": [
                {"type": "public-key", "id": item["credential_id"]}
                for item in credentials
            ],
        }
    }


def verify_authentication(email: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = _load_store()
    _cleanup_expired(data)
    client_data, client_data_json = _client_data(payload)
    challenge = client_data.get("challenge")
    if client_data.get("type") != "webauthn.get":
        raise ValueError("로그인 응답 type이 올바르지 않습니다.")
    if client_data.get("origin") != _origin():
        raise ValueError("로그인 origin이 일치하지 않습니다.")
    _consume_challenge(data, challenge, "authentication", email)

    credential_id = payload.get("id") or payload.get("rawId")
    credential = next(
        (
            item
            for item in data["credentials"]
            if item.get("email") == email and item.get("credential_id") == credential_id
        ),
        None,
    )
    if not credential:
        raise ValueError("등록된 credential이 아닙니다.")
    authenticator_data = b64url_decode(payload["response"]["authenticatorData"])
    signature = b64url_decode(payload["response"]["signature"])
    signed_data = authenticator_data + hashlib.sha256(client_data_json).digest()
    public_key = _public_key_from_cose(_restore_cose(credential["public_key_cose"]))
    try:
        public_key.verify(signature, signed_data, ec.ECDSA(SHA256()))
    except InvalidSignature:
        try:
            r, s = decode_dss_signature(signature)
            der_signature = encode_dss_signature(r, s)
            public_key.verify(der_signature, signed_data, ec.ECDSA(SHA256()))
        except Exception as exc:
            raise ValueError("passkey 서명이 올바르지 않습니다.") from exc
    auth_data = _parse_auth_data(authenticator_data)
    credential["sign_count"] = max(int(credential.get("sign_count") or 0), auth_data["sign_count"])
    credential["last_used_at"] = _now_iso()
    token = b64url_encode(secrets.token_bytes(PASSKEY_SESSION_BYTES))
    data["sessions"][token] = {
        "email": email,
        "created_at": _now_iso(),
        "expires_at": (get_now() + timedelta(seconds=PASSKEY_SESSION_TTL_SECONDS)).isoformat(),
    }
    _save_store(data)
    return {"token": token, "expires_in": PASSKEY_SESSION_TTL_SECONDS}


def verify_session(token: str, email: str = "") -> bool:
    if not token:
        return False
    data = _load_store()
    _cleanup_expired(data)
    session = data.get("sessions", {}).get(token)
    _save_store(data)
    if not session:
        return False
    if email and session.get("email") != email:
        return False
    return True
