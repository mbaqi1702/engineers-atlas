#!/usr/bin/env python3
"""Build the static GitHub Pages site for The Engineer's Atlas.

Inputs
  --export   folder produced by reading the artifact database with out_dir:
             <export>/toc/*.json, <export>/terms/*.json, <export>/lessons/*.json, <export>/home/main.json
  --template the artifact page source (index.html copied by `Artifact read`)
  --out      output folder (the repository root)

What it does
  1. Merges the exported documents into a few JSON files under data/
     (toc.json, terms.json, home.json and one lessons bundle per domain).
  2. Turns the artifact page into a static page: the database calls are replaced by fetches
     of those JSON files, and the "Deep dive with Claude" button disappears (it needs Claude's runtime).
  3. Writes README.md, .nojekyll and a copy of this script into tools/.

Run:  python3 build_site.py --export export --template page/index.html --out site
Preview: cd site && python3 -m http.server 8000   (opening index.html as a file will not work: fetch needs http)
"""
import argparse
import datetime
import json
import re
import shutil
from pathlib import Path


def load_dir(folder):
    return {p.stem: json.loads(p.read_text()) for p in sorted(Path(folder).glob("*.json"))}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


SHIM = r"""(function(){
var main=$("#main");main.innerHTML='<p class="meta">Loading the Atlas\u2026</p>';
function J(u){return fetch(u).then(function(r){if(!r.ok)throw new Error(u+" returned "+r.status);return r.json()})}
var bundles={};
DB={doc:function(p){var id=p.replace(/^lessons\//,"");return{get:function(){var dom=LS[id]&&LS[id].d;if(!dom)return Promise.resolve({exists:false});
return(bundles[dom]||(bundles[dom]=J("data/lessons/"+dom+".json"))).then(function(b){var d=b[id];return{exists:!!d,data:function(){return d}}})}}}};
Promise.all([J("data/toc.json"),J("data/terms.json"),J("data/home.json").catch(function(){return null})]).then(function(r){
TOC=r[0];TERMS=r[1];HOME=r[2];LS={};for(var d in TOC)for(var k in TOC[d])LS[k]={id:k,d:d,t:TOC[d][k][0],lv:TOC[d][k][1],m:TOC[d][k][2]};
buildRe();side();route()}).catch(function(e){main.innerHTML='<h1>Could not load the Atlas</h1><p>'+esc(e.message)+'. If you opened index.html as a file, serve the folder instead, for example <code>python3 -m http.server</code>.</p>'});
})();
</script>"""

HEAD = """<title>The Engineer's Atlas</title>
<meta name="description" content="A free, hands-on map of software engineering: {nl} lessons with runnable examples and {nt} linked terms, from the command line to cloud, security and AI.">
<meta property="og:title" content="The Engineer's Atlas"><meta property="og:type" content="website">
<meta property="og:description" content="A free, hands-on map of software engineering: {nl} lessons with runnable examples and {nt} linked terms.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%232456c9'/%3E%3Ccircle cx='9' cy='11' r='3' fill='white'/%3E%3Ccircle cx='17' cy='19' r='3' fill='white'/%3E%3Ccircle cx='24' cy='9' r='3' fill='white'/%3E%3C/svg%3E">
<noscript><style>#main::before{{content:"The Atlas needs JavaScript."}}</style></noscript>"""


def must_replace(text, old, new, label):
    if old not in text:
        raise SystemExit(f"template changed: could not find {label!r}. Update build_site.py before publishing.")
    return text.replace(old, new, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    exp, out = Path(a.export), Path(a.out)

    toc = load_dir(exp / "toc")
    terms = load_dir(exp / "terms")
    lessons = load_dir(exp / "lessons")
    home_file = exp / "home" / "main.json"
    home = json.loads(home_file.read_text()) if home_file.exists() else None

    known = {lid for d in toc.values() for lid in d}
    orphans = sorted(set(lessons) - known)
    missing = sorted(known - set(lessons))
    if orphans:
        print("warning: lessons not listed in any toc:", orphans)
    if missing:
        print("note: toc entries without a lesson yet (shown as 'not written yet'):", len(missing))

    shutil.rmtree(out / "data", ignore_errors=True)
    dump(out / "data" / "toc.json", toc)
    dump(out / "data" / "terms.json", terms)
    if home:
        dump(out / "data" / "home.json", home)
    by_domain = {}
    for lid, doc in lessons.items():
        by_domain.setdefault(doc.get("d", "misc"), {})[lid] = doc
    for dom, bundle in by_domain.items():
        dump(out / "data" / "lessons" / f"{dom}.json", bundle)

    page = Path(a.template).read_text()
    page = must_replace(page, "<title>The Engineer's Atlas</title>", HEAD.format(nl=len(lessons), nt=len(terms)), "title")
    page = must_replace(page, 'window.addEventListener("hashchange",route);side();route();', 'window.addEventListener("hashchange",route);', "initial route call")
    page, n = re.subn(r"if\(window\.claude&&claude\.use\)\{.*?\n</script>", lambda m: SHIM, page, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("template changed: could not find the claude.use block. Update build_site.py before publishing.")
    built = datetime.date.today().isoformat()
    page = must_replace(page, '<aside id="dr" hidden></aside>',
                        '<aside id="dr" hidden></aside><footer style="max-width:1180px;margin:0 auto;padding:0 28px 40px;color:var(--mut);font-size:13px">'
                        f'Built {built}. Your progress and "known" flags are saved in this browser only.</footer>', "drawer")
    (out / "index.html").write_text(page)
    (out / ".nojekyll").write_text("\n")
    (out / "tools").mkdir(exist_ok=True)
    shutil.copy(__file__, out / "tools" / "build_site.py")
    (out / "README.md").write_text(f"""# The Engineer's Atlas

A free, hands-on map of software engineering: {len(lessons)} lessons with runnable examples and {len(terms)} linked terms,
from the command line and networking to cloud, security and AI. Every lesson says what was verified and what was not.

Live site: enable GitHub Pages for this repository (Settings, Pages, Deploy from branch, `main`, `/ (root)`).

## Run it locally

```
python3 -m http.server 8000
```

Then open http://localhost:8000 (opening `index.html` directly will not work because the page fetches `data/*.json`).

## How the site is built

The content lives in the Atlas artifact database; `tools/build_site.py` turns an export of it into the static files here.
Last build: {built}. Do not edit `data/` by hand; it is regenerated.
""")
    print(f"built {len(lessons)} lessons, {len(terms)} terms, {len(by_domain)} lesson bundles into {out}")


if __name__ == "__main__":
    main()
