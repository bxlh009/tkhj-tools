(function () {
  var header = document.querySelector(".site-header");
  var toggle = document.querySelector("[data-theme-toggle]");

  function updateToggleLabel() {
    if (!toggle) return;
    var dark = document.documentElement.dataset.theme === "dark";
    toggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }

  if (header) {
    function updateHeader() {
      header.classList.toggle("scrolled", window.scrollY > 8);
    }
    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
  }

  if (toggle) {
    updateToggleLabel();
    toggle.addEventListener("click", function () {
      var next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try {
        localStorage.setItem("tkhj-theme", next);
      } catch (error) {
        // The theme still works for this page when storage is unavailable.
      }
      updateToggleLabel();
    });
  }
})();
