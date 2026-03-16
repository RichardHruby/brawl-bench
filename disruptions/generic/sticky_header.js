// Browser Brawl: Sticky Promotional Header
// Adds a sticky promotional banner above Amazon's navigation.
// Persistent: always visible, pushes content down, can occlude elements.
// Self-aware: uses MutationObserver to wait for Amazon's navbar.
(function() {
  'use strict';

  var BANNER_ID = '__bb_sticky_promo_header';

  function injectBanner() {
    if (document.getElementById(BANNER_ID)) return;

    // Look for Amazon's navbar elements
    var navTarget = document.getElementById('navbar') || document.getElementById('nav-belt');
    if (!navTarget) return;

    // Walk up to find the top-level nav container
    var navContainer = navTarget;
    var candidate = navTarget;
    while (candidate.parentNode && candidate.parentNode !== document.body && candidate.parentNode !== document.documentElement) {
      if (candidate.parentNode.id === 'navbar' || candidate.parentNode.tagName === 'HEADER') {
        navContainer = candidate.parentNode;
        break;
      }
      candidate = candidate.parentNode;
    }

    var banner = document.createElement('div');
    banner.id = BANNER_ID;
    banner.style.cssText = 'position:sticky;top:0;left:0;right:0;width:100%;height:80px;background:linear-gradient(135deg,#232f3e 0%,#37475a 50%,#232f3e 100%);color:#ffffff;display:flex;align-items:center;justify-content:center;gap:16px;z-index:999997;font-family:"Amazon Ember",Arial,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,0.25);box-sizing:border-box;padding:0 20px;overflow:hidden;';

    banner.innerHTML = ''
      + '<span style="font-size:28px;flex-shrink:0;">&#128666;</span>'
      + '<div style="text-align:center;">'
      + '<div style="font-size:20px;font-weight:700;letter-spacing:0.5px;line-height:1.3;">FREE SHIPPING on orders over $35!</div>'
      + '<div style="font-size:13px;color:#f0c040;font-weight:500;margin-top:2px;">Limited time offer &bull; No promo code needed &bull; Eligible items only</div>'
      + '</div>'
      + '<span style="font-size:28px;flex-shrink:0;">&#128230;</span>';

    // Insert the banner before the nav container
    navContainer.parentNode.insertBefore(banner, navContainer);
  }

  function startObserving() {
    // Try immediately
    injectBanner();

    // Also observe DOM in case nav loads dynamically
    if (!document.getElementById(BANNER_ID)) {
      var observer = new MutationObserver(function() {
        if (!document.getElementById(BANNER_ID)) {
          var nav = document.getElementById('navbar') || document.getElementById('nav-belt');
          if (nav) {
            injectBanner();
            observer.disconnect();
          }
        } else {
          observer.disconnect();
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startObserving);
  } else {
    startObserving();
  }
})();
