# -*- coding: utf-8 -*-
"""sitemap.xml の lastmod を W3C Datetime（時刻・タイムゾーンつき）で再生成する。

lastmod の決め方:
  1. 中央キュー queue/jobs/*.json の publication.published_at（同一URLに複数あれば最大）
  2. git がそのファイルを最後に変更したコミットの author date
  → 両方あれば「新しい方」を採る。1 は公開記録の正本、2 は記録外の実変更を取りこぼさないための下限。
"""
import glob, io, json, os, re, subprocess, sys
from datetime import datetime, timedelta, timezone

SITE = '/Users/shino/tvshoki/site'
REPO = '/Users/shino/tvshoki'
QUEUE = '/Users/shino/tver-product-monitor/queue/jobs'
JST = timezone(timedelta(hours=9))

def parse_iso(s):
    return datetime.fromisoformat(s).astimezone(JST)

# --- 1. 中央キューの公開記録 ---
pub = {}
for f in glob.glob(os.path.join(QUEUE, '*.json')):
    try:
        j = json.load(io.open(f, encoding='utf-8'))
    except Exception:
        continue
    p = j.get('publication') or {}
    url, at = p.get('url'), p.get('published_at')
    if not (url and at):
        continue
    d = parse_iso(at)
    if url not in pub or d > pub[url]:
        pub[url] = d

# --- 2. git の最終変更時刻 ---
def git_mtime(path):
    out = subprocess.run(['git', '-C', REPO, 'log', '-1', '--format=%aI', '--', path],
                         capture_output=True, text=True).stdout.strip()
    return parse_iso(out) if out else None

src = io.open(os.path.join(SITE, 'sitemap.xml'), encoding='utf-8').read()
locs = re.findall(r'<loc>(.*?)</loc>', src)

rows, report = [], []
for url in locs:
    rel = url.replace('https://tv-mita.jp/', '')
    path = os.path.join('site', rel, 'index.html').replace('//', '/')
    full = os.path.join(REPO, path)
    if not os.path.exists(full):
        print('MISSING FILE for', url); sys.exit(1)
    g = git_mtime(path)
    q = pub.get(url)
    cands = [c for c in (g, q) if c]
    if not cands:
        print('NO DATE for', url); sys.exit(1)
    best = max(cands)
    src_label = 'queue+git' if (q and g) else ('queue' if q else 'git')
    rows.append((url, best))
    report.append((url, best.isoformat(timespec='seconds'),
                   q.isoformat(timespec='seconds') if q else '-',
                   g.isoformat(timespec='seconds') if g else '-', src_label))

out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for url, d in rows:
    out += ['  <url>', '    <loc>%s</loc>' % url,
            '    <lastmod>%s</lastmod>' % d.isoformat(timespec='seconds'), '  </url>']
out += ['</urlset>', '']
io.open(os.path.join(SITE, 'sitemap.xml'), 'w', encoding='utf-8').write('\n'.join(out))

print('%-52s %-25s %-25s %-25s %s' % ('URL', 'lastmod', 'queue', 'git', 'src'))
for r in report:
    print('%-52s %-25s %-25s %-25s %s' % (r[0].replace('https://tv-mita.jp', ''), r[1], r[2], r[3], r[4]))
print('urls:', len(rows))
