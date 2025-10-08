
#!/usr/bin/env python3
import sys, os, json, datetime, re
from pathlib import Path

_PKG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PKG_ROOT not in sys.path: sys.path.insert(0, _PKG_ROOT)

from scripts.utils import load_yaml, ensure_dirs, write_json
from scripts.fetch_pubmed import fetch_pubmed

def _parse_date(iso):
    try:
        return datetime.date.fromisoformat(iso[:10])
    except Exception:
        return None

def _is_new_week(d):
    if not d: return False
    return (datetime.date.today() - d).days <= 7

def _is_recent_year(d):
    if not d: return False
    return (datetime.date.today() - d).days <= 365

def _classify_type(title):
    t = (title or "").lower()
    if re.search(r"\bsystematic review\b|\bmeta[- ]analysis\b|\bnetwork meta[- ]analysis\b", t):
        return "systematic_review"
    if re.search(r"\brandomi[sz]ed\b|\bcontrolled trial\b|\bplacebo[- ]controlled\b|\bdouble[- ]blind", t):
        return "trial"
    return "other"

def _classify_intervention(title):
    t = (title or "").lower()
    iv = ["intravenous iron","ferric carboxymaltose","iron derisomaltose","ferumoxytol","iron dextran","low molecular weight iron dextran","iron sucrose","ferric gluconate"]
    esa = ["methoxy polyethylene glycol-epoetin beta","epoetin alfa","epoetin zeta","darbepoetin alfa","erythropoiesis stimulating"]
    if any(k in t for k in iv): return "iv_iron"
    if any(k in t for k in esa): return "esa"
    if "bundle" in t or "patient blood management" in t or "pbm" in t: return "other_pbm"
    return "other"

def _classify_population(title):
    t = (title or "").lower()
    if any(k in t for k in ["icu","intensive care","critical care","critical illness"]):
        return "icu"
    return "other"

def build_summary(slug, title, papers):
    counts = {"new":0,"recent":0,"all":0}
    for p in papers:
        d = _parse_date(p.get("published"))
        if _is_new_week(d): counts["new"] += 1
        if _is_recent_year(d): counts["recent"] += 1
        counts["all"] += 1

    snapshot_html = f'''
<section class="tiles3">
  <a class="btn-tile" href="papers.html?slug={slug}&view=new"><span class="num">{counts['new']}</span><span class="lbl">New</span></a>
  <a class="btn-tile" href="papers.html?slug={slug}&view=recent"><span class="num">{counts['recent']}</span><span class="lbl">Recent</span></a>
  <a class="btn-tile" href="papers.html?slug={slug}&view=all"><span class="num">{counts['all']}</span><span class="lbl">All</span></a>
</section>
<p class="legal">experimental &bull; AI-assisted &bull; may contain errors &bull; read the originals</p>
'''
    return {"title": title, "counts": counts, "summary_html": snapshot_html}

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--limit", default="60")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    spec = load_yaml(args.spec)
    slug = spec["slug"]
    title = spec.get("title","lantern delta")
    ensure_dirs(root/"data"/slug, root/"logs")

    papers = [] if args.dry_run else fetch_pubmed(spec, limit=int(args.limit))

    for p in papers:
        p["type"] = _classify_type(p.get("title"))
        p["intervention"] = _classify_intervention(p.get("title"))
        p["population"] = _classify_population(p.get("title"))

    write_json(root/"data"/slug/"papers.json", {"papers": papers})
    summary = build_summary(slug, title, papers)
    write_json(root/"data"/slug/"summary.json", summary)
    print(f"Built review: {slug}  papers={len(papers)}  counts={summary['counts']}")

if __name__ == "__main__":
    main()
