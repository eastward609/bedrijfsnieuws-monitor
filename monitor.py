#!/usr/bin/env python3
"""Officieel bedrijfsnieuws: dagelijkse cloudcrawler en statische website. Python standaardbibliotheek."""
from __future__ import annotations
import csv
import datetime as dt
import email.utils
import html
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
COMPANIES = ROOT / 'bedrijven.csv'
NEWS = ROOT / 'data' / 'nieuws.json'
STATE = ROOT / 'data' / 'bronnenstatus.json'
SITE = ROOT / 'site'
USER_AGENT = 'OfficieelBedrijfsnieuwsMonitor/1.0 (personal company news dashboard)'
MAX_BYTES = 5_000_000
MAX_NEWS = 20000
FIELDNAMES = ['bedrijf', 'ticker', 'officiele_website', 'bron_naam', 'bron_url', 'bron_type', 'actief', 'extra_officiele_domeinen']
KEYWORDS = {
 'Financieel': ['earnings', 'result', 'quarter', 'revenue', 'profit', 'ebit', 'sales performance', 'guidance', 'outlook', 'dividend', 'financial', 'share buyback', 'cash flow', 'annual report', 'interim report', 'trading update', 'debt', 'bond', 'capital increase', 'omzet', 'winst', 'kwartaal', 'jaarcijfers', 'jaarresult', 'jaarverslag', 'aandeleninkoop', 'dividende', 'résultat', 'chiffre d’affaires', 'résultats', 'résultat', 'bénéfice', 'umsatz', 'gewinn', 'geschäftsjahr', 'finanz'],
 'Operationeel': ['acquisition', 'merger', 'partnership', 'investment', 'factory', 'plant', 'production', 'capacity', 'order', 'contract', 'launch', 'shipment', 'expansion', 'supply', 'deliveries', 'new product', 'joint venture', 'deal', 'strategic', 'overname', 'fusie', 'samenwerking', 'investering', 'fabriek', 'productie', 'capaciteit', 'contract', 'levering', 'lancering', 'expansie', 'investissement', 'acquisition', 'usine', 'produktion', 'auftrag', 'übernahme'],
 'Bestuur': ['ceo', 'cfo', 'board', 'director', 'chairman', 'chairwoman', 'appointment', 'resignation', 'management', 'governance', 'shareholder meeting', 'supervisory board', 'benoeming', 'directeur', 'bestuur', 'algemene vergadering', 'directrice', 'directeur général', 'conseil d’administration', 'vorstand', 'aufsichtsrat']
}


def now():
 return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def read_json(path, fallback):
 try:
  return json.loads(path.read_text(encoding='utf-8'))
 except (FileNotFoundError, json.JSONDecodeError):
  return fallback


