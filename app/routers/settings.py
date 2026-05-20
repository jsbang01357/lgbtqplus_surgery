from fastapi import APIRouter, Request, Depends

from app.models import PasswordUpdateRequest
from app.api_deps import _json, get_current_user
from app.ai import GEMINI_MODEL, format_krw_cost, USD_TO_KRW_RATE, _load_gemini_usage_logs, _parse_usage_time, _sum_usage_costs, _entry_cost_usd
from app.security import update_account_password
from app.access_logger import get_access_logs, clear_access_logs

router = APIRouter()

@router.get('/api/usage/summary')
async def usage_summary(request: Request):

    try:
        multiplier = float(request.query_params.get("multiplier", 1.0))
        exchange_rate = float(
            request.query_params.get("exchange_rate", USD_TO_KRW_RATE)
        )
    except ValueError:
        multiplier = 1.0
        exchange_rate = USD_TO_KRW_RATE

    try:
        logs = _load_gemini_usage_logs()
        today_krw, month_krw, today_usd, month_usd = _sum_usage_costs(logs)

        base_multiplier = 10.0 * multiplier
        today_adjusted = today_usd * exchange_rate * base_multiplier
        month_adjusted = month_usd * exchange_rate * base_multiplier

        return _json(
            {
                "model": GEMINI_MODEL,
                "today_cost": today_adjusted,
                "month_cost": month_adjusted,
                "today_cost_usd": today_usd,
                "month_cost_usd": month_usd,
                "today_cost_label": format_krw_cost(today_adjusted),
                "month_cost_label": format_krw_cost(month_adjusted),
                "request_count": len(logs),
            }
        )
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)

@router.post('/api/settings/password')
async def settings_password_update(request: Request, payload: PasswordUpdateRequest, _: bool = Depends(get_current_user)):
    new_password = payload.new_password.strip()
    if len(new_password) < 4:
        return _json({"error": "비밀번호는 4자리 이상이어야 합니다."}, status_code=400)


    try:
        update_account_password(new_password)
        return _json({"ok": True})
    except Exception as exc:
        return _json({"error": f"비밀번호 변경 실패: {exc}"}, status_code=500)

@router.get('/api/settings/access-logs')
async def settings_access_logs(request: Request, _: bool = Depends(get_current_user)):
    try:
        logs = get_access_logs()[:50]
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)
    ip_counts: dict[str, int] = {}
    for entry in logs:
        ip = str(entry.get("ip") or "Unknown")
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    top_ips = [
        {"ip": ip, "count": count}
        for ip, count in sorted(
            ip_counts.items(), key=lambda item: item[1], reverse=True
        )[:5]
    ]
    return _json(
        {
            "total": len(logs),
            "unique_ips": len(ip_counts),
            "latest": logs[0] if logs else {},
            "top_ips": top_ips,
            "logs": logs[:12],
        }
    )

@router.post('/api/settings/access-logs/clear')
async def settings_access_logs_clear(request: Request, _: bool = Depends(get_current_user)):
    try:
        clear_access_logs()
        return _json({"ok": True})
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)

@router.get('/api/settings/gemini-usage')
async def settings_gemini_usage(request: Request, _: bool = Depends(get_current_user)):
    try:
        multiplier = float(request.query_params.get("multiplier", 1.0))
        exchange_rate = float(
            request.query_params.get("exchange_rate", USD_TO_KRW_RATE)
        )
    except ValueError:
        multiplier = 1.0
        exchange_rate = USD_TO_KRW_RATE

    try:
        logs = _load_gemini_usage_logs()
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=500)

    today_krw, month_krw, today_usd, month_usd = _sum_usage_costs(logs)
    total_tokens = sum(int(entry.get("total_tokens") or 0) for entry in logs)
    input_tokens = sum(int(entry.get("input_tokens") or 0) for entry in logs)
    output_tokens = sum(int(entry.get("output_tokens") or 0) for entry in logs)
    daily: dict[str, dict] = {}
    for entry in logs:
        entry_time = _parse_usage_time(entry.get("time", ""))
        day = entry_time.strftime("%Y-%m-%d") if entry_time else "unknown"
        row = daily.setdefault(
            day, {"date": day, "requests": 0, "tokens": 0, "cost_usd": 0.0}
        )
        row["requests"] += 1
        row["tokens"] += int(entry.get("total_tokens") or 0)

        row["cost_usd"] += _entry_cost_usd(entry)

    daily_rows = sorted(daily.values(), key=lambda row: row["date"], reverse=True)[:10]
    base_multiplier = 10.0 * multiplier
    for row in daily_rows:
        adjusted_cost = row["cost_usd"] * exchange_rate * base_multiplier
        row["cost_label"] = format_krw_cost(adjusted_cost)

    today_adjusted = today_usd * exchange_rate * base_multiplier
    month_adjusted = month_usd * exchange_rate * base_multiplier

    return _json(
        {
            "model": GEMINI_MODEL,
            "request_count": len(logs),
            "today_cost_label": format_krw_cost(today_adjusted),
            "month_cost_label": format_krw_cost(month_adjusted),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "daily": daily_rows,
        }
    )
