"""Browser integration checks with FAKE Kick snapshot and fake player.
No real Kick playback is claimed by these checks.
"""
import time, json, sys
from urllib.parse import urlparse
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
try:
    time.sleep(.6)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
        js_errors=[]
        page.on('pageerror',lambda e:js_errors.append(str(e)))
        streamers=json.loads((ROOT/'data/streamers.json').read_text())
        checked=int(time.time()*1000)
        for r in streamers['channels']:
            r['status']='unknown';r['checkedAt']=None
            if r['username'] in ('burakg','flavorr'):
                r.update(status='live',checkedAt=checked,viewers=135,startTime='2026-10-21T18:00:00Z')
            if r['username']=='limonvari':r.update(status='offline',checkedAt=checked)
        streamers.update(checkedAt=checked,source='official',successCount=3,failedCount=94)
        def site_route(route):
            path=urlparse(route.request.url).path.lstrip('/') or 'index.html'
            if path=='data/streamers.json':
                return route.fulfill(status=200,content_type='application/json',body=json.dumps(streamers))
            target=(ROOT/path).resolve()
            if not target.is_relative_to(ROOT) or not target.is_file():return route.fulfill(status=404,body='Not Found')
            mime=('text/javascript' if target.suffix=='.js' else 'application/json' if target.suffix=='.json' else 'text/html')
            return route.fulfill(status=200,content_type=mime,body=target.read_bytes())
        page.route('https://gtalive.test/**',site_route)
        page.route('https://kick.com/api/**',lambda route:route.abort())
        page.route('https://player.kick.com/**',lambda route:route.fulfill(status=200,body='<body>Test oynatıcı iframe</body>',content_type='text/html'))
        page.route('https://images.kick.com/**',lambda route:route.abort())
        page.set_content((ROOT/'index.html').read_text(encoding='utf-8'))
        page.evaluate('''(data) => {
            const original=window.fetch;
            window.fetch = async (url,options) => {
                if(String(url).includes('channels.json')) return new Response(JSON.stringify(data.config), {status:200});
                if(String(url).includes('data/streamers.json')) return new Response(JSON.stringify(data.snapshot), {status:200});
                throw new Error('mock Kick unavailable');
            };
        }''', {'config':json.loads((ROOT/'channels.json').read_text()),'snapshot':streamers})
        page.add_script_tag(content=(ROOT/'app.js').read_text(encoding='utf-8'))
        page.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'))")
        page.wait_for_selector('.streamer-card')
        page.wait_for_timeout(950)
        assert page.locator('.streamer-card').count()==97
        assert page.get_by_text('Kick’te izle ↗').count()==0
        assert page.get_by_text('Yayın videoları ↗').count()==0
        assert page.locator('#autoplay-toggle').is_checked()
        # confirmed live in first viewport should autoplay
        assert page.locator('[data-username="burakg"] .streamer-iframe').count()==1, 'burakg live autoplay missing'
        # Make a channel manual and preserve during snapshot refresh
        page.evaluate("document.querySelector('[data-username=burakg]').scrollIntoView({block:'center'})")
        page.wait_for_timeout(500)
        assert page.locator('[data-username="burakg"] .streamer-iframe').count()==1
        iframe_before=page.locator('[data-username="burakg"] iframe').evaluate('(n)=>n')
        page.evaluate("window.__gtaTest.state.records.get('burakg').viewers=140; window.__gtaTest.refresh()")
        page.wait_for_timeout(200)
        assert page.locator('[data-username="burakg"] iframe').count()==1
        # manually closed should remain closed on next observer tick
        page.locator('[data-username="burakg"] .player-exit').click()
        page.wait_for_timeout(250)
        assert page.locator('[data-username="burakg"] iframe').count()==0, 'closed autoplay reopened'
        # unknown channel can be automatically attempted when scrolled into view
        page.evaluate("document.querySelector('[data-username=x4te]').scrollIntoView({block:'center'})")
        page.wait_for_timeout(600)
        assert page.locator('[data-username="x4te"] iframe').count()==1, 'unknown preview not attempted'
        # automatic playback is disabled when toggle is unchecked
        page.locator('#autoplay-toggle').uncheck()
        page.wait_for_timeout(300)
        assert page.locator('.streamer-iframe').count()==0
        # manually opened player still works with automatic off
        page.locator('[data-username="x4te"] .media-play').click()
        assert page.locator('[data-username="x4te"] iframe').count()==1
        page.screenshot(path=str(ROOT/'ONIZLEME_V8.png'),full_page=False)
        print('BROWSER OK: 97 cards, no duplicate links, live autoplay, unknown preview, close suppress, toggle, manual')
        print('JS errors:',js_errors)
        assert not js_errors
        browser.close()
finally:
    pass
