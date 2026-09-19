# site

消費者向けブランド「テレビでみた」の静的公開ファイル。

想定ドメイン: `https://tv-mita.jp/`
このフォルダをリポジトリに置いただけでは `tv-mita.jp` には公開されない。公開は未実施。

## 構成

HTML / CSS のみ。CMS・ダッシュボード・認証・JS フレームワークは使わない。

- `index.html` — トップ（スタブ。ライブ SKU ができるまで商品ページへのリンクは置かない）
- `p/index.html` — カテゴリランキング記事のハブ（`/p/`）。パイロットは `/p/ketchup/`
- `p/README.md` — `/p/<category-slug>/` の再利用テンプレート（番組総合1位ページではない）
- `p/<product-slug>/` — 既存の商品購入ガイド
- `styles.css` — 共通スタイル（最小）。`.item-card.og-card img` は 1200×630 OG サムネ用（140px 商品クロップではない）
- `og/` — 速報 OG サムネ（SVG ソース + 1200×630 PNG）。生成は `scripts/generate_og_thumb.py`（`og/README.md`）
- `robots.txt` — Allow `/` for all user-agents. `Sitemap: https://tv-mita.jp/sitemap.xml`. Do not Disallow Googlebot or hide `/` `/p/` `/2026-08-29/`
- `sitemap.xml` — live URLs only: `/` `/2026-08-29/` `/p/`
- `404.html` — real 404. Cloudflare Pages treats a missing top-level `404.html` as an SPA and serves homepage `index.html` for `/sitemap.xml` and `/robots.txt`
- `_headers` — `text/xml` for `/sitemap.xml`, `text/plain` for `/robots.txt`

## デプロイ

未定（TBD）。GitHub Pages を読者向けの公開 URL にしない。GitHub blob URL も読者 URL にしない。

カスタムドメインは `tv-mita.jp`。DNS は Owner の お名前.com Navi（Mac 上）で管理する。ドメイン購入や DNS 変更はこの作業の範囲外。

## 商品ページ（WEB Designer 骨格）

`p/index.html` は WEB Designer 指定の骨格そのもの。未記入の `/p/` はライブページではない。空テンプレートの `template-note` は置いてよい。ホームページからはリンクしない。

ファーストビューはこの順だけ。

1. 番組名 + 放送日（`.eyebrow`）
2. 画像があるときだけ残す。無いときはコメントのまま（空き枠や「任意・未設定」は出さない）
3. 小さめのブランド（`.brand-name`）+ 商品名を H1（「紹介された商品」は使わない）
4. 一文「{番組名}で紹介」（`.reason`）。ラベル「根拠URL」は出さない
5. 価格帯と送料は事実だけ
6. 全幅 CTA「商品を見る」。`display:block; width:100%; min-height:44px`。`href="#"`
7. CTA 直下に「広告を含みます」（`.ad-note`）

`title` は「{番組名} {放送日} {商品名}｜テレビでみた」。長文・関連記事・JS は置かない。商品名フィールドの二重表示はしない。

CTA の `href` は公開時に本番の追跡 URL を注入する。このリポジトリでは `href="#"` のままにする。楽天 ID を invent しない。live の `hb.afl` URL を commit しない。

task_id: 2026-08-26-tvshoki-conversion-page-v1
