"""Optional cached channel avatars for GitHub Pages.

Only downloads HTTPS images returned by Kick's data source or the familiar
Kick CDN URL; never downloads arbitrary URLs from names or JSON.
If a source is inaccessible, it leaves the browser's existing fallback intact.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse, quote
from urllib.request import build_opener, HTTPRedirectHandler, Request
from urllib.error import URLError, HTTPError
import json
import time

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / 'data' / 'streamers.json'
DEST = ROOT / 'assets' / 'avatars'
INDEX = DEST / 'cache_index.json'
MAX_BYTES = 500_000


def allowed(url):
    if not isinstance(url, str) or len(url) > 2048:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    return (parsed.scheme == 'https' and parsed.username is None and parsed.password is None and
            (host == 'kick.com' or host.endswith('.kick.com') or
             host == 'dbxmjjzl5pc1g.cloudfront.net'))


def image_extension(data):
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    return None


class KickOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # Never follow a Kick image redirect to an arbitrary external host.
        if not allowed(newurl):
            return None
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download(url):
    if not allowed(url):
        return None
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'image/webp,image/png,image/jpeg'})
    try:
        with build_opener(KickOnlyRedirect).open(request, timeout=5) as response:
            if response.status != 200:
                return None
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return None
            kind = image_extension(raw)
            return (kind, raw) if kind and len(raw) > 200 else None
    except (HTTPError, URLError, TimeoutError, OSError):
        return None


def update():
    payload = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    try:
        index = json.loads(INDEX.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        index = {}
    updated = 0
    bad_cdn = 0
    checked = 0
    DEST.mkdir(parents=True, exist_ok=True)
    for record in payload.get('channels', []):
        name = record.get('username')
        if not isinstance(name, str) or not name.isascii() or not name.replace('_', '').isalnum() or not 1 <= len(name) <= 30:
            continue
        previous = index.get(name, {})
        stored = previous.get('path', '')
        full_path = ROOT / stored if isinstance(stored, str) else ROOT
        photo = record.get('profileImage')
        existing = full_path.is_file() and stored.startswith('assets/avatars/')
        if existing and (photo is None or photo == previous.get('source')):
            record['avatarCached'] = stored
            continue
        candidates = []
        if allowed(photo):
            candidates.append(photo)
        if bad_cdn < 3:
            candidates.append(f'https://images.kick.com/channels/{quote(name,safe="")}/profile_small')
        found = False
        for url in candidates:
            checked += 1
            result = download(url)
            if not result:
                if '/channels/' in url and url.endswith('/profile_small'):
                    bad_cdn += 1
                continue
            ext, content = result
            path = DEST / f'{name}.{ext}'
            path.write_bytes(content)
            if existing and full_path != path:
                full_path.unlink(missing_ok=True)
            stored = path.relative_to(ROOT).as_posix()
            record['avatarCached'] = stored
            index[name] = {'path': stored, 'source': photo or url}
            updated += 1
            found = True
            break
        if not found and existing:
            record['avatarCached'] = stored  # old known-good image wins over missing new image
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    SNAPSHOT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Avatar önbelleği: {updated} yeni görsel, {checked} kontrollü istek. '
          'Kick kaynakları erişilemezse eksikler kalabilir.')
    return updated


if __name__ == '__main__':
    update()
