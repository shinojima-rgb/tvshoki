/**
 * site/analytics.js のクリック計測をローカルで検証する。
 *
 * - ネットワークは一切使わない。リンクも開かない。gtag はスタブ。
 * - 実ファイル（site/p/<slug>/index.html）から <a> の実属性を抽出し、
 *   最小 DOM シム上で本物の analytics.js を実行する。
 *
 * 検証すること:
 *   1. 対象の楽天リンク1クリックで outbound_product_click がちょうど1回
 *   2. product_link_click も1回（移行期の併送）。両者は同一 event_id なので
 *      2種類を足すとクリック数が2倍になる＝合算してはいけない
 *   3. product_id / link_position / article_id / article_version が期待どおり
 *   4. data-product-id も class(buy|cta) も無いリンクは0件（修正前の状態）
 *
 * 実行: node tests/analytics-click-events.test.mjs
 */
import { readFileSync } from "node:fs";
import { createContext, runInContext } from "node:vm";

const PAGES = [
  { slug: "sunsun-sponge-black", sellerLinks: 1 },
  { slug: "yonekyu-4cheese-hamburg", sellerLinks: 1 },
  { slug: "edelchef-teppanyaki-cheese-hamburg", sellerLinks: 3 },
  { slug: "marna-mizupika-sponge-k841", sellerLinks: 5 },
];

const SELECTOR_CLASSES = ["buy", "cta"];
let failures = 0;
const check = (label, actual, expected) => {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"} ${label}${ok ? "" : ` — 実際=${JSON.stringify(actual)} 期待=${JSON.stringify(expected)}`}`);
};

/** 実HTMLから楽天リンクの属性を取り出す */
function parseLinks(html) {
  const out = [];
  for (const m of html.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)) {
    const attrs = {};
    for (const a of m[1].matchAll(/([a-zA-Z-]+)="([^"]*)"/g)) attrs[a[1]] = a[2];
    if (!attrs.href || !attrs.href.includes("hb.afl.rakuten.co.jp")) continue;
    out.push({ attrs, text: m[2].replace(/<[^>]+>/g, "").trim() });
  }
  return out;
}
const articleRootOf = (html) => ({
  articleId: (html.match(/data-article-id="([^"]*)"/) || [])[1],
  articleVersion: (html.match(/data-article-version="([^"]*)"/) || [])[1],
});
const camel = (s) => s.replace(/^data-/, "").replace(/-([a-z])/g, (_, c) => c.toUpperCase());

/** analytics.js が触る範囲だけの要素シム */
function makeElement(link, root) {
  const dataset = {};
  for (const [k, v] of Object.entries(link.attrs)) if (k.startsWith("data-")) dataset[camel(k)] = v;
  const classes = (link.attrs.class || "").split(/\s+/).filter(Boolean);
  const el = {
    href: link.attrs.href,
    textContent: link.text,
    dataset,
    getAttribute: (n) => link.attrs[n] ?? null,
    matches(sel) {
      if (sel.includes("a[data-product-id]") && dataset.productId) return true;
      return SELECTOR_CLASSES.some((c) => sel.includes(`a.${c}`) && classes.includes(c));
    },
    closest(sel) {
      if (sel === "article") return null;              // 商品ガイドは <article> で包まない
      if (sel === "[data-article-id]") return { dataset: { ...root } };
      return el.matches(sel) ? el : null;
    },
  };
  return el;
}

