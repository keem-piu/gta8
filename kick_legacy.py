"""Best-effort read-only fallback for the ORIGINAL website endpoint.

Not an official API. It may be blocked by Kick or stop working without notice.
Never reports an unverified channel as offline. Requires no API secrets.
"""
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import quote
import json
import time

class LegacyError(Exception):
    pass

def iso(value):
    if not isinstance(value,str) or not value.strip(): return None
    try:
        d=datetime.fromisoformat(value.strip().replace(' ','T').replace('Z','+00:00'))
        if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
        return d.isoformat() if 2010<=d.year<=2100 else None
    except (ValueError,TypeError):return None

def https(value):
    return value if isinstance(value,str) and value.startswith('https://') and len(value)<2048 else None

def parse(name,data):
    if not isinstance(data,dict) or not isinstance(data.get('user'),dict):
        raise LegacyError('Kanal JSON şeması beklenenden farklı')
    live=data.get('livestream')
    live=live if isinstance(live,dict) else None
    running=bool(live and live.get('is_live') is not False and (
        live.get('id') is not None or live.get('created_at') or live.get('is_live') is True))
    old=data.get('recent_livestream') if isinstance(data.get('recent_livestream'),dict) else {}
    timestamp=iso((live or {}).get('created_at')) if running else None
    last=timestamp or iso(old.get('created_at')) or iso(data.get('last_live_at'))
    user=data['user']
    title=(live or {}).get('session_title') if running else None
    thumb=(live or {}).get('thumbnail') if running else None
    thumb=thumb.get('url') if isinstance(thumb,dict) else thumb
    categories=(live or {}).get('categories') if running else []
    category=categories[0].get('name') if isinstance(categories,list) and categories and isinstance(categories[0],dict) else 'GTA'
    return {'username':name,'status':'live' if running else 'offline',
            'title':str(title or f'{name} Kanalı')[:250],
            'category':str(category or 'GTA')[:80],
            'startTime':timestamp,'lastStream':last,
            'lastStreamSource':'observed' if timestamp else 'recent_livestream' if iso(old.get('created_at')) else 'last_live_at' if last else 'none',
            'lastVideoAt':None,'viewers':max(0,int(live.get('viewer_count') or 0)) if running else None,
            'profileImage':https(user.get('profile_pic') or user.get('profile_picture')),
            'thumbnail':https(thumb),'checkedAt':int(time.time()*1000),'source':'legacy'}

def retrieve(name):
    req=Request('https://kick.com/api/v2/channels/'+quote(name,safe=''),headers={
        'Accept':'application/json','User-Agent':'Mozilla/5.0 (compatible; GTA-LIVE/7.0)'})
    try:
        with urlopen(req,timeout=7) as res:
            if res.status!=200: raise LegacyError('HTTP '+str(res.status))
            payload=res.read(500_001)
            if len(payload)>500_000:raise LegacyError('Veri boyutu sınırı')
            return parse(name,json.loads(payload))
    except HTTPError as e: raise LegacyError('HTTP '+str(e.code)) from None
    except (URLError,TimeoutError,OSError,ValueError) as e:raise LegacyError(type(e).__name__) from None

def fetch(names):
    records=[]; errors=[];failed=0
    for name in names:
        try:
            records.append(retrieve(name));failed=0
        except LegacyError as e:
            errors.append(name+': '+str(e));failed+=1
            if failed>=3:
                errors.append('Ardışık 3 istek başarısız; aşırı API isteği önlemek için durduruldu')
                break
        time.sleep(0.15)
    return records,errors
