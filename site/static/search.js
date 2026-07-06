(function(){
  var urlParams = new URLSearchParams(window.location.search);
  var q = (urlParams.get("q") || "").trim();
  var resultsDiv = document.getElementById("results");
  var titleInput = document.querySelector("[data-srch]");

  if (titleInput) titleInput.value = q;
  if (!q) {
    if (resultsDiv) resultsDiv.innerHTML = '<p style="color:var(--text-3)">Enter a search term above.</p>';
    return;
  }

  fetch("/search_index.json")
    .then(function(r){ return r.json(); })
    .then(function(data){
      var query = q.toLowerCase();
      var hits = data.filter(function(a){
        var hay = (a.title + " " + a.cat + " " + a.kw.join(" ")).toLowerCase();
        return hay.indexOf(query) >= 0;
      });

      if (hits.length === 0) {
        resultsDiv.innerHTML = '<p style="color:var(--text-3)">No results for "' + q + '"</p>';
        return;
      }

      var html = '<p style="font-size:.9rem;color:var(--text-3);margin-bottom:24px">' + hits.length + ' result' + (hits.length>1?'s':'') + ' for "' + q + '"</p>';
      html += '<div class="grid-4">';
      hits.forEach(function(a){
        html += '<a class="card" href="' + a.url + '">'
          + '<div class="card-body">'
          + '<span class="card-cat cat-ai">' + a.cat + '</span>'
          + '<h3 class="card-title">' + a.title + '</h3>'
          + '<div class="card-foot"><span>TKHJ Tools</span><span>' + a.date + '</span></div>'
          + '</div></a>';
      });
      html += '</div>';
      resultsDiv.innerHTML = html;

      // Update page title
      document.title = 'Search: ' + q + ' \u00b7 TKHJ Tools';
    })
    .catch(function(err){
      resultsDiv.innerHTML = '<p style="color:red">Failed to load search index.</p>';
    });

  // Search page Enter handler
  var srchInput = document.querySelector("[data-srch]");
  if (srchInput) {
    srchInput.addEventListener("keydown", function(e) {
      if (e.key === "Enter") {
        e.preventDefault();
        var val = srchInput.value.trim();
        if (val) {
          window.location = "/search.html?q=" + encodeURIComponent(val);
        }
      }
    });
  }

})();
