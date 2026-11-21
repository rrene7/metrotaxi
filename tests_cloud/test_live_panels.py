"""LIVE-122: each role renders polled panels without destructive identical redraws."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class LivePanelsTests(unittest.TestCase):
    def test_polling_uses_shared_diff_renderer(self):
        api=(ROOT/'web-staging/js/api.js').read_text(encoding='utf-8')
        self.assertIn('setHtml(id,html)',api)
        self.assertIn('metroPanelCache=new WeakMap()',api)
        for role,ids in {'cliente':['trips','trip-history','messages'],
                         'central':['trips','drivers','stats','messages'],
                         'conductor':['trips','driver-trip-history','unit']}.items():
            s=(ROOT/f'web-staging/js/{role}.js').read_text(encoding='utf-8')
            html=(ROOT/f'web-staging/{role}.html').read_text(encoding='utf-8')
            for id in ids:self.assertIn(f"M.setHtml('{id}',",s)
            self.assertIn('/js/api.js?v=live-122',html)
            self.assertIn(f'/js/{role}.js?v='+('live-122' if role=='cliente' else 'alerts-123'),html)
    def test_roles_and_gps_guards_remain_present(self):
        s=(ROOT/'web-staging/js/conductor.js').read_text(encoding='utf-8')
        self.assertIn("s.user.role!=='driver'",s)
        self.assertIn("t.arrival?.[act]?.allowed",s)
        s=(ROOT/'web-staging/js/central.js').read_text(encoding='utf-8')
        self.assertIn("['admin','operator'].includes(s.user.role)",s)
        self.assertIn('hasPendingCentralEdits()',s)
        s=(ROOT/'web-staging/js/cliente.js').read_text(encoding='utf-8')
        self.assertIn("s.user.role==='customer'",s)
        self.assertIn('passengerStatuses',s)
        self.assertNotIn('/api/fleet',s)
if __name__=='__main__':unittest.main()
