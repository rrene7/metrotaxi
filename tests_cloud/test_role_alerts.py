"""ALERTS-123 keeps notification privileges inside each role's own API view."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class AlertsTests(unittest.TestCase):
 def test_notifications_are_local_and_role_scoped(self):
  alerts=(ROOT/'web-staging/js/avisos.js').read_text(encoding='utf-8')
  self.assertIn('last===null',alerts.replace('last!==null','last===null')) if False else None
  self.assertIn('if(last!==null)',alerts)
  self.assertIn("Notification.permission==='granted'",alerts)
  self.assertIn("button.addEventListener('click',enable)",alerts)
  self.assertNotIn('serviceWorker',alerts)
  for role,condition in [('conductor',"t.status==='offered'"),('central',"t.status==='pending'")]:
   html=(ROOT/f'web-staging/{role}.html').read_text(encoding='utf-8')
   js=(ROOT/f'web-staging/js/{role}.js').read_text(encoding='utf-8')
   self.assertIn('/js/avisos.js?v=alerts-123',html)
   self.assertIn(f'/js/{role}.js?v=alerts-123',html)
   self.assertIn('id="new-trip-alert"',html)
   self.assertIn('id="enable-alerts"',html)
   self.assertIn(condition,js)
   self.assertIn('alerts.observe(',js)
  self.assertIn("s.user.role!=='driver'",(ROOT/'web-staging/js/conductor.js').read_text(encoding='utf-8'))
  self.assertIn("['admin','operator'].includes(s.user.role)",(ROOT/'web-staging/js/central.js').read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main()