def write_json(path, content):
 path.parent.mkdir(parents=True, exist_ok=True)
 path.write_text(json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def host(url):
 try:
  p = urllib.parse.urlparse(url)
  if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
   return ''
  h = p.hostname.lower().rstrip('.')
  if h.startswith('www.'):
   h = h[4:]
  import ipaddress
  try:
   ipaddress.ip_address(h)
   return ''
  except ValueError:
   pass
  if h in ('localhost',) or h.endswith(('.local', '.internal', '.test')) or '.' not in h:
   return ''
  return h
 except ValueError:
  return ''


def approved_hosts(row):
 raw = [row['officiele_website']] + [f'https://{x.strip()}' for x in row.get('extra_officiele_domeinen', '').split('|') if x.strip()]
 return {host(x) for x in raw if host(x)}


def is_official(url, allowed):
 h = host(url)
 return bool(h and any(h == a or h.endswith('.' + a) for a in allowed))


def load_companies():
 with COMPANIES.open('r', encoding='utf-8-sig', newline='') as f:
  reader = csv.DictReader(f, delimiter=';')
  if not reader.fieldnames or any(field not in reader.fieldnames for field in FIELDNAMES):
   raise ValueError('bedrijven.csv heeft een onjuiste kolomindeling; behoud de oorspronkelijke kopregel.')
  rows = [{k: (row.get(k) or '').strip() for k in FIELDNAMES} for row in reader]
 if len(rows) > 1000:
  raise ValueError('Maximaal 1.000 bronregels toegestaan.')
 valid = []
 for i, row in enumerate(rows, 2):
  if not any(row.values()):
   continue
  if not row['bedrijf'] or len(row['bedrijf']) > 150:
   raise ValueError(f'Regel {i}: ongeldige bedrijfsnaam.')
  if row['actief'].lower() not in ('ja', 'nee'):
   raise ValueError(f'Regel {i}: actief moet ja of nee zijn.')
  if row['bron_type'] not in ('rss', 'html', 'auto'):
   raise ValueError(f'Regel {i}: bron_type moet rss, html of auto zijn.')
  allowed = approved_hosts(row)
  if not allowed or not is_official(row['bron_url'], allowed):
   raise ValueError(f'Regel {i}: de HTTPS-bron moet op een opgegeven officieel bedrijfsdomein staan. Voeg evt. een gecontroleerd domein toe in extra_officiele_domeinen.')
  valid.append(row)
 return valid


def save_companies(rows):
 out = io.StringIO(newline='')
 writer = csv.DictWriter(out, fieldnames=FIELDNAMES, delimiter=';', lineterminator='\n')
 writer.writeheader()
 writer.writerows(rows)
 COMPANIES.write_text(out.getvalue(), encoding='utf-8')


def manage_from_environment():
 action = os.environ.get('BEHEER_ACTIE', 'verversen').strip().lower()
 if action in ('', 'verversen'):
  return
 rows = load_companies()
 company = os.environ.get('BEHEER_BEDRIJF', '').strip()
 if not company:
  raise ValueError('Vul een bedrijfsnaam in bij Bedrijf.')
 if action == 'verwijderen':
  before = len(rows)
  rows = [r for r in rows if r['bedrijf'].casefold() != company.casefold()]
  if len(rows) == before:
   raise ValueError(f'Bedrijf "{company}" niet gevonden. Gebruik de naam uit bedrijven.csv.')
 elif action == 'toevoegen':
  row = {'bedrijf': company,
         'ticker': os.environ.get('BEHEER_TICKER', '').strip(),
         'officiele_website': os.environ.get('BEHEER_WEBSITE', '').strip(),
         'bron_naam': os.environ.get('BEHEER_BRONNAAM', '').strip() or 'Bedrijfsnieuws',
         'bron_url': os.environ.get('BEHEER_BRONURL', '').strip(),
         'bron_type': os.environ.get('BEHEER_BRONTYPE', 'auto').strip() or 'auto',
         'actief': 'ja',
         'extra_officiele_domeinen': os.environ.get('BEHEER_EXTRADOMEIN', '').strip()}
  # Validate before saving by applying the same source/domain restrictions.
  if not is_official(row['bron_url'], approved_hosts(row)) or row['bron_type'] not in ('auto', 'rss', 'html'):
   raise ValueError('De bron is geen HTTPS-URL op het opgegeven officiële domein. Controleer website en bron_url.')
  if any(r['bedrijf'].casefold() == company.casefold() and r['bron_url'] == row['bron_url'] for r in rows):
   raise ValueError('Dit bedrijf en deze bron staan al in de lijst.')
  rows.append(row)
 else:
  raise ValueError('Onbekende actie; kies verversen, toevoegen of verwijderen.')
 save_companies(rows)
 print(f'Beheer uitgevoerd: {action} - {company} ({len(rows)} bronnen in lijst)')


def strip_tags(text):
 return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(text or '')))).strip()


def date_iso(value):
 if not value:
  return None
 try:
  d = email.utils.parsedate_to_datetime(value)
 except (TypeError, ValueError, OverflowError):
  try:
   d = dt.datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
  except (TypeError, ValueError):
   return None
 if d.tzinfo is None:
  d = d.replace(tzinfo=dt.timezone.utc)
 return d.astimezone(dt.timezone.utc).isoformat(timespec='seconds')


def tagtext(e, *tags):
 for tag in tags:
  node = e.find(tag)
  if node is not None and node.text:
   return node.text.strip()
 return ''


