// Cloudflare Pages pretty-URL handling 308s /file.html → /file.
// GSC HTML-file verification requires HTTP 200 at the exact .html path.
// This middleware runs in front of static assets (including the GSC file).
const GSC_PATH = "/google59eb4595440230ab.html";
const GSC_BODY = "google-site-verification: google59eb4595440230ab.html\n";

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.pathname === GSC_PATH) {
    return new Response(GSC_BODY, {
      status: 200,
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "public, max-age=0, must-revalidate",
        "x-content-type-options": "nosniff",
      },
    });
  }
  return context.next();
}
