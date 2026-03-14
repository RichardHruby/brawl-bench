// Browser Brawl: Newsletter Modal
// Realistic newsletter signup popup. Appears after 8 seconds.
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
    if (getStore('__bb_newsletter_dismissed')) return;
    if (document.getElementById('__bb_newsletter_modal')) return;

    setTimeout(function() {
      // Re-check after delay
      if (getStore('__bb_newsletter_dismissed')) return;
      if (document.getElementById('__bb_newsletter_modal')) return;

      // Backdrop overlay
      var backdrop = document.createElement('div');
      backdrop.id = '__bb_newsletter_modal';
      backdrop.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:2147483646;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;';

      function dismissModal() {
        setStore('__bb_newsletter_dismissed', '1');
        backdrop.remove();
      }

      // Click on backdrop to dismiss
      backdrop.addEventListener('click', function(e) {
        if (e.target === backdrop) dismissModal();
      });

      // Inject keyframe animation
      var styleEl = document.createElement('style');
      styleEl.textContent = '@keyframes __bb_modal_fade_in { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }';
      document.head.appendChild(styleEl);

      // Modal container
      var modal = document.createElement('div');
      modal.style.cssText = 'background:#ffffff;border-radius:12px;padding:40px 36px 36px;max-width:440px;width:90%;position:relative;box-shadow:0 20px 60px rgba(0,0,0,0.3);text-align:center;animation:__bb_modal_fade_in 0.3s ease-out;';

      modal.innerHTML = ''
        + '<button id="__bb_newsletter_close" style="position:absolute;top:12px;right:14px;background:none;border:none;font-size:22px;color:#999;cursor:pointer;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:50%;padding:0;line-height:1;" aria-label="Close">&#10005;</button>'
        + '<div style="font-size:48px;margin-bottom:16px;">&#9993;&#65039;</div>'
        + '<h2 style="margin:0 0 10px;font-size:24px;font-weight:700;color:#1a1a1a;">Sign up for our newsletter!</h2>'
        + '<p style="margin:0 0 24px;font-size:14px;color:#666;line-height:1.5;">Get exclusive deals, product recommendations, and the latest updates delivered straight to your inbox. No spam, unsubscribe anytime.</p>'
        + '<div style="display:flex;gap:8px;margin-bottom:16px;">'
        + '<input type="email" placeholder="Enter your email address" style="flex:1;padding:12px 14px;border:1px solid #ccc;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;">'
        + '<button id="__bb_newsletter_subscribe" style="background:#4a90d9;color:#fff;border:none;padding:12px 24px;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap;">Subscribe</button>'
        + '</div>'
        + '<div style="font-size:12px;color:#999;"><a id="__bb_newsletter_nothanks" style="color:#999;text-decoration:underline;cursor:pointer;">No thanks, I don\'t want deals</a></div>';

      backdrop.appendChild(modal);
      document.body.appendChild(backdrop);

      // Attach dismiss handlers
      document.getElementById('__bb_newsletter_close').addEventListener('click', function(e) {
        e.preventDefault(); e.stopPropagation(); dismissModal();
      });
      document.getElementById('__bb_newsletter_subscribe').addEventListener('click', function(e) {
        e.preventDefault(); e.stopPropagation(); dismissModal();
      });
      document.getElementById('__bb_newsletter_nothanks').addEventListener('click', function(e) {
        e.preventDefault(); e.stopPropagation(); dismissModal();
      });
    }, 8000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
