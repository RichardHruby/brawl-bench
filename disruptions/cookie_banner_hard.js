// Browser Brawl: Cookie Banner (Hard)
// Realistic OneTrust-style cookie consent banner.
// One-shot: dismissed via localStorage. Blocks interaction with dark overlay.
(function() {
  'use strict';

  function getStore(key) {
    try { return sessionStorage.getItem(key); } catch(e) { return null; }
  }
  function setStore(key, val) {
    try { sessionStorage.setItem(key, val); } catch(e) {}
  }

  function inject() {
    if (getStore('__bb_cookie_dismissed')) return;
    if (document.getElementById('__bb_cookie_banner')) return;

    // Dark overlay covering the ENTIRE page
    var overlay = document.createElement('div');
    overlay.id = '__bb_cookie_overlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:2147483646;';

    // Banner container at the bottom
    var banner = document.createElement('div');
    banner.id = '__bb_cookie_banner';
    banner.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:2147483647;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;';

    banner.innerHTML = '<div style="background:#1a1a2e;color:#e0e0e0;padding:24px 32px;display:flex;align-items:center;justify-content:space-between;gap:24px;min-height:120px;box-shadow:0 -4px 20px rgba(0,0,0,0.4);flex-wrap:wrap;">'
      + '<div style="flex:1 1 500px;min-width:280px;">'
      + '<div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:10px;">We value your privacy</div>'
      + '<div style="font-size:13px;color:#b0b0b0;line-height:1.6;max-width:700px;">We and our partners use cookies and similar technologies to personalise content, tailor and measure ads, and provide a better experience. By clicking &quot;Accept all cookies&quot;, you agree to the storing of cookies on your device to enhance site navigation, analyse site usage, and assist in our marketing efforts. You can manage your preferences at any time.</div>'
      + '</div>'
      + '<div style="display:flex;gap:12px;flex-shrink:0;align-items:center;flex-wrap:wrap;">'
      + '<button id="__bb_cookie_manage" style="background:transparent;color:#6ec1e4;border:2px solid #6ec1e4;padding:12px 24px;border-radius:4px;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap;">Manage preferences</button>'
      + '<button id="__bb_cookie_accept" style="background:#4caf50;color:#fff;border:none;padding:12px 28px;border-radius:4px;font-size:15px;font-weight:700;cursor:pointer;white-space:nowrap;box-shadow:0 2px 8px rgba(76,175,80,0.4);">Accept all cookies</button>'
      + '</div>'
      + '</div>';

    document.body.appendChild(overlay);
    document.body.appendChild(banner);

    function dismiss() {
      setStore('__bb_cookie_dismissed', '1');
      overlay.remove();
      banner.remove();
    }

    document.getElementById('__bb_cookie_accept').addEventListener('click', function(e) {
      e.preventDefault(); e.stopPropagation(); dismiss();
    });
    // Manage preferences does nothing — it's a decoy
    document.getElementById('__bb_cookie_manage').addEventListener('click', function(e) {
      e.preventDefault(); e.stopPropagation();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
