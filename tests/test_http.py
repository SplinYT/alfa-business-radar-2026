import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from app import core,server

class HttpTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.old=core.DB;core.DB=core.Path(cls.tmp.name)/'http.sqlite';core.import_data(core.ROOT/'data/demo')
  cls.s=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);threading.Thread(target=cls.s.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.s.shutdown();cls.s.server_close();core.DB=cls.old;cls.tmp.cleanup()
 def call(self,method,path,body=None,headers=None):
  c=http.client.HTTPConnection('127.0.0.1',self.s.server_port)
  c.request(method,path,json.dumps(body) if body else None,headers or {});r=c.getresponse();data=r.read();h=dict(r.getheaders());c.close();return r.status,json.loads(data),h
 def test_login_to_analysis(self):
  self.assertEqual(self.call('GET','/api/companies')[0],401)
  status,body,h=self.call('POST','/api/login',{'password':server.TOKEN});self.assertEqual(status,200)
  headers={'Cookie':h['Set-Cookie'].split(';')[0],'X-CSRF-Token':body['csrf']}
  status,companies,_=self.call('GET','/api/companies',headers=headers);self.assertEqual(status,200)
  uid=companies[0]['SYNTHETIC_U']
  status,result,_=self.call('POST','/api/analyze',{'company':uid,'role':core.ROLES[0],'as_of':'2026-10-21'},headers)
  self.assertEqual(status,200);self.assertTrue(result['cards'])
  headers.pop('X-CSRF-Token');self.assertEqual(self.call('POST','/api/news',{'title':'x'},headers)[0],403)
 def test_cross_origin(self):
  status,_,_=self.call('POST','/api/login',{'password':server.TOKEN},{'Origin':'https://evil.example','Host':'127.0.0.1'})
  self.assertEqual(status,403)
 def test_company_access(self):
  old=server.ALLOWED;server.ALLOWED=['DEMO_RETAIL']
  try:
   _,b,h=self.call('POST','/api/login',{'password':server.TOKEN});headers={'Cookie':h['Set-Cookie'].split(';')[0],'X-CSRF-Token':b['csrf']}
   self.assertEqual(self.call('POST','/api/analyze',{'company':'DEMO_STEEL','role':core.ROLES[0]},headers)[0],403)
  finally:server.ALLOWED=old
