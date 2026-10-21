import datetime as dt
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from app import core
from scripts.import_rss import parse_feed

class CoreTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.old=core.DB;core.DB=core.Path(cls.tmp.name)/'test.sqlite'
  core.import_data(core.ROOT/'data/demo')
 @classmethod
 def tearDownClass(cls):core.DB=cls.old;cls.tmp.cleanup()
 def test_personalization(self):
  a=core.analyze('DEMO_STEEL',core.ROLES[0],'2026-10-21')
  b=core.analyze('DEMO_RETAIL',core.ROLES[0],'2026-10-21')
  self.assertNotEqual([x['news']['id'] for x in a['cards']],[x['news']['id'] for x in b['cards']])
  self.assertEqual(a['company']['group_members'],2)
  self.assertAlmostEqual(a['company']['top_counterparties'][0]['share'],.7)
  self.assertEqual(a['company']['related_companies'],1)
 def test_dedup_and_unseen(self):
  obj=dict(title='Новая кредитная новость',text='Ставка кредитования выросла: уточните плавающую часть долга.',date='2026-10-21')
  a=core.add_news(obj);b=core.add_news(obj);self.assertEqual(a['id'],b['id'])
  r=core.analyze('DEMO_STEEL',core.ROLES[0],'2026-10-21')
  self.assertIn(a['id'],[c['news']['id'] for c in r['cards']])
 def test_future_filtered(self):
  r=core.analyze('DEMO_STEEL',core.ROLES[0],'2020-01-01');self.assertEqual(r['cards'],[])
 def test_unknown_company(self):
  with self.assertRaises(ValueError):core.profile('not-found')
 def test_missing_data_and_nan(self):
  self.assertEqual(core.number('nan'),0)
  r=core.analyze('DEMO_SUPPLIER',core.ROLES[0],'2026-10-21')
  self.assertEqual(r['company']['outgoing_total'],0)
 def test_retrieval_citation(self):
  with core.connect() as db:db.execute('INSERT OR REPLACE INTO bank VALUES(?,?,?,?)',('test:1','test.pdf',1,'Инфляция и ставка. Стоимость кредитования остаётся высокой.'))
  rows=core.retrieve('кредитования',['rates']);self.assertTrue(rows)
  self.assertEqual(rows[0]['page'],1);self.assertIn('кредитования',rows[0]['quote'])
 def test_no_bank_retry(self):
  with patch('app.core.retrieve',return_value=[]):
   r=core.analyze('DEMO_STEEL',core.ROLES[0],'2026-10-21')
  self.assertTrue(any(s['step']=='retry' for s in r['cards'][0]['trace']))
  self.assertIn('не установлена',r['cards'][0]['insight']['bank_position'])
 def test_model_allowlist(self):
  env={'LLM_MODEL':'forbidden','LLM_MODEL_ID':'x','LLM_BASE_URL':'https://invalid','LLM_API_KEY':'secret'}
  with patch.dict(os.environ,env):
   with self.assertRaises(ValueError):core.generate({}, {}, [])
 def test_llm_rejects_unknown_citation(self):
  payload={'summary':'x','risks':[],'opportunities':[],'actions':[],'claims':[{'text':'x','source_ids':['invented']}]}
  response=unittest.mock.MagicMock()
  response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps(payload)}}]}).encode()
  env={'LLM_MODEL':'Kimi-K2.6','LLM_MODEL_ID':'issued-id','LLM_BASE_URL':'https://gateway.example/v1','LLM_API_KEY':'test-key','LLM_DAILY_TOKEN_LIMIT':'100000'}
  with patch.dict(os.environ,env),patch('urllib.request.build_opener') as opener:
   opener.return_value.open.return_value=response
   result,warning=core.generate({'text':'ставка'}, {}, [{'id':'real','quote':'text'}])
  self.assertIsNone(result);self.assertIn('не принят',warning)
 def test_llm_accepts_known_citation(self):
  payload={'summary':'x','risks':[],'opportunities':[],'actions':[],'claims':[{'text':'x','source_ids':['real']}]}
  response=unittest.mock.MagicMock()
  response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps(payload)}}]}).encode()
  env={'LLM_MODEL':'Kimi-K2.6','LLM_MODEL_ID':'issued-id','LLM_BASE_URL':'https://gateway.example/v1','LLM_API_KEY':'test-key','LLM_DAILY_TOKEN_LIMIT':'100000'}
  with patch.dict(os.environ,env),patch('urllib.request.build_opener') as opener:
   opener.return_value.open.return_value=response
   result,warning=core.generate({'text':'ставка'}, {}, [{'id':'real','quote':'text'}])
  self.assertEqual(result['mode'],'llm');self.assertIsNone(warning)
 def test_llm_budget_prevents_network(self):
  env={'LLM_MODEL':'Kimi-K2.6','LLM_MODEL_ID':'issued-id','LLM_BASE_URL':'https://gateway.example/v1','LLM_API_KEY':'test-key','LLM_DAILY_TOKEN_LIMIT':'1'}
  with patch.dict(os.environ,env),patch('urllib.request.build_opener') as opener:
   result,warning=core.generate({'text':'ставка'}, {}, [{'id':'real','quote':'text'}])
   opener.assert_not_called()
  self.assertIsNone(result);self.assertIn('лимит',warning)
 def test_invalid_news(self):
  for obj in ({'title':'','text':'a','date':'2026-10-21'},{'title':'a','text':'b','date':'bad'},{'title':'a','text':'b','date':'2026-10-21','url':'javascript:alert(1)'}):
   with self.assertRaises(ValueError):core.add_news(obj)
 def test_rss_and_atom(self):
  rss=b'<rss><channel><item><title>A</title><description>B</description><pubDate>Wed, 21 Oct 2026 10:00:00 GMT</pubDate><link>https://example.org</link></item></channel></rss>'
  self.assertEqual(parse_feed(rss)[0]['date'],'2026-10-21')
  atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A</title><summary>B</summary><updated>2026-10-21T00:00:00Z</updated><link href="https://example.org"/></entry></feed>'
  self.assertEqual(parse_feed(atom)[0]['url'],'https://example.org')
 def test_xml_entities(self):
  with self.assertRaises(ValueError):parse_feed(b'<!DOCTYPE x><rss/>')

if __name__=='__main__':unittest.main()
