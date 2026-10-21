"""Explicit operator-triggered RSS/Atom ingestion; no arbitrary URL tool for the LLM."""
import datetime as dt
import email.utils
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core import add_news

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Redirect disabled; configure the final trusted RSS URL')

def parse_feed(data):
 if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('DTD/Entities forbidden')
 root=ET.fromstring(data);items=root.findall('.//item')
 atom={'a':'http://www.w3.org/2005/Atom'}
 items+=root.findall('a:entry',atom);out=[]
 for item in items[:100]:
  def text(*keys):
   for k in keys:
    el=item.find(k,atom)
    if el is not None:return ''.join(el.itertext()).strip()
   return ''
  title=text('title','a:title');body=text('description','a:summary','a:content')
  date=text('pubDate','a:published','a:updated');url=text('link')
  if not url:
   link=item.find('a:link',atom);url=link.get('href','') if link is not None else ''
  try:day=dt.datetime.fromisoformat(date.replace('Z','+00:00')).date()
  except ValueError:
   try:day=email.utils.parsedate_to_datetime(date).date()
   except (TypeError,ValueError):continue
  if title and body:out.append(dict(title=title,text=body,date=day.isoformat(),url=url))
 return out

def main():
 url=sys.argv[1];parts=urlsplit(url)
 allowed=set(os.getenv('RSS_ALLOWED_HOSTS','cbr.ru,www.cbr.ru').split(','))
 if parts.scheme!='https' or parts.hostname not in allowed or parts.username or parts.password or parts.port not in (None,443):raise ValueError('Use an explicitly trusted HTTPS RSS host')
 opener=urllib.request.build_opener(NoRedirect)
 with opener.open(urllib.request.Request(url,headers={'User-Agent':'BusinessRadar/0.1'}),timeout=15) as response:data=response.read(2000001)
 if len(data)>2000000:raise ValueError('Feed too large')
 rows=parse_feed(data)
 for row in rows:add_news(row)
 print(json.dumps({'imported_or_duplicate':len(rows)}))
if __name__=='__main__':main()