function runClick(el, html) {
  const events = [];
  let handler = null;
  const ctx = createContext({
    window: {
      // gtag は gtag("event", <イベント名>, <パラメータ>) の3引数で呼ばれる
      gtag: (command, name, params) => { if (command === "event") events.push({ name, params }); },
      location: { href: "https://tv-mita.jp/p/x/", pathname: "/p/x/" },
      crypto: { randomUUID: () => "fixed-uuid" },
    },
    document: {
      addEventListener: (type, fn) => { if (type === "click") handler = fn; },
      querySelector: (sel) =>
        sel.includes("canonical")
          ? { href: (html.match(/rel="canonical" href="([^"]*)"/) || [])[1] }
          : null,
    },
    URL,
  });
  ctx.window.window = ctx.window;
  runInContext(readFileSync(new URL("../site/analytics.js", import.meta.url), "utf8"), ctx);
  if (!handler) throw new Error("analytics.js が click ハンドラを登録しなかった");
  handler({ target: el });                              // リンクは開かない
  return events;
}

console.log("analytics.js クリック計測のローカル検証（ネットワーク未使用）\n");

for (const page of PAGES) {
  const path = new URL(`../site/p/${page.slug}/index.html`, import.meta.url);
  const html = readFileSync(path, "utf8");
  const root = articleRootOf(html);
  const links = parseLinks(html);
  console.log(`■ ${page.slug}  楽天リンク ${links.length}件`);

  const positions = [];
  for (const link of links) {
    const el = makeElement(link, root);
    const events = runClick(el, html);
    const outbound = events.filter((e) => e.name === "outbound_product_click");
    const legacy = events.filter((e) => e.name === "product_link_click");
    const pos = link.attrs["data-link-position"];
    positions.push(pos);

    check(`[${pos}] outbound_product_click が1回`, outbound.length, 1);
    check(`[${pos}] product_link_click が1回（移行期の併送）`, legacy.length, 1);
    check(`[${pos}] 併送2件は同一 event_id（合算すると二重計上）`,
      outbound[0].params.event_id === legacy[0].params.event_id, true);
    check(`[${pos}] product_id`, outbound[0].params.product_id, link.attrs["data-product-id"]);
    check(`[${pos}] link_position`, outbound[0].params.link_position, pos);
    check(`[${pos}] article_id`, outbound[0].params.article_id, root.articleId);
    check(`[${pos}] article_version`, outbound[0].params.article_version, Number(root.articleVersion));
    check(`[${pos}] link_url が改変されていない`, outbound[0].params.link_url, link.attrs.href);
  }
  check("link_position が全リンクで一意", positions.length, new Set(positions).size);
  check("販売先リンク数", positions.filter((p) => p && p.startsWith("seller-table-")).length, page.sellerLinks);
  console.log("");
}

// 修正前の状態（data-product-id も class も無い）は計測されない
{
  console.log("■ 回帰ガード: 修正前の未計測リンク");
  const bare = makeElement(
    { attrs: { href: "https://hb.afl.rakuten.co.jp/hgc/x/?pc=https%3A%2F%2Fitem.rakuten.co.jp%2Fa%2Fb%2F", rel: "nofollow sponsored noopener" }, text: "販売店" },
    { articleId: "guide-x", articleVersion: "1" },
  );
  check("セレクタ外のリンクは0件", runClick(bare, "").length, 0);
}

// 複数ASP: data-affiliate-partner の優先と affiliate_program_id の保存
{
  console.log("\n■ 複数ASP（ValueCommerce）");
  const html = readFileSync(new URL("../site/2026-09-08/matsuko/index.html", import.meta.url), "utf8");
  const root = articleRootOf(html);
  const vc = [...html.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)]
    .map((m) => {
      const attrs = {};
      for (const a of m[1].matchAll(/([a-zA-Z-]+)="([^"]*)"/g)) attrs[a[1]] = a[2];
      return { attrs, text: m[2].replace(/<[^>]+>/g, "").trim() };
    })
    .filter((l) => l.attrs["data-affiliate-partner"] === "valuecommerce");

  check("ValueCommerceリンクが1本", vc.length, 1);
  const link = vc[0];
  const outbound = runClick(makeElement(link, root), html).filter((e) => e.name === "outbound_product_click");
  check("outbound_product_click が1回", outbound.length, 1);
  check("affiliate_partner は属性優先で valuecommerce", outbound[0].params.affiliate_partner, "valuecommerce");
  check("affiliate_program_id を保存", outbound[0].params.affiliate_program_id, "2147651");
  check("product_id", outbound[0].params.product_id, "tabelog-frufull-akasaka-13155288");
  check("link_position", outbound[0].params.link_position, "restaurant-card");
  check("article_version は2", outbound[0].params.article_version, 2);
  check("rakuten_tracking_id は unassigned", outbound[0].params.rakuten_tracking_id, "unassigned");
  check("リンクテキストに『予約』を含む", link.text.includes("予約"), true);
  check("計測ピクセルが同じリンク内にある", /ad\.jp\.ap\.valuecommerce\.com\/servlet\/gifbanner/.test(html), true);
}

// 楽天リンクは属性が無くてもホストから rakuten と判定され続ける（回帰ガード）
{
  console.log("\n■ 回帰ガード: 楽天は従来どおり");
  const html = readFileSync(new URL("../site/p/sunsun-sponge-black/index.html", import.meta.url), "utf8");
  const root = articleRootOf(html);
  const link = parseLinks(html)[0];
  const outbound = runClick(makeElement(link, root), html).filter((e) => e.name === "outbound_product_click");
  check("affiliate_partner は rakuten", outbound[0].params.affiliate_partner, "rakuten");
  check("affiliate_program_id 未指定は unassigned", outbound[0].params.affiliate_program_id, "unassigned");
}

// 合算禁止の明示
{
  console.log("\n■ 合算禁止の確認");
  const html = readFileSync(new URL("../site/p/marna-mizupika-sponge-k841/index.html", import.meta.url), "utf8");
  const root = articleRootOf(html);
  const links = parseLinks(html);
  let outbound = 0, legacy = 0;
  for (const l of links) {
    const ev = runClick(makeElement(l, root), html);
    outbound += ev.filter((e) => e.name === "outbound_product_click").length;
    legacy += ev.filter((e) => e.name === "product_link_click").length;
  }
  check(`実クリック${links.length}回に対し outbound_product_click`, outbound, links.length);
  check("2種類を足すと2倍になる（足してはいけない）", outbound + legacy, links.length * 2);
  console.log("  → 収益評価は outbound_product_click のみを使う。旧イベントとの合算は禁止。");
}

console.log(`\n${failures === 0 ? "すべて成功" : `失敗 ${failures} 件`}`);
process.exit(failures === 0 ? 0 : 1);
