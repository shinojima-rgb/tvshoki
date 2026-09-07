#!/usr/bin/env python3
"""公開URLの HTTP / title / H1 / canonical / meta robots を点検する。

sitemap.xml に載っている URL を対象に、検索エンジンの登録を妨げる問題を洗い出す。
終了コード 1 = 要修正あり。

    python3 scripts/check_seo_basics.py
    python3 scripts/check_seo_basics.py --base https://tv-mita.jp
"""
import argparse
import concurrent.futures as cf
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (compatible; tv-mita-seocheck/1.0)"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.url, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        return 0, url, type(e).__name__


def one(url):
    code, final, body = get(url)
    issues = []
    if code != 200:
        return url, code, [f"HTTP {code}"]
    if final.rstrip("/") != url.rstrip("/"):
        issues.append(f"リダイレクト先 {final}")

    t = re.search(r"<title>(.*?)</title>", body, re.S)
    title = t.group(1).strip() if t else ""
    if not title:
        issues.append("title なし")
    elif len(title) > 60:
        issues.append(f"title {len(title)}文字（長い）")

    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    if len(h1) == 0:
        issues.append("H1 なし")
    elif len(h1) > 1:
        issues.append(f"H1 が{len(h1)}個")

    c = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', body)
    if not c:
        issues.append("canonical なし")
    elif c.group(1).rstrip("/") != url.rstrip("/"):
        issues.append(f"canonical 不一致 {c.group(1)}")

    r = re.search(r'<meta[^>]+name="robots"[^>]+content="([^"]+)"', body, re.I)
    if r and re.search(r"noindex|none", r.group(1), re.I):
        issues.append(f"robots={r.group(1)}")

    if not re.search(r'<meta[^>]+name="description"[^>]+content="[^"]+"', body):
        issues.append("meta description なし")
    return url, code, issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://tv-mita.jp")
    a = ap.parse_args()

    code, _, xml = get(a.base.rstrip("/") + "/sitemap.xml")
    if code != 200:
        print(f"sitemap.xml が取得できません（HTTP {code}）")
        return 1
    urls = [e.text.strip() for e in ET.fromstring(xml).findall(".//s:loc", NS)]
    print(f"sitemap: {len(urls)} URL\n")

    bad = 0
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for url, st, issues in ex.map(one, urls):
            mark = "OK " if not issues else "NG "
            print(f"  {mark}{st} {url}")
            for i in issues:
                print(f"        - {i}")
            bad += bool(issues)

    for extra in ("/robots.txt", "/sitemap.xml", "/404-does-not-exist-check/"):
        c, _, _ = get(a.base.rstrip("/") + extra)
        want = 404 if "does-not-exist" in extra else 200
        ok = c == want
        print(f"  {'OK ' if ok else 'NG '}{c} {extra}（期待 {want}）")
        bad += (not ok)

    print(f"\n要修正: {bad} 件" if bad else "\nすべて問題なし")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