def parse_feed(data, base_url):
 try:
  root = ET.fromstring(data)
 except ET.ParseError as exc:
  raise ValueError('Geen geldige RSS- of Atom-feed.') from exc
 atom = '{http://www.w3.org/2005/Atom}'
 dc = '{http://purl.org/dc/elements/1.1/}'
 rss1 = '{http://purl.org/rss/1.0/}'
 rootname = root.tag.rsplit('}', 1)[-1].lower()
 out = []
 if rootname == 'feed':
  for e in root.findall(f'{atom}entry'):
   title = strip_tags(tagtext(e, f'{atom}title'))
   link = ''
   for el in e.findall(f'{atom}link'):
    if el.attrib.get('rel', 'alternate') == 'alternate' and el.attrib.get('href'):
     link = el.attrib['href']; break
   if not link:
    link = e.find(f'{atom}link').attrib.get('href', '') if e.find(f'{atom}link') is not None else ''
   out.append({'title': title, 'url': urllib.parse.urljoin(base_url, link),
               'published_at': date_iso(tagtext(e, f'{atom}published', f'{atom}updated')),
               'summary': strip_tags(tagtext(e, f'{atom}summary', f'{atom}content'))[:400]})
 elif rootname in ('rss', 'rdf', 'rdf:rdf'):
  for e in root.findall('.//item') + root.findall(f'{rss1}item'):
   title = strip_tags(tagtext(e, 'title', f'{rss1}title'))
   link = tagtext(e, 'link', f'{rss1}link')
   out.append({'title': title, 'url': urllib.parse.urljoin(base_url, link),
               'published_at': date_iso(tagtext(e, 'pubDate', f'{dc}date', 'date')),
               'summary': strip_tags(tagtext(e, 'description', f'{rss1}description'))[:400]})
 else:
  raise ValueError('Bron is geen RSS/Atom.')
 return [x for x in out if x['title'] and host(x['url'])][:150]


class AnchorParser(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True)
  self.links = []
  self.feeds = []
  self.anchor = None
  self.in_heading = 0
  self.in_article = 0
 def handle_starttag(self, tag, attrs):
  a = dict(attrs)
  if tag == 'article': self.in_article += 1
  if tag in ('h1','h2','h3','h4'): self.in_heading += 1
  if tag == 'link' and 'alternate' in a.get('rel','') and any(x in a.get('type','') for x in ('rss','atom')):
   if a.get('href'): self.feeds.append(a['href'])
  if tag == 'a':
   self.anchor = {'href': a.get('href',''), 'title': a.get('title',''), 'text': [], 'heading': self.in_heading > 0, 'article': self.in_article > 0}
 def handle_data(self, text):
  if self.anchor is not None:
   self.anchor['text'].append(text)
 def handle_endtag(self, tag):
  if tag == 'a' and self.anchor is not None:
   rec = self.anchor
   rec['text'] = strip_tags(' '.join(rec['text']) or rec['title'])
   self.links.append(rec)
   self.anchor = None
  if tag == 'article': self.in_article = max(0, self.in_article-1)
  if tag in ('h1','h2','h3','h4'): self.in_heading = max(0, self.in_heading-1)


def parse_html(data, base_url):
 p = AnchorParser(); p.feed(data.decode('utf-8', 'replace'))
 cues = ('/press', '/news/', '/release', '/article', '/media/', '/investor', '/result', '/financial', '/publication', '/bericht', '/communique', '/meldungen', '/reports/')
 terms = ('earnings', 'report', 'result', 'dividend', 'quarter', 'financial', 'announcement', 'press release', 'contract', 'acquisition', 'investment', 'omzet', 'winst', 'jaarverslag', 'resultaten', 'communiqué', 'résultats', 'pressemitteilung', 'investor')
 skips = ('privacy', 'cookie', 'contact', 'subscribe', 'linkedin', 'twitter', 'facebook', 'instagram', 'legal', 'sitemap', 'careers', 'sign in')
 out, seen = [], set()
 base_path = urllib.parse.urlparse(base_url).path.rstrip('/').lower()
 for a in p.links:
  title = a['text']; url = urllib.parse.urljoin(base_url, a['href']).split('#',1)[0]
  path = urllib.parse.urlparse(url).path.lower()
  if not 18 <= len(title) <= 230 or url in seen or url.rstrip('/') == base_url.rstrip('/'):
   continue
  t = title.casefold()
  if any(x in t for x in skips) or t in ('read more','view details','learn more','more news','press releases','newsroom'):
   continue
  if path.endswith(('.jpg','.png','.gif','.css','.js','.zip','.svg')):
   continue
  nearby_section = bool(base_path and path.startswith(base_path + '/'))
  date_path = bool(re.search(r'/20\d{2}/|[-/]20\d{2}[-/]', path))
  related_url = any(c in path for c in cues)
  related_title = any(c in t for c in terms)
  if not ((a['heading'] or a['article']) and (related_url or date_path or related_title or nearby_section)
          or (related_url and (date_path or related_title or nearby_section))
          or (nearby_section and (date_path or related_title))):
   continue
  out.append({'title': title, 'url': url, 'published_at': None, 'summary': ''})
  seen.add(url)
 return out[:120], p.feeds


