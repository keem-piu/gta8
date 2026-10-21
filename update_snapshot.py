"""Update a public Pages snapshot with official Kick API, only inside GitHub Actions.

No app credentials are written to the snapshot or served to a browser.
Without credentials the site still loads but does NOT invent live statuses.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "streamers.json"
CONFIG = ROOT / "channels.json"
FIELDS = ("title", "category", "profileImage", "avatarCached", "thumbnail", "lastStream", "lastVideoAt", "lastStreamSource")


def read_json(path: Path):
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def initial(name: str) -> dict:
    return {"username": name, "status": "unknown", "title": f"{name} Kanalı", "category": "GTA",
            "lastStream": None, "lastVideoAt": None, "lastStreamSource": "none",
            "startTime": None, "profileImage": None, "avatarCached": None, "thumbnail": None, "viewers": None, "checkedAt": None}


def merge_records(names, previous, fresh):
    """Never upgrade a failed API response to 'offline' or claim stale status is current."""
    old_index = {x.get("username"): x for x in previous if isinstance(x, dict)}
    new_index = {x.get("username"): x for x in fresh if isinstance(x, dict)}
    merged = []
    for name in names:
        old = old_index.get(name) or {}
        new = new_index.get(name) or {}
        combined = {**initial(name), **old, **new, "username": name}
        if new.get("status") in ("live", "offline"):
            combined["status"] = new["status"]
            combined.pop("lastKnownStatus", None)
            combined["stale"] = False
            for field in FIELDS:
                if not new.get(field) and old.get(field):
                    combined[field] = old[field]
            # A previous broadcast start is remembered if a new API response lacks it.
            if combined["status"] == "live" and combined.get("startTime"):
                combined["lastStream"] = combined["startTime"]
                combined["lastStreamSource"] = "observed"
            if combined["status"] != "live":
                combined["startTime"] = None
            elif old.get("lastStream") and new.get("lastStream"):
                from datetime import datetime
                def timestamp_date(value):
                    try: return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
                    except (ValueError, TypeError): return 0
                if timestamp_date(old["lastStream"]) > timestamp_date(new["lastStream"]):
                    combined["lastStream"] = old["lastStream"]
                    combined["lastStreamSource"] = old.get("lastStreamSource", "observed")
        else:
            # If credentials/API fail, previous 'live'/'offline' must not be presented as current.
            known = old.get("status") if old.get("status") in ("live", "offline") else old.get("lastKnownStatus")
            combined["lastKnownStatus"] = known if known in ("live", "offline") else None
            combined["status"] = "unknown"
            combined["stale"] = True
            combined["startTime"] = None
        merged.append(combined)
    return merged


def update():
    names = read_json(CONFIG).get("streamers")
    if not isinstance(names, list) or not names or any(not isinstance(x, str) or not x.isascii() or not x.isalnum() for x in names):
        raise ValueError("Geçersiz channels.json")
    past = read_json(OUT)
    old = past.get("channels", [])
    if not isinstance(old, list):
        old = []
    configured = bool(os.getenv("KICK_CLIENT_ID") and os.getenv("KICK_CLIENT_SECRET"))
    warnings = []
    if configured:
        import kick_official
        try:
            fresh, diagnostics = kick_official.fetch_snapshot(names)
            successes = diagnostics['successCount']
            warnings = diagnostics.get('warnings', [])
            source = 'official' if successes else 'kick-unavailable'
            print(f"Kick API: {successes}/{len(names)} kanal doğrulandı; "
                  f"{diagnostics['liveRecords']} canlı yayın, "
                  f"{diagnostics['profileRecords']} profil kaydı")
            for warning in warnings:
                print('Kick uyarısı:', warning)
        except kick_official.KickAPIError as exc:
            fresh = []
            successes = 0
            source = 'kick-unavailable'
            warnings = [f'Kick API bağlantısı: {exc}']
            print('Kick API bağlantı hatası:', exc)
    else:
        fresh = []
        successes = 0
        source = 'unconfigured'
        warnings = ['GitHub Actions Secrets içinde KICK_CLIENT_ID ve KICK_CLIENT_SECRET tanımlanmamış.']
        print('Kick kimlik bilgileri yok: canlı yayın algılaması yapılamıyor.')
    # Original project's public endpoint as best-effort fallback. It may return 403.
    # Official API remains authoritative when both return a checked channel.
    if successes < len(names):
        import kick_legacy
        verified = {x['username'] for x in fresh if x.get('status') in ('live','offline')}
        missing = [name for name in names if name not in verified]
        legacy, legacy_errors = kick_legacy.fetch(missing)
        if legacy:
            byname = {x['username']:x for x in fresh}
            for x in legacy: byname[x['username']] = x
            fresh=list(byname.values())
            successes += len(legacy)
            source = 'official+legacy' if source == 'official' else 'legacy'
        warnings.extend(legacy_errors[:5])
        print('Orijinal Kick kanal API yedeği:', len(legacy), '/',len(missing), 'doğrulandı')
    merged = merge_records(names, old, fresh)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "schemaVersion": 1,
        "channels": merged,
        "total": len(merged),
        "successCount": successes,
        "failedCount": len(merged) - successes,
        "source": source,
        "warnings": warnings,
        "lastAttemptAt": int(datetime.now(timezone.utc).timestamp() * 1000),
        "generatedAt": generated_at if successes else past.get("generatedAt"),
        # Only mark a successful API check as current. Failed or unconfigured is not a new check.
        "checkedAt": int(datetime.now(timezone.utc).timestamp() * 1000) if successes else past.get("checkedAt"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUT)
    return payload


if __name__ == "__main__":
    update()
