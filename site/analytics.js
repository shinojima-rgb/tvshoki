(function () {
  "use strict";

  function newEventId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return "click-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  }

  function canonicalArticleId() {
    var canonical = document.querySelector('link[rel="canonical"]');
    var path = canonical ? new URL(canonical.href, window.location.href).pathname : window.location.pathname;
    return "legacy:" + path.replace(/\/+$/, "");
  }

  document.addEventListener("click", function (event) {
    var link = event.target.closest("a[data-product-id], a.buy, a.cta");
    if (!link || typeof window.gtag !== "function") {
      return;
    }

    var destination = new URL(link.href, window.location.href);
    var isRakuten = destination.hostname === "hb.afl.rakuten.co.jp";
    var isSponsored = (link.getAttribute("rel") || "").split(/\s+/).indexOf("sponsored") !== -1;
    if (!isRakuten && !isSponsored && !link.dataset.productId) {
      return;
    }
    var item = link.closest("article");
    var articleRoot = link.closest("[data-article-id]") || document.querySelector("[data-article-id]");
    var itemName = item && item.querySelector("h1, h2, h3");
    var displayName = itemName ? itemName.textContent.trim() : link.textContent.trim();
    var partner = isRakuten ? "rakuten" : destination.hostname;
    var articleId = link.dataset.articleId || (articleRoot && articleRoot.dataset.articleId) || canonicalArticleId();
    var articleVersion = Number(link.dataset.articleVersion || (articleRoot && articleRoot.dataset.articleVersion) || 1);
    var productId = link.dataset.productId || link.dataset.productName || displayName || destination.href;
    var linkPosition = link.dataset.linkPosition || "legacy-product-cta";
    var parameters = {
      event_id: newEventId(),
      article_id: articleId,
      article_version: articleVersion,
      product_id: productId,
      link_position: linkPosition,
      link_url: destination.href,
      link_domain: destination.hostname,
      affiliate_partner: partner,
      rakuten_tracking_id: link.dataset.rakutenTrackingId || "unassigned",
      item_name: displayName,
      page_path: window.location.pathname,
      transport_type: "beacon"
    };

    window.gtag("event", "outbound_product_click", parameters);
    // Keep the original event during the GA4 report migration window. Revenue
    // evaluation uses outbound_product_click only.
    window.gtag("event", "product_link_click", parameters);
  });
})();
