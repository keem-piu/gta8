"""Offline contract tests for Kick public API snapshot and merge logic."""
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
import kick_official as api
import update_snapshot as snap

NOW=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()

class KickTests(unittest.TestCase):
    def test_iso_validation(self):
        self.assertEqual(api.valid_iso('2026-10-19T12:30:00Z'),'2026-10-19T12:30:00Z')
        self.assertIsNone(api.valid_iso('last week'))
    def test_https_url(self):
        self.assertIsNone(api.safe_https('javascript:alert(1)'))
        self.assertEqual(api.safe_https('https://kick.com/image.jpg'),'https://kick.com/image.jpg')
    def test_chunk_limit(self):
        self.assertEqual([len(x) for x in api.chunked(list(range(97)),50)],[50,47])
    def test_official_live_and_profiles(self):
        def fake(path, token, params):
            if path.endswith('channels'):
                return [dict(slug='flavorr',broadcaster_user_id=101,stream_title='Yayın başlığı',stream={}),
                        dict(slug='burakg',broadcaster_user_id=102,stream_title='Eski başlık',stream={})]
            if path.endswith('users/livestreams'):
                return [dict(broadcaster_user=dict(id=101,profile_picture='https://images.example/live.jpg'),
                             title='GTA Yayındayım',started_at=NOW,viewer_count=730,
                             category=dict(name='Grand Theft Auto V'),thumbnail='https://images.example/thumbnail.jpg')]
            if path.endswith('users'):
                return [dict(user_id=101,profile_picture='https://images.example/101.jpg'),
                        dict(user_id=102,profile_picture='https://images.example/102.jpg')]
            self.fail(path)
        with patch.object(api,'api_get',side_effect=fake):
            items,meta=api.fetch_snapshot(['flavorr','burakg'],token='mock-token')
        self.assertEqual([x['status'] for x in items],['live','offline'])
        self.assertEqual(items[0]['viewers'],730)
        self.assertEqual(items[0]['profileImage'],'https://images.example/101.jpg')
        self.assertEqual(items[1]['profileImage'],'https://images.example/102.jpg')
        self.assertEqual(meta['successCount'],2)
    def test_api_failure_not_offline(self):
        with patch.object(api,'api_get',side_effect=api.KickAPIError('HTTP 429')):
            items,meta=api.fetch_snapshot(['flavorr'],token='mock-token')
        self.assertEqual(items[0]['status'],'unknown')
        self.assertEqual(meta['successCount'],0)
    def test_preserve_history_photo_on_failed_refresh(self):
        old=[dict(username='flavorr',status='offline',profileImage='https://images.example/photo.jpg',lastStream=NOW,title='Known')]
        merged=snap.merge_records(['flavorr'],old,[])
        self.assertEqual(merged[0]['status'],'unknown')
        self.assertEqual(merged[0]['lastStream'],NOW)
        self.assertEqual(merged[0]['profileImage'],'https://images.example/photo.jpg')
    def test_keep_photo_when_api_returns_none(self):
        old=[dict(username='flavorr',status='offline',profileImage='https://images.example/photo.jpg',lastStream=NOW)]
        new=[dict(username='flavorr',status='live',profileImage=None,startTime=NOW,lastStream=None,checkedAt=api.now_ms())]
        merged=snap.merge_records(['flavorr'],old,new)
        self.assertEqual(merged[0]['profileImage'],'https://images.example/photo.jpg')
        self.assertEqual(merged[0]['status'],'live')
        self.assertEqual(merged[0]['lastStream'],NOW)

if __name__=='__main__': unittest.main()

class OriginalLegacyTests(unittest.TestCase):
    def test_original_live_object_without_is_live_flag(self):
        import kick_legacy
        example={'user':{'profile_pic':'https://images.example/flavorr.png'},
                 'livestream':{'id':123,'created_at':'2026-10-21T18:00:00Z',
                               'viewer_count':120,'session_title':'GTA LIVE','categories':[{'name':'GTA V'}]}}
        result=kick_legacy.parse('flavorr',example)
        self.assertEqual(result['status'],'live')
        self.assertEqual(result['viewers'],120)
        self.assertEqual(result['profileImage'],'https://images.example/flavorr.png')
    def test_offline_real_json_and_history(self):
        import kick_legacy
        example={'user':{'profile_pic':'https://images.example/photo.png'},
                'livestream':None,'recent_livestream':{'created_at':'2026-10-13T15:00:00Z'}}
        result=kick_legacy.parse('flavorr',example)
        self.assertEqual(result['status'],'offline')
        self.assertTrue(result['lastStream'])
    def test_invalid_json_does_not_mean_offline(self):
        import kick_legacy
        with self.assertRaises(kick_legacy.LegacyError):kick_legacy.parse('flavorr',{'error':'403'})

class WorkflowTests(unittest.TestCase):
    def test_original_api_stops_after_three_consecutive_errors(self):
        import kick_legacy
        with patch.object(kick_legacy,'retrieve',side_effect=kick_legacy.LegacyError('HTTP 403')) as mock, patch.object(kick_legacy.time,'sleep'):
            records,errors=kick_legacy.fetch(['a','b','c','d','e'])
        self.assertEqual(records,[])
        self.assertEqual(mock.call_count,3)
        self.assertTrue(any('Ardışık 3' in e for e in errors))
    def test_update_without_keys_uses_original_endpoint_fallback(self):
        import tempfile, os
        from unittest.mock import patch
        import kick_legacy
        import json
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'streamers.json'
            config=Path(temp)/'channels.json'
            config.write_text(json.dumps({'streamers':['flavorr']}))
            fake=dict(username='flavorr',status='live',title='Flavour GTA',viewers=33,
                      checkedAt=api.now_ms(),profileImage='https://images.example/x.png',
                      startTime=NOW,lastStream=NOW)
            with patch.object(snap,'OUT',out), patch.object(snap,'CONFIG',config), \
                 patch.object(kick_legacy,'fetch',return_value=([fake],[])), \
                 patch.dict(os.environ,{'KICK_CLIENT_ID':'','KICK_CLIENT_SECRET':''}):
                result=snap.update()
            self.assertEqual(result['source'],'legacy')
            self.assertEqual(result['successCount'],1)
            self.assertEqual(result['channels'][0]['status'],'live')
