# The Engineer's Atlas

A free, hands-on map of software engineering: 122 lessons with runnable examples and 951 linked terms,
from the command line and networking to cloud, security and AI. Every lesson says what was verified and what was not.

Live site: enable GitHub Pages for this repository (Settings, Pages, Deploy from branch, `main`, `/ (root)`).

## Run it locally

```
python3 -m http.server 8000
```

Then open http://localhost:8000 (opening `index.html` directly will not work because the page fetches `data/*.json`).

## How the site is built

The content lives in the Atlas artifact database; `tools/build_site.py` turns an export of it into the static files here.
Last build: 2026-10-24. Do not edit `data/` by hand; it is regenerated.
