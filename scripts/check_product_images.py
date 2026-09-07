#!/usr/bin/env python3
"""site/ 配下の外部画像とアフィリエイトリンクの到達性を確認する。

商品画像は楽天の店舗が差し替え・削除すると無言で壊れる。定期実行して
非200を検出する。終了コード 1 = 到達しないURLあり。

    python3 scripts/check_product_images.py
    python3 scripts/check_product_images.py --links   # CTAリンクも確認
"""
import argparse
import concurrent.futures as cf
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent / "site"
UA = "Mozilla/5.0 (compatible; tv-mita-linkcheck/1.0)"
IMG = re.compile(r'<img[^>]+src="(https://[^"]+)"')
CTA = re.compile(r'<a[^>]+class="cta"[^>]+href="(https://[^"]+)"')


def probe(url):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return url, r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return url, e.code, ""
    except Exception as e:
        return url, 0, type(e).__name__


def collect(pattern, skip_hosts=()):
    found = {}
    for f in sorted(ROOT.rglob("*.html")):
        for url in pattern.findall(f.read_text(encoding="utf-8")):
            if any(h in url for h in skip_hosts):
                continue
            found.setdefault(url, []).append(str(f.relative_to(ROOT.parent)))
    return found


def run(label, targets, want_image):
    if not targets:
        print(f"{label}: 対象なし")
        return []
    bad = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for url, code, info in ex.map(probe, targets):
            ok = code == 200 and (not want_image or info.startswith("image/"))
            if not ok:
                bad.append((url, code, info, targets[url]))
            print(f"  {code or 'ERR':>3} {'OK ' if ok else 'NG '} {url}")
    print(f"{label}: {len(targets)}件中 {len(bad)}件が異常")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--links", action="store_true", help="CTAリンクも確認する")
    a = ap.parse_args()

    print("== 商品画像 ==")
    bad = run("画像", collect(IMG, skip_hosts=("googletagmanager.com",)), want_image=True)
    if a.links:
        print("== CTAリンク ==")
        bad += run("リンク", collect(CTA), want_image=False)

    if bad:
        print("\n異常あり:")
        for url, code, info, files in bad:
            print(f"  [{code or info}] {url}")
            for f in files:
                print(f"      {f}")
        return 1
    print("\nすべて到達しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
