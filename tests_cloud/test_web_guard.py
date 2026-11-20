"""Cross-check critical UI references and no legacy navigation dependency."""
import unittest
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse

WEB=Path(__file__).resolve().parents[1]/'web-staging'
class Assets(HTMLParser):
    def __init__(self):super().__init__();self.refs=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='script' and a.get('src'):self.refs.append(a['src'])
        elif tag=='link' and a.get('href'):self.refs.append(a['href'])

class CloudWebChecks(unittest.TestCase):
    def test_assets_exist(self):
        for html in WEB.glob('*.html'):
            parser=Assets();parser.feed(html.read_text())
            for path in parser.refs:
                if path.startswith('https://'):
                    self.assertEqual(path, 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css', (html, path))
                else:
                    self.assertTrue((WEB/path.lstrip('/')).is_file(), (html,path))
    def test_no_cross_role_exposure(self):
        driver=(WEB/'js/conductor.js').read_text()
        self.assertNotIn(".phone",driver)
        self.assertIn("data-retry",driver)
        client=(WEB/'js/cliente.js').read_text()
        self.assertNotIn("/api/fleet",client)
        self.assertIn("/api/customer/trips",client)
    def test_android_frontend_entry(self):
        java=(WEB.parents[0]/'android-conductor/app/src/main/java/pa/metrotaxi/conductor/MainActivity.java').read_text()
        self.assertIn('"/ingresar.html"',java)
        self.assertIn('"/conductor"',java)

if __name__=='__main__':unittest.main()
