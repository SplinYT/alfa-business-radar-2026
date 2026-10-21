import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs,urlsplit
from app.core import ROOT,DB,ROLES,analyze,list_companies,add_news,import_data,connect

SESSIONS={}
LOCK=threading.Lock()
ATTEMPTS={}
TOKEN=os.getenv('APP_PASSWORD','demo-radar-2026')
ALLOWED=os.getenv('DEMO_COMPANIES','').split(',') if os.getenv('DEMO_COMPANIES') else None

def authorized_company(uid): return ALLOWED is None or uid in ALLOWED

class Handler(BaseHTTPRequestHandler):
 def log_message(self,format,*args): pass
 def send(self,status,obj,kind='application/json; charset=utf-8',cookie=None):
  content=obj if isinstance(obj,bytes) else json.dumps(obj,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(content)))
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(content)
 def session(self):
  cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
  sid=cookie.get('radar');item=SESSIONS.get(sid.value) if sid else None
  return item if item and item['expires']>time.time() else None
 def do_GET(self):
  path=urlsplit(self.path).path;q=parse_qs(urlsplit(self.path).query)
  if path in ('/','/app.js','/style.css'):
   name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
   return self.send(200,(ROOT/'web'/name).read_bytes(),{'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css'}[path])
  if path=='/health':return self.send(200,{'status':'ok'})
  s=self.session()
  if not s:return self.send(401,{'error':'Войдите в сервис'})
  try:
   if path=='/api/session':return self.send(200,{'csrf':s['csrf'],'roles':ROLES})
   if path=='/api/companies':
    rows=list_companies(q.get('q',[''])[0],q.get('large',['1'])[0]=='1')
    return self.send(200,[r for r in rows if authorized_company(r['SYNTHETIC_U'])])
   if path=='/api/bank':
    with connect() as db:r=db.execute('SELECT * FROM bank WHERE id=?',(q.get('id',[''])[0],)).fetchone()
    return self.send(200,dict(r)) if r else self.send(404,{'error':'Нет источника'})
   return self.send(404,{'error':'Нет маршрута'})
  except (ValueError,KeyError):return self.send(400,{'error':'Некорректный запрос'})
 def do_POST(self):
  path=urlsplit(self.path).path
  # Reject cross-origin writes, including login CSRF.
  origin=self.headers.get('Origin')
  if origin and urlsplit(origin).netloc!=self.headers.get('Host'):return self.send(403,{'error':'Origin запрещён'})
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=30000:return self.send(413,{'error':'Размер запроса'})
   body=json.loads(self.rfile.read(size))
   if not isinstance(body,dict):raise ValueError()
  except (ValueError,TypeError):return self.send(400,{'error':'Некорректный JSON'})
  if path=='/api/login':
   ip=self.client_address[0];now=time.time()
   with LOCK:
    hits=[t for t in ATTEMPTS.get(ip,[]) if now-t<60];ATTEMPTS[ip]=hits
    if len(hits)>=10:return self.send(429,{'error':'Слишком много попыток, повторите через минуту'})
    hits.append(now)
   if not hmac.compare_digest(str(body.get('password','')),TOKEN):return self.send(401,{'error':'Неверный пароль'})
   sid=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
   with LOCK:
    for k in list(SESSIONS):
     if SESSIONS[k]['expires']<now:del SESSIONS[k]
    SESSIONS[sid]={'expires':now+3600,'csrf':csrf}
   secure='; Secure' if os.getenv('COOKIE_SECURE')=='1' else ''
   return self.send(200,{'csrf':csrf},cookie=f'radar={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600'+secure)
  session=self.session()
  if not session:return self.send(401,{'error':'Войдите в сервис'})
  if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf']):return self.send(403,{'error':'CSRF token'})
  try:
   if path=='/api/analyze':
    uid=body.get('company','')
    if not authorized_company(uid):return self.send(403,{'error':'Нет доступа к компании'})
    return self.send(200,analyze(uid,body.get('role',ROLES[0]),body.get('as_of')))
   if path=='/api/news':return self.send(201,add_news(body))
   if path=='/api/logout':
    with LOCK:
     for k in list(SESSIONS):
      if SESSIONS[k] is session:del SESSIONS[k]
    return self.send(200,{},cookie='radar=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
   return self.send(404,{'error':'Нет маршрута'})
  except (ValueError,KeyError,TypeError) as exc:return self.send(400,{'error':str(exc)[:200]})
  except Exception:return self.send(500,{'error':'Сервис не смог выполнить запрос; проверьте конфигурацию'})

def main():
 if not DB.exists():import_data(os.getenv('DATA_DIR',str(ROOT/'data/demo')))
 print('Business Radar listening on :8000',flush=True)
 ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()

if __name__=='__main__':main()
