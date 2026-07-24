(function () {
  var params = new URLSearchParams(window.location.search);
  var query = (params.get("q") || "").trim();
  var results = document.getElementById("results");
  var pageInput = document.querySelector("[data-search-page]");
  var chinese = document.documentElement.lang === "zh-CN";

  if (pageInput) pageInput.value = query;
  if (!results) return;

  function message(text) {
    results.replaceChildren();
    var paragraph = document.createElement("p");
    paragraph.className = "search-status";
    paragraph.textContent = text;
    results.appendChild(paragraph);
  }

  function card(item) {
    var article = document.createElement("article");
    article.className = "guide-card";
    var link = document.createElement("a");
    link.href = chinese && item.zh_url ? item.zh_url : item.url;
    var eyebrow = document.createElement("span");
    eyebrow.className = "eyebrow";
    eyebrow.textContent = item.category;
    var title = document.createElement("h3");
    title.textContent = chinese && item.zh_title ? item.zh_title : item.title;
    var description = document.createElement("p");
    description.textContent = chinese && item.zh_description
      ? item.zh_description
      : item.description;
    var meta = document.createElement("span");
    meta.className = "card-meta";
    meta.textContent = chinese ? "发布于 " + item.date : "Published " + item.date;
    link.append(eyebrow, title, description, meta);
    article.appendChild(link);
    return article;
  }

  if (!query) {
    message(chinese ? "请在上方输入搜索词。" : "Enter a search term above.");
    return;
  }

  fetch("/search_index.json")
    .then(function (response) {
      if (!response.ok) throw new Error("Search index request failed");
      return response.json();
    })
    .then(function (items) {
      var normalized = query.toLocaleLowerCase();
      var hits = items.filter(function (item) {
        var haystack = [
          item.title,
          item.description,
          item.zh_title,
          item.zh_description,
          item.category,
          item.track
        ].join(" ").toLocaleLowerCase();
        return haystack.includes(normalized);
      });
      results.replaceChildren();
      var status = document.createElement("p");
      status.className = "search-status";
      status.textContent = chinese
        ? "找到 " + hits.length + " 篇与“" + query + "”相关的文章"
        : hits.length + " result" + (hits.length === 1 ? "" : "s") + ' for "' + query + '"';
      results.appendChild(status);
      if (!hits.length) return;
      var grid = document.createElement("div");
      grid.className = "guide-grid";
      hits.forEach(function (item) {
        grid.appendChild(card(item));
      });
      results.appendChild(grid);
      document.title = (chinese ? "搜索：" : "Search: ") + query + " | TKHJ Tools";
    })
    .catch(function () {
      message(chinese ? "搜索索引加载失败，请稍后重试。" : "Search index failed to load. Please try again.");
    });
})();