class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def __init__(self, allow):
  self.allow = allow
 def redirect_request(self, request, fp, code, msg, headers, newurl):
  if not is_official(newurl, self.allow):
   raise ValueError('Doorgestuurd naar een extern (niet-toegelaten) domein.')
  return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch(url, allowed):
 if not is_official(url, allowed):
  raise ValueError('Bron of omleiding is niet op een toegestaan officieel domein.')
 opener = urllib.request.build_opener(SafeRedirect(allowed))
 req = urllib.request.Request(url, headers={
  'User-Agent': USER_AGENT,
  'Accept':'application/rss+xml, application/atom+xml, text/xml, application/xml, text/html;q=0.9,*/*;q=0.5'
 })
 with opener.open(req, timeout=14) as response:
  final = response.geturl()
  if not is_official(final, allowed):
   raise ValueError('Het uiteindelijke adres is niet op een officieel domein.')
  content = response.read(MAX_BYTES+1)
  if len(content) > MAX_BYTES:
   raise ValueError('Bron groter dan 5 MB; gebruik een specifiekere nieuwsfeed.')
  return content, response.headers.get('Content-Type',''), final


def fetch_items(row):
 allowed = approved_hosts(row)
 raw, ctype, final = fetch(row['bron_url'], allowed)
 kind = row['bron_type']
 looks_xml = ('xml' in ctype or 'rss' in ctype or raw.lstrip()[:100].startswith(b'<?xml')
              or b'<rss' in raw[:120].lower() or b'<feed' in raw[:200].lower())
 if kind == 'rss' or (kind == 'auto' and looks_xml):
  entries = parse_feed(raw, final); method = 'RSS/Atom'
 else:
  entries, feeds = parse_html(raw, final)
  method = 'Officiële webpagina'
  if kind == 'auto' and feeds:
   for href in feeds[:3]:
    url = urllib.parse.urljoin(final, href)
    if not is_official(url, allowed): continue
    try:
     data, _, feedfinal = fetch(url, allowed)
     entries = parse_feed(data, feedfinal)
     method = 'Automatisch gevonden RSS'
     break
    except (ValueError, urllib.error.URLError, ET.ParseError):
     pass
 valid = []
 for x in entries:
  if is_official(x['url'], allowed):
   x['url'] = x['url'].split('#',1)[0]
   valid.append(x)
 return valid, method


def categorize(title, summary=''):
 text = (title + ' ' + summary[:200]).casefold()
 for category in ('Financieel','Bestuur','Operationeel'):
  if any(word in text for word in KEYWORDS[category]):
   return category
 return 'Overig'


def source_key(r):
 return r['bedrijf'].casefold() + '|' + r['bron_url']


def crawl_one(row):
 try:
  items, method = fetch_items(row)
  state = 'ok' if items else 'waarschuwing'
  msg = f'{len(items)} berichten gelezen via {method}' if items else f'Geen herkenbare berichten op {method}; controleer deze bron handmatig.'
  return row, items, {'status': state, 'melding': msg, 'gevonden': len(items)}
 except Exception as e:
  return row, [], {'status': 'fout', 'melding': (type(e).__name__ + ': ' + str(e))[:250], 'gevonden': 0}


