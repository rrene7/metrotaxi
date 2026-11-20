"""Netlify auto-publication smoke: public site never contains operational backend or private credentials."""
import hashlib
import re
import tomllib
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'netlify-public'


class NetlifyStaticPublishTests(unittest.TestCase):
    def test_only_public_demo_is_published(self):
        with (ROOT/'netlify.toml').open('rb') as f:
            cfg=tomllib.load(f)
        self.assertEqual(cfg['build']['publish'],'netlify-public')
        self.assertEqual(cfg['build']['command'],'node tests_cloud/test_netlify_public_demo.cjs')
        self.assertEqual(sorted(p.name for p in SITE.iterdir()),['demo.js','index.html'])
        self.assertFalse((SITE/'_redirects').exists())
        self.assertFalse((SITE/'api').exists())
        self.assertFalse((SITE/'.env').exists())
        self.assertFalse((SITE/'runtime').exists())
        self.assertFalse((SITE/'cloud').exists())
        self.assertFalse((SITE/'docker-compose.yml').exists())

    def test_demo_explicitly_fictitious_and_cache_safe(self):
        html=(SITE/'index.html').read_text(encoding='utf-8')
        js=(SITE/'demo.js').read_bytes()
        git_blob=hashlib.sha1(b'blob '+str(len(js)).encode()+b'\0'+js).hexdigest()[:12]
        self.assertIn('demo.js?v='+git_blob,html)
        self.assertIn('SIMULACIÓN PÚBLICA',html)
        self.assertIn('No introduzcas información personal.',html)
        self.assertIn('id="operations-panel" hidden',html)
        self.assertIn('id="demo-stats" hidden',html)
        self.assertNotIn('/api/customer',html)
        self.assertNotIn('DATABASE_URL',html)
        self.assertNotIn('METRO_PILOT_PASSWORD',html)

    def test_headers_prevent_indexing_and_geolocation(self):
        with (ROOT/'netlify.toml').open('rb') as f:
            cfg=tomllib.load(f)
        values=cfg['headers'][0]['values']
        self.assertEqual(values['X-Robots-Tag'],'noindex, nofollow')
        self.assertEqual(values['X-Content-Type-Options'],'nosniff')
        self.assertIn('geolocation=()',values['Permissions-Policy'])
        self.assertEqual(values['Cache-Control'],'no-store')


if __name__=='__main__':unittest.main()
