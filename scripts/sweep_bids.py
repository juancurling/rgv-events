#!/usr/bin/env python3
"""Direct-to-website bid scraper for the RGV bid tracker.

Fetches every entity's purchasing_url from data/bids.json, scans the page for
links/headings that look like open solicitations in our trades, and writes a
review report. No third-party services — straight to each entity's own site.

Run from the repo root:  python3 scripts/sweep_bids.py
Outputs:
  data/sweep-report.json — per-entity fetch status + candidate solicitations
  (printed summary to stdout)

Candidates are leads for human/AI review, not auto-added to bids.json: gov
sites vary too much to trust blind parsing, and many block datacenter IPs
(status 'blocked' in the report) — those need a browser or manual check.
Also flags open_bids whose due_date has passed.
"""
import json, re, ssl, sys, urllib.request
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "bids.json").read_text())

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 20

# solicitation-shaped text: an RFP/bid word, or a bid-number pattern
SOLICIT = re.compile(
    r"\b(rfp|rfq|rfb|csp|ifb|itb|bid|proposal|solicitation|request for)\b", re.I)
TRADES = re.compile(
    r"\b(roof|re-?roof|electric|drywall|sheetrock|gypsum|insulat|structur|steel|"
    r"concrete|fram(?:e|ing)|cabling|low.?volt|network|fiber|e-?rate|construct|"
    r"renovat|remodel|hvac|joc|job order|cmar|building)\w*", re.I)
NOISE = re.compile(r"\b(closed|awarded|archive|result|tabulation|past|expired)\b", re.I)


class LinkScan(HTMLParser):
    """Collect (href, text) for anchors, and heading/list text without links."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self._href, self._buf = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href") or ""
            self._buf = []

    def handle_data(self, data):
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                self.links.append((self._href, text))
            self._href = None


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
        return r.read(1_500_000).decode("utf-8", "replace")


def absolutize(base, href):
    from urllib.parse import urljoin
    return urljoin(base, href)


def scan_entity(e):
    url = (e.get("purchasing_url") or "").split(" ")[0].strip()
    if not url.startswith("http"):
        return {"entity": e["name"], "status": "no-url", "candidates": []}
    try:
        html = fetch(url)
    except Exception as ex:
        kind = "blocked" if "403" in str(ex) else "error"
        return {"entity": e["name"], "status": kind, "url": url,
                "error": str(ex)[:120], "candidates": []}
    p = LinkScan()
    try:
        p.feed(html)
    except Exception:
        pass
    cands, seen = [], set()
    for href, text in p.links:
        if len(text) < 8 or NOISE.search(text):
            continue
        if SOLICIT.search(text) and TRADES.search(text):
            full = absolutize(url, href)
            if full not in seen:
                seen.add(full)
                cands.append({"title": text[:200], "url": full})
    return {"entity": e["name"], "status": "ok", "url": url, "candidates": cands}


def main():
    only = sys.argv[1].lower() if len(sys.argv) > 1 else None
    results, counts = [], {"ok": 0, "blocked": 0, "error": 0, "no-url": 0}
    for e in DATA.get("entities", []):
        if only and only not in e["name"].lower():
            continue
        r = scan_entity(e)
        counts[r["status"]] += 1
        results.append(r)
        tag = f"[{r['status']}]"
        hits = f" {len(r['candidates'])} candidate(s)" if r["candidates"] else ""
        print(f"{tag:10}{e['name']}{hits}")
        for c in r["candidates"]:
            print(f"          → {c['title'][:90]}  {c['url']}")

    stale = [b for b in DATA.get("open_bids", [])
             if re.match(r"\d{4}-\d{2}-\d{2}", b.get("due_date") or "")
             and b["due_date"][:10] < date.today().isoformat()]
    report = {"swept": datetime.now().isoformat(timespec="seconds"),
              "summary": counts, "results": results,
              "past_due_in_registry": [
                  {"entity": b["entity"], "title": b["title"],
                   "due_date": b["due_date"]} for b in stale]}
    (ROOT / "data" / "sweep-report.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    total_c = sum(len(r["candidates"]) for r in results)
    print(f"\n{counts} | {total_c} candidates | {len(stale)} past-due in registry"
          f"\n→ data/sweep-report.json")
    if counts["blocked"]:
        print("Note: 'blocked' sites refuse datacenter IPs — check those in a "
              "browser or run this from a residential connection.")


if __name__ == "__main__":
    main()
