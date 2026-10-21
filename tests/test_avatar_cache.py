import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import avatar_cache

class CacheTests(unittest.TestCase):
    def test_remote_urls_restricted(self):
        self.assertTrue(avatar_cache.allowed('https://images.kick.com/foo'))
        self.assertTrue(avatar_cache.allowed('https://dbxmjjzl5pc1g.cloudfront.net/foo'))
        for x in ('http://images.kick.com/abc', 'https://example.com/a', 'file:///etc/passwd',
                  'https://images.kick.com.evil.net/abc', 'https://user:pass@images.kick.com/x'):
            self.assertFalse(avatar_cache.allowed(x),x)
    def test_file_signatures(self):
        self.assertEqual(avatar_cache.image_extension(b'\xff\xd8\xff123'),'jpg')
        self.assertEqual(avatar_cache.image_extension(b'\x89PNG\r\n\x1a\n1'),'png')
        self.assertEqual(avatar_cache.image_extension(b'RIFF----WEBP'), 'webp')
        self.assertIsNone(avatar_cache.image_extension(b'<html>not an image'))
    def test_image_saved_and_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'data'/'streamers.json';out.parent.mkdir()
            image='https://images.kick.com/some-valid-profile.png'
            out.write_text(json.dumps({'channels':[{'username':'flavorr','profileImage':image}]}))
            with patch.object(avatar_cache,'ROOT',root),patch.object(avatar_cache,'SNAPSHOT',out),\
                 patch.object(avatar_cache,'DEST',root/'assets'/'avatars'),\
                 patch.object(avatar_cache,'INDEX',root/'assets'/'avatars'/'cache_index.json'),\
                 patch.object(avatar_cache,'download',return_value=('png',b'\x89PNG\r\n\x1a\n'+b'x'*400)) as dl:
                self.assertEqual(avatar_cache.update(),1)
                record=json.loads(out.read_text())['channels'][0]
                self.assertEqual(record['avatarCached'],'assets/avatars/flavorr.png')
                self.assertTrue((root/record['avatarCached']).is_file())
                self.assertEqual(avatar_cache.update(),0)
                self.assertEqual(dl.call_count,1)
    def test_missing_image_not_claimed_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'data'/'streamers.json';out.parent.mkdir()
            out.write_text(json.dumps({'channels':[{'username':'absent','profileImage':None}]}))
            with patch.object(avatar_cache,'ROOT',root),patch.object(avatar_cache,'SNAPSHOT',out),\
                 patch.object(avatar_cache,'DEST',root/'assets'/'avatars'),\
                 patch.object(avatar_cache,'INDEX',root/'assets'/'avatars'/'cache_index.json'),\
                 patch.object(avatar_cache,'download',return_value=None):
                self.assertEqual(avatar_cache.update(),0)
                self.assertFalse(json.loads(out.read_text())['channels'][0].get('avatarCached'))

if __name__=='__main__':unittest.main()
