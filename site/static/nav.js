(function(){
  // THEME TOGGLE (before everything else so flash is minimized)
  (function(){
    var saved = null;
    try { saved = localStorage.getItem("tkhj-theme"); } catch(e){}
    var sysDark = window.matchMedia && window.matchMedia("(prefers-color-scheme:dark)").matches;
    var theme = saved || (sysDark ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  })();

  // Render Lucide (data-lucide) elements into inline SVG
  window.renderLucide = function renderLucide(root){
    root = root || document;
    root.querySelectorAll("[data-lucide]").forEach(function(el){
      if (el.getAttribute("data-lucide-rendered") === "1") return;
      var name = el.getAttribute("data-lucide");
      if (!name) return;
      var size = parseInt(el.getAttribute("data-lucide-size") || el.getAttribute("data-size") || "18", 10);
      var cls = el.getAttribute("data-lucide-class") || "";
      var raw = (window.LUCIDE_ICONS || {})[name];
      if (!raw) { el.style.display = "none"; return; }
      var svg = raw;
      if (!(/width=/.test(raw))) {
        svg = raw.replace("<svg ", "<svg width=\"" + size + "\" height=\"" + size + "\" class=\"lucide-svg " + cls + "\" ");
      } else if (cls && !/class=/.test(svg)) {
        svg = svg.replace("<svg ", "<svg class=\"lucide-svg " + cls + "\" ");
      }
      el.innerHTML = svg;
      el.setAttribute("data-lucide-rendered", "1");
      el.style.display = "";
    });
  };
  window.renderLucide();
  setTimeout(function(){ window.renderLucide(); }, 0);

  // ACTIVE NAV
  var p = window.location.pathname;
  document.querySelectorAll(".nav-links a").forEach(function(a){
    var href = a.getAttribute("href");
    if (!href || href === "#" ) return;
    if (href === p || (p !== "/" && href !== "/" && p.startsWith(href))) {
      a.classList.add("active");
    }
  });

  // SCROLL SHADOW
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function(){
      if (window.scrollY > 8) header.classList.add("scrolled");
      else header.classList.remove("scrolled");
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // THEME TOGGLE BUTTON
  var themeBtn = document.querySelector("[data-theme-toggle]");
  if (themeBtn) {
    themeBtn.addEventListener("click", function(){
      var cur = document.documentElement.getAttribute("data-theme");
      var next = cur === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("tkhj-theme", next); } catch(e){}
    });
  }

  // TABS FILTERING
  document.querySelectorAll("[data-tabs]").forEach(function(tabBar){
    var name = tabBar.getAttribute("data-tabs");
    var section = tabBar.closest("[data-section]");
    if (!section) return;
    var cards = section.querySelectorAll("[data-card]");
    var tabs = tabBar.querySelectorAll("[data-tab]");

    function applyFilter(val) {
      var v = (val || "").toLowerCase();
      cards.forEach(function(card){
        if (v === "" || v === "all" || v === "all exams" || v === "more") {
          card.classList.remove("hidden");
          return;
        }
        var kwRaw = card.getAttribute("data-keywords") || "[]";
        var title = (card.querySelector(".card-title") || {}).textContent || "";
        var cat = (card.querySelector(".card-cat") || {}).textContent || "";
        var kws = [];
        try { kws = JSON.parse(kwRaw); } catch(e) {}
        var hay = (title + " " + cat + " " + kws.join(" ")).toLowerCase();
        card.classList.toggle("hidden", hay.indexOf(v) === -1);
      });
    }

    tabs.forEach(function(tab){
      tab.addEventListener("click", function(){
        tabs.forEach(function(t){ t.classList.remove("active"); });
        tab.classList.add("active");
        applyFilter(tab.getAttribute("data-val"));
      });
    });
  });

  

  // SEARCH
  var search = document.querySelector("[data-search]");
  function runSearch() {
    var q = (search ? search.value : "").trim().toLowerCase();
    document.querySelectorAll("[data-card]").forEach(function(card){
      if (!q) { card.classList.remove("hidden"); return; }
      var title = (card.querySelector(".card-title") || {}).textContent || "";
      var cat = (card.querySelector(".card-cat") || {}).textContent || "";
      var desc = (card.querySelector(".card-desc") || {}).textContent || "";
      var hay = (title + " " + cat + " " + desc).toLowerCase();
      card.classList.toggle("hidden", hay.indexOf(q) === -1);
    });
  }
  if (search) {
    search.addEventListener("input", debounce(runSearch, 150));
    search.addEventListener("keydown", function(e){
      if (e.key === "Enter") { e.preventDefault(); window.location = "/search.html?q=" + encodeURIComponent(search.value); }
    });
  }

function debounce(fn, ms){
    var t;
    return function(){
      var self = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function(){ fn.apply(self, args); }, ms);
    };
  }
})();


// BACK TO TOP BUTTON
(function(){
  var btn = document.createElement("button");
  btn.innerHTML = "?";
  btn.setAttribute("aria-label", "Back to top");
  btn.style.cssText = "position:fixed;bottom:24px;right:24px;width:44px;height:44px;border-radius:50%;background:var(--brand);color:#fff;border:none;font-size:1.2rem;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.2);opacity:0;transition:opacity .2s;z-index:999";
  document.body.appendChild(btn);
  window.addEventListener("scroll", function(){
    btn.style.opacity = window.scrollY > 300 ? "1" : "0";
  });
  btn.addEventListener("click", function(){
    window.scrollTo({top: 0, behavior: "smooth"});
  });
})();