def refresh():
 moment = now()
 all_rows = load_companies()
 active = [r for r in all_rows if r['actief'].lower() == 'ja']
 old_news = read_json(NEWS, {'items': []}).get('items', [])
 existing = {(x['bedrijf'].casefold(), x['url']): x for x in old_news if x.get('bedrijf') and x.get('url')}
 old_state = read_json(STATE, {'sources':{}}).get('sources',{})
 new_state = {}
 total_new = 0
 imported = 0
 with ThreadPoolExecutor(max_workers=6) as pool:
  futures = {pool.submit(crawl_one, r):r for r in active}
  for future in as_completed(futures):
   row, items, check = future.result()
   key = source_key(row)
   prior = old_state.get(key, {})
   baseline = not prior.get('laatste_succes')
   check.update({'bedrijf':row['bedrijf'], 'ticker':row['ticker'], 'bron_naam':row['bron_naam'], 'bron_url':row['bron_url'], 'bron_type':row['bron_type'], 'gecontroleerd_op':moment,
                 'laatste_succes':moment if check['status'] != 'fout' else prior.get('laatste_succes')})
   new_state[key] = check
   for item in items:
    identity = (row['bedrijf'].casefold(), item['url'])
    previous = existing.get(identity)
    if previous:
     if not previous.get('publicatiedatum') and item.get('published_at'):
      previous['publicatiedatum'] = item['published_at']
     continue
    existing[identity] = {
      'bedrijf':row['bedrijf'], 'ticker':row['ticker'], 'bron':row['bron_naam'],
      'titel':item['title'][:250], 'url':item['url'], 'publicatiedatum':item.get('published_at'),
      'ontdekt_op':moment, 'categorie':categorize(item['title'], item.get('summary','')),
      'samenvatting':item.get('summary','')[:400], 'beginarchief':baseline
    }
    if baseline: imported += 1
    else: total_new += 1
 # Preserve history for removed companies in archive; the website shows only currently followed companies.
 archive = sorted(existing.values(),key=lambda x:x.get('ontdekt_op',''),reverse=True)[:MAX_NEWS]
 write_json(NEWS, {'items':archive})
 write_json(STATE, {'laatste_controle':moment, 'nieuwe_berichten':total_new, 'startarchief':imported, 'aantal_bronnen':len(active), 'sources':new_state})
 build_site(all_rows, archive, new_state, moment, total_new)
 print(f'Klaar: {len(active)} actieve bronnen, {total_new} nieuwe berichten, {sum(x["status"]=="fout" for x in new_state.values())} fout(en).')


def build_site(rows=None, news=None, sources=None, check_time=None, new=0):
 if rows is None: rows = load_companies()
 if news is None: news = read_json(NEWS, {'items':[]}).get('items',[])
 if sources is None: sources = read_json(STATE, {'sources':{}}).get('sources',{})
 if check_time is None: check_time = read_json(STATE, {}).get('laatste_controle')
 active_rows = [r for r in rows if r['actief'].lower()=='ja']
 company_names = {r['bedrijf'].casefold() for r in active_rows}
 visible = [x for x in news if x['bedrijf'].casefold() in company_names]
 unique = {}
 for r in active_rows:
  unique[r['bedrijf'].casefold()] = {'naam':r['bedrijf'], 'ticker':r['ticker']}
 payload = {'items':visible, 'bedrijven':list(sorted(unique.values(),key=lambda x:x['naam'].casefold())),
            'bronnen':list(sorted(sources.values(),key=lambda x:(x['bedrijf'].casefold(),x['bron_naam'].casefold()))),
            'laatste_controle':check_time, 'toegevoegd_laatste_keer':new,
            'aantal_bronnen':len(active_rows), 'github_repository':os.environ.get('GITHUB_REPOSITORY','')}
 template = (ROOT / 'dashboard_template.html').read_text(encoding='utf-8')
 # Escape tags to avoid data-driven script injection while keeping valid JSON.
 packed = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
 SITE.mkdir(parents=True, exist_ok=True)
 (SITE/'index.html').write_text(template.replace('__MONITOR_DATA__', packed), encoding='utf-8')
 (SITE/'.nojekyll').write_text('', encoding='utf-8')


def main():
 manage_from_environment()
 refresh()


if __name__ == '__main__':
 main()
