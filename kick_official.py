"""Kick public developer API snapshot fetcher (runs inside GitHub Actions, not Pages).

Official docs: https://api.kick.com/swagger/doc.json
- GET /public/v1/channels accepts up to 50 slug query parameters.
- GET /public/v1/users/livestreams accepts up to 100 user_id query parameters.
- GET /public/v1/users accepts user ID parameters; returns profile_picture.
- All require a server-side OAuth client-credentials access token.
"""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import os
import time

BASE = 'https://api.kick.com'
TOKEN_URL = 'https://id.kick.com/oauth/token'
TIMEOUT = 12


class KickAPIError(Exception):
    pass


def now_ms():
    return int(time.time() * 1000)


def valid_iso(value):
    if not isinstance(value, str) or not 10 <= len(value) <= 40:
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        if dt.year < 2000 or dt.year > 2100:
            return None
        return value.strip()
    except (ValueError, TypeError):
        return None


def safe_https(value):
    return value if isinstance(value, str) and value.startswith('https://') and len(value) < 2048 else None


def chunked(values, size):
    for i in range(0, len(values), size):
        yield values[i:i + size]


def transport(url, headers=None, form=None):
    headers = {'Accept': 'application/json', 'User-Agent': 'GTA-LIVE-Pages/5.0', **(headers or {})}
    req = Request(url, data=urlencode(form).encode('utf-8') if form is not None else None,
                  headers=headers, method='POST' if form is not None else 'GET')
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                raise KickAPIError(f'HTTP {resp.status}')
            raw = resp.read(1_000_001)
            if len(raw) > 1_000_000:
                raise KickAPIError('API yanıtı beklenenden büyük')
            return json.loads(raw)
    except HTTPError as exc:
        raise KickAPIError(f'HTTP {exc.code}') from None
    except (URLError, TimeoutError, OSError) as exc:
        raise KickAPIError(f'Ağ hatası ({type(exc).__name__})') from None
    except (ValueError, UnicodeDecodeError) as exc:
        raise KickAPIError('Geçersiz JSON yanıtı') from exc


def get_app_token():
    client_id = os.getenv('KICK_CLIENT_ID', '').strip()
    secret = os.getenv('KICK_CLIENT_SECRET', '').strip()
    if not client_id or not secret:
        raise KickAPIError('KICK_CLIENT_ID ve KICK_CLIENT_SECRET eksik')
    result = transport(TOKEN_URL, {'Content-Type': 'application/x-www-form-urlencoded'}, {
        'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': secret})
    token = result.get('access_token') if isinstance(result, dict) else None
    if not isinstance(token, str) or not token:
        raise KickAPIError('OAuth access_token yanıtında yok')
    return token


def api_get(path, token, params):
    url = BASE + path + ('?' + urlencode(params, doseq=True) if params else '')
    result = transport(url, headers={'Authorization': f'Bearer {token}'})
    if not isinstance(result, dict) or not isinstance(result.get('data'), list):
        raise KickAPIError('API data dizisi yok')
    return result['data']


def identifier(value):
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str) and value.isdecimal() and int(value) > 0:
        return int(value)
    return None


def stream_broadcaster_id(stream):
    user = stream.get('broadcaster_user') if isinstance(stream.get('broadcaster_user'), dict) else {}
    return identifier(user.get('id')) or identifier(stream.get('broadcaster_user_id'))


def parse_live(stream, fallback_name):
    cat = stream.get('category') if isinstance(stream.get('category'), dict) else {}
    broadcaster = stream.get('broadcaster_user') if isinstance(stream.get('broadcaster_user'), dict) else {}
    return {
        'title': str(stream.get('title') or f'{fallback_name} Kanalı')[:250],
        'category': str(cat.get('name') or 'GTA')[:80],
        'startTime': valid_iso(stream.get('started_at')),
        'viewers': max(0, int(stream.get('viewer_count') or 0)),
        'thumbnail': safe_https(stream.get('thumbnail')),
        'profileImage': safe_https(broadcaster.get('profile_picture')),
    }


