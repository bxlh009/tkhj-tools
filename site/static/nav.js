(function () {
  var header = document.querySelector(".site-header");
  var toggle = document.querySelector("[data-theme-toggle]");
  var languageToggle = document.querySelector("[data-language-toggle]");
  var translations = {
    "nav-home": ["Home", "首页"],
    "nav-learning": ["Learning", "学习"],
    "nav-ai": ["AI", "AI"],
    "nav-library": ["Library", "文章库"],
    "nav-about": ["About", "关于"],
    "nav-contact": ["Contact", "联系"],
    "skip-link": ["Skip to main content", "跳到主要内容"],
    "footer-summary": [
      "Source-grounded Learning and AI guides with visible reasoning, practical examples, and explicit limits.",
      "以可靠来源为基础的学习与 AI 指南，提供清晰推理、实用示例和明确边界。"
    ],
    "footer-editorial": ["Editorial process", "编辑流程"],
    "footer-corrections": ["Corrections", "内容更正"],
    "footer-privacy": ["Privacy", "隐私"],
    "footer-disclaimer": [
      "Independent editorial site; no provider endorsement is implied.",
      "独立编辑网站；不代表任何服务商认可或背书。"
    ],
    "home-title": ["Use evidence. Make a better next move.", "依据证据，做出更好的下一步。"],
    "home-lead": [
      "Evidence-first guides for learning better and using AI with judgment. Learning guides turn mistakes into practice; AI guides turn announcements and documentation into decisions.",
      "帮助你更有效学习、更稳妥使用 AI 的独立指南。学习指南把错误转化为练习，AI 指南把公告和文档转化为可执行决策。"
    ],
    "explore-learning": ["Explore Learning", "探索学习"],
    "explore-ai": ["Explore AI", "探索 AI"],
    "see-editorial": ["See the editorial process", "查看编辑流程"],
    "method-evidence": ["Find the evidence", "找到证据"],
    "method-judgment": ["Separate claim from judgment", "区分事实主张与判断"],
    "method-next-step": ["Run a small next step", "先执行一个小步骤"],
    "learning-heading": ["Improve one study decision", "改善一个学习决策"],
    "ai-heading": ["Use AI with judgment", "有判断地使用 AI"],
    "view-learning": ["View Learning", "查看学习内容"],
    "view-ai": ["View AI", "查看 AI 内容"],
    "search-label": ["Search guides", "搜索指南"],
    "search-placeholder": ["Search", "搜索"],
    "search-page-placeholder": ["Search titles, topics, or exams", "搜索标题、主题或考试"],
    "search-button": ["Search", "搜索"],
    "search-eyebrow": ["Guide search", "指南搜索"],
    "search-title": ["Search the library", "搜索文章库"]
  };

  function applyLanguage(language) {
    var chinese = language === "zh-CN";
    document.documentElement.lang = chinese ? "zh-CN" : "en";
    document.querySelectorAll("[data-i18n]").forEach(function (element) {
      var values = translations[element.dataset.i18n];
      if (values) element.textContent = values[chinese ? 1 : 0];
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(function (element) {
      var values = translations[element.dataset.i18nPlaceholder];
      if (values) element.setAttribute("placeholder", values[chinese ? 1 : 0]);
    });
    if (languageToggle) {
      var label = languageToggle.querySelector("[data-language-label]");
      if (label) label.textContent = chinese ? "EN" : "中文";
      languageToggle.setAttribute("aria-label", chinese ? "Switch to English" : "切换到中文");
      languageToggle.setAttribute("aria-pressed", String(chinese));
    }
  }

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

  var pageLanguage = document.documentElement.dataset.pageLanguage || "en";
  var alternateUrl = document.documentElement.dataset.languageUrl || "";
  var storedLanguage = "";
  try {
    storedLanguage = localStorage.getItem("tkhj-language") || "";
  } catch (error) {
    // Use the server-rendered language when storage is unavailable.
  }
  if (
    alternateUrl &&
    ((pageLanguage === "en" && storedLanguage === "zh-CN") ||
      (pageLanguage === "zh" && storedLanguage === "en"))
  ) {
    window.location.replace(alternateUrl);
    return;
  }
  var initialLanguage = pageLanguage === "zh" || document.documentElement.lang === "zh-CN"
    ? "zh-CN"
    : "en";
  applyLanguage(initialLanguage);

  if (languageToggle) {
    languageToggle.addEventListener("click", function () {
      var next = document.documentElement.lang === "zh-CN" ? "en" : "zh-CN";
      try {
        localStorage.setItem("tkhj-language", next);
      } catch (error) {
        // The interface still switches when storage is unavailable.
      }
      if (alternateUrl) {
        window.location.assign(alternateUrl);
        return;
      }
      applyLanguage(next);
    });
  }
})();
