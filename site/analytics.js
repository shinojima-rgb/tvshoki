(function () {
  "use strict";

  document.addEventListener("click", function (event) {
    var link = event.target.closest("a.cta");
    if (!link || typeof window.gtag !== "function") {
      return;
    }

    var destination = new URL(link.href, window.location.href);
    var item = link.closest("article");
    var itemName = item && item.querySelector("h1, h2, h3");
    var partner = destination.hostname === "hb.afl.rakuten.co.jp"
      ? "rakuten"
      : destination.hostname;

    window.gtag("event", "product_link_click", {
      link_url: destination.href,
      link_domain: destination.hostname,
      affiliate_partner: partner,
      item_name: itemName ? itemName.textContent.trim() : link.textContent.trim(),
      page_path: window.location.pathname,
      transport_type: "beacon"
    });
  });
})();