def fetch_snapshot(names, token=None):
    """Return (records, diagnostics). Partial failures are unknown, never fake offline.

    A successful user-livestreams batch is an authoritative presence/absence check
    for those IDs; successful channel lookups provide metadata and a fallback
    when the livestream endpoint itself fails.
    """
    stamp = now_ms()
    errors = []
    channels = {}
    token = token or get_app_token()
    for group in chunked(list(names), 50):
        try:
            rows = api_get('/public/v1/channels', token, [('slug', slug) for slug in group])
            for row in rows:
                if not isinstance(row, dict):
                    continue
                name = str(row.get('slug') or '').lower()
                if name in group:
                    channels[name] = row
        except KickAPIError as exc:
            errors.append(f'channels ({group[0]}..): {exc}')

    user_ids = {name: identifier(row.get('broadcaster_user_id')) for name, row in channels.items()}
    good_ids = [v for v in user_ids.values() if v is not None]

    # A completed batch's absence is meaningful: the broadcaster is offline.
    # A failed batch's absence is NOT meaningful and must not turn into offline.
    seen_livestreams = {}
    successfully_checked_ids = set()
    for group in chunked(list(dict.fromkeys(good_ids)), 100):
        try:
            rows = api_get('/public/v1/users/livestreams', token, [('user_id', uid) for uid in group])
            successfully_checked_ids.update(group)
            for row in rows:
                if not isinstance(row, dict):
                    continue
                uid = stream_broadcaster_id(row)
                if uid in group:
                    seen_livestreams[uid] = row
        except KickAPIError as exc:
            errors.append(f'users/livestreams ({len(group)} id): {exc}')

    # User pictures are independent from live status. A failure here must not
    # discard an otherwise successful live/offline verification.
    photos = {}
    for group in chunked(list(dict.fromkeys(good_ids)), 50):
        try:
            rows = api_get('/public/v1/users', token, [('id', uid) for uid in group])
            for row in rows:
                if isinstance(row, dict):
                    uid = identifier(row.get('user_id'))
                    if uid:
                        photos[uid] = safe_https(row.get('profile_picture'))
        except KickAPIError as exc:
            errors.append(f'users/profile ({len(group)} id): {exc}')

    records = []
    for name in names:
        record = {
            'username': name, 'status': 'unknown', 'title': f'{name} Kanalı',
            'category': 'GTA', 'startTime': None, 'lastStream': None,
            'lastStreamSource': 'none', 'lastVideoAt': None,
            'viewers': None, 'followers': None, 'profileImage': None,
            'thumbnail': None, 'checkedAt': None, 'source': 'official',
        }
        channel = channels.get(name)
        if channel is not None:
            uid = user_ids.get(name)
            stream = channel.get('stream') if isinstance(channel.get('stream'), dict) else {}
            category = channel.get('category') if isinstance(channel.get('category'), dict) else {}
            record['title'] = str(channel.get('stream_title') or record['title'])[:250]
            record['category'] = str(category.get('name') or 'GTA')[:80]
            record['profileImage'] = photos.get(uid)
            record['thumbnail'] = safe_https(stream.get('thumbnail'))
            if uid and uid in seen_livestreams:
                record.update(parse_live(seen_livestreams[uid], name))
                record['profileImage'] = photos.get(uid) or record['profileImage']
                broadcast_user = seen_livestreams[uid].get('broadcaster_user')
                if isinstance(broadcast_user, dict):
                    record['profileImage'] = record['profileImage'] or safe_https(
                        broadcast_user.get('profile_picture'))
                record['status'] = 'live'
                record['checkedAt'] = stamp
            elif uid and uid in successfully_checked_ids:
                # Stream list is verified, but don't downgrade a contradictory
                # explicit is_live=true from /channels.
                if stream.get('is_live') is True:
                    record['status'] = 'live'
                    record['viewers'] = max(0, int(stream.get('viewer_count') or 0))
                    record['startTime'] = valid_iso(stream.get('start_time'))
                    errors.append(f'{name}: channels CANLI, users/livestreams listesinde yok')
                else:
                    record['status'] = 'offline'
                record['checkedAt'] = stamp
            elif isinstance(stream.get('is_live'), bool):
                # Use explicitly validated /channels fallback if the separate
                # user-livestreams endpoint was unavailable.
                record['status'] = 'live' if stream['is_live'] else 'offline'
                if stream['is_live']:
                    record['viewers'] = max(0, int(stream.get('viewer_count') or 0))
                    record['startTime'] = valid_iso(stream.get('start_time'))
                record['checkedAt'] = stamp
        records.append(record)
    success = sum(item['status'] != 'unknown' for item in records)
    return records, {'successCount': success, 'failedCount': len(names) - success,
                     'warnings': errors[:12], 'channelRecords': len(channels),
                     'liveRecords': len(seen_livestreams), 'profileRecords': len(photos)}
