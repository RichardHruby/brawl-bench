// Browser Brawl: Load More Cliff
// Hides search results beyond #4, shows a "Show more results" button.
// Self-aware: uses MutationObserver to detect Amazon search results.
// Per-page: re-activates on each new search/navigation.
(function() {
  'use strict';

  var RESULTS_SELECTOR = '[data-component-type="s-search-result"]';
  var VISIBLE_COUNT = 4;
  var BUTTON_ID = '__bb_load_more_btn';

  function hideExcessResults() {
    var results = document.querySelectorAll(RESULTS_SELECTOR);
    if (results.length <= VISIBLE_COUNT) return;

    var hiddenResults = [];

    for (var i = 0; i < results.length; i++) {
      if (i >= VISIBLE_COUNT) {
        results[i].style.display = 'none';
        results[i].setAttribute('data-bb-hidden', '1');
        hiddenResults.push(results[i]);
      }
    }

    // Don't insert button if it already exists
    if (document.getElementById(BUTTON_ID)) return;
    if (hiddenResults.length === 0) return;

    // Insert button after the last visible result
    var lastVisible = results[VISIBLE_COUNT - 1];
    var insertTarget = lastVisible.parentNode;

    var buttonWrapper = document.createElement('div');
    buttonWrapper.id = BUTTON_ID;
    buttonWrapper.style.cssText = 'text-align:center;padding:20px 0;margin:10px 0;border-top:1px solid #e7e7e7;';

    var button = document.createElement('button');
    button.style.cssText = 'background:#fff;border:1px solid #888c8c;border-radius:8px;padding:10px 40px;font-size:14px;color:#0f1111;cursor:pointer;font-family:"Amazon Ember",Arial,sans-serif;box-shadow:0 2px 5px rgba(15,17,17,.15);';
    button.textContent = 'Show more results';

    button.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();

      // Reveal all hidden results
      var hidden = document.querySelectorAll(RESULTS_SELECTOR + '[data-bb-hidden="1"]');
      for (var j = 0; j < hidden.length; j++) {
        hidden[j].style.display = '';
        hidden[j].removeAttribute('data-bb-hidden');
      }

      // Remove the button
      buttonWrapper.remove();
    });

    buttonWrapper.appendChild(button);

    if (lastVisible.nextSibling) {
      insertTarget.insertBefore(buttonWrapper, lastVisible.nextSibling);
    } else {
      insertTarget.appendChild(buttonWrapper);
    }
  }

  function cleanupAndReprocess() {
    var oldBtn = document.getElementById(BUTTON_ID);
    if (oldBtn) oldBtn.remove();

    var oldHidden = document.querySelectorAll(RESULTS_SELECTOR + '[data-bb-hidden="1"]');
    for (var k = 0; k < oldHidden.length; k++) {
      oldHidden[k].style.display = '';
      oldHidden[k].removeAttribute('data-bb-hidden');
    }

    hideExcessResults();
  }

  function startObserving() {
    // Initial run
    hideExcessResults();

    // Observe DOM for dynamically loaded results
    var observer = new MutationObserver(function(mutations) {
      var shouldReprocess = false;
      for (var m = 0; m < mutations.length; m++) {
        if (mutations[m].addedNodes.length > 0) {
          for (var n = 0; n < mutations[m].addedNodes.length; n++) {
            var node = mutations[m].addedNodes[n];
            if (node.nodeType === 1) {
              if (node.matches && node.matches(RESULTS_SELECTOR)) {
                shouldReprocess = true;
                break;
              }
              if (node.querySelector && node.querySelector(RESULTS_SELECTOR)) {
                shouldReprocess = true;
                break;
              }
            }
          }
        }
        if (shouldReprocess) break;
      }

      if (shouldReprocess) {
        cleanupAndReprocess();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startObserving);
  } else {
    startObserving();
  }
})();
