# Locus presentation

Static English/Russian GitHub Pages site. Edit index.html, style.css and app.js here; assets are the author-supplied presentation images. They are illustrations, not live application screenshots. No build or third-party runtime assets.

Pushes to main affecting site/ publish automatically through .github/workflows/pages.yml. The deployed artifact contains only site/, never the local application data. Preview with python3 -m http.server 8421 --directory site, then open http://127.0.0.1:8421/.
