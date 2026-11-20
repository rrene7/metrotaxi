"""V0.8.2: CSRF remains mandatory, while frontend can refresh a stale token."""
import unittest
import test_mvp as legacy
from pathlib import Path

class CSRFV082Tests(unittest.TestCase):
    setUp=legacy.ApiMVPTests.setUp
    tearDown=legacy.ApiMVPTests.tearDown
    client=legacy.ApiMVPTests.client
    request=legacy.ApiMVPTests.request
    login=legacy.ApiMVPTests.login

    def test_bad_or_missing_csrf_is_still_rejected_with_machine_code(self):
        admin,csrf=self.login('admin')
        payload={'mode':'manual'}
        for bad_token in (None,'invalid-stale-csrf'):
            status,response=self.request('/api/dispatch/settings','POST',payload,admin,bad_token)
            self.assertEqual(status,403)
            self.assertEqual(response['code'],'CSRF_INVALID')
        status,_=self.request('/api/dispatch/settings','POST',payload,admin,csrf)
        self.assertEqual(status,200)

    def test_csrf_token_is_private_and_never_cached(self):
        admin,csrf=self.login('admin')
        r=admin.open(self.origin+'/api/me')
        result=__import__('json').loads(r.read())
        self.assertEqual(result['csrf'],csrf)
        self.assertEqual(r.headers.get('Cache-Control'),'no-store')
        guest=self.client()
        status,me=self.request('/api/me',client=guest)
        self.assertEqual(status,200)
        self.assertIsNone(me['csrf'])

    def test_frontend_sends_token_and_retries_only_explicit_csrf_error(self):
        s=(Path(__file__).resolve().parents[1]/'static/app.js').read_text('utf-8')
        self.assertIn("obj.code==='CSRF_INVALID'",s)
        self.assertIn("window.MT.refreshCsrf()",s)
        self.assertIn("opts.headers['X-CSRF-Token']=window.MT.csrf",s)
        self.assertIn('attempt<2',s)

if __name__=='__main__':unittest.main()
