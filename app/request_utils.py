def get_client_ip(headers, fallback: str | None = None) -> str:
    forwarded_for = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For") or ""
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first

    for key in ("cf-connecting-ip", "CF-Connecting-IP", "remote-addr", "Remote-Addr"):
        value = headers.get(key, "")
        if value:
            return str(value).strip()

    return fallback or "Unknown"
