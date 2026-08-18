/* Cookieless, self-hosted analytics.
 *
 * The website id lives here and nowhere else. Every page loads this one file, so
 * rotating the id -- or pulling analytics entirely -- is a one-file change instead
 * of an eleven-file sweep that always misses one.
 *
 * Umami runs on our own box. Only two of its routes are reachable from the
 * internet, /_a/script.js and /_a/api/send; the dashboard is bound to loopback and
 * reached over an SSH tunnel. Nothing here sets a cookie or contacts a third party,
 * which is what keeps the claim on /privacy true.
 */
(function () {
  var WEBSITE_ID = "REPLACE_WITH_WEBSITE_ID";

  // Until the id is filled in this file is inert, so it is safe to deploy the
  // markup before the dashboard exists -- no console errors, no failed requests.
  if (WEBSITE_ID.lastIndexOf("REPLACE", 0) === 0) return;

  var s = document.createElement("script");
  s.defer = true;
  s.src = "/_a/script.js";
  s.setAttribute("data-website-id", WEBSITE_ID);
  // Sent explicitly rather than left to the tracker's guess from its own src.
  s.setAttribute("data-host-url", window.location.origin + "/_a");
  document.head.appendChild(s);
})();
