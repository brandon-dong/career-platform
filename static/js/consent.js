// Analytics consent for the Google tag in base.html.
// Google's gtag.js sits in <head> as type="text/plain", so the browser never
// fetches it. Only after the visitor accepts does this script load it.
// The choice is kept in localStorage; nothing else is stored.
(function () {
  var KEY = 'analytics-consent';
  var banner = document.querySelector('[data-consent-banner]');
  var settings = document.querySelector('[data-consent-open]');
  if (!banner) return;

  function readChoice() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function saveChoice(value) {
    try { localStorage.setItem(KEY, value); } catch (e) { /* storage blocked: ask again next page */ }
  }

  function loadAnalytics() {
    gtag('consent', 'update', {'analytics_storage': 'granted'});
    var placeholder = document.querySelector('script[data-consent="analytics"]');
    if (!placeholder || placeholder.dataset.loaded) return;
    placeholder.dataset.loaded = 'true';
    var script = document.createElement('script');
    script.async = true;
    script.src = placeholder.src;
    document.head.appendChild(script);
  }

  // GA4 sets _ga and _ga_<stream> on the widest domain it can (".brandondong.me"),
  // so expire them on every parent domain of this host as well as host-only.
  function clearAnalyticsCookies() {
    var parts = location.hostname.split('.');
    var domains = [''];
    for (var i = 0; i < parts.length - 1; i++) {
      domains.push('; domain=.' + parts.slice(i).join('.'));
    }
    document.cookie.split(';').forEach(function (cookie) {
      var name = cookie.split('=')[0].trim();
      if (name !== '_ga' && name.indexOf('_ga_') !== 0) return;
      domains.forEach(function (domain) {
        document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/' + domain;
      });
    });
  }

  function openBanner() {
    banner.hidden = false;
    banner.querySelector('button').focus();
  }

  banner.addEventListener('click', function (event) {
    var choice = event.target.getAttribute('data-consent-choice');
    if (!choice) return;
    var previous = readChoice();
    saveChoice(choice);
    banner.hidden = true;
    if (choice === 'granted') {
      loadAnalytics();
    } else if (previous === 'granted') {
      // gtag.js can't be unloaded from a page, so start over without it.
      // Denying storage first stops it rewriting _ga_<stream> as the page unloads.
      gtag('consent', 'update', {'analytics_storage': 'denied'});
      clearAnalyticsCookies();
      location.reload();
    }
  });

  if (settings) {
    settings.hidden = false;
    settings.addEventListener('click', openBanner);
  }

  var stored = readChoice();
  if (stored === 'granted') {
    loadAnalytics();
  } else if (stored === 'denied') {
    clearAnalyticsCookies();  // in case any were left from before a withdrawal
  } else {
    banner.hidden = false;
  }
})();
