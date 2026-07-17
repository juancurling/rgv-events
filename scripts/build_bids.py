#!/usr/bin/env python3
"""RGV bid-opportunity tracker — static page + spreadsheet builder.

Reads data/bids.json and generates:
  bids/index.html                 — dashboard: open bids, entity directory, platforms
  bids/rgv-open-bids.csv          — open solicitations spreadsheet
  bids/rgv-entity-directory.csv   — every RGV public entity + purchasing link + contact

Run from the repo root:  python3 scripts/build_bids.py
Idempotent: regenerates everything from current bids.json.

data/bids.json shape:
  updated: "YYYY-MM-DD"
  entities: [{name, type, county, purchasing_url, platform, contact_name,
              contact_email, contact_phone, notes}]
  open_bids: [{entity, title, bid_number, trade, due_date, url, contact, notes}]
  sources:  [{name, search_url, how_to_use, notes}]        # federal/state search pages
  platforms:[{name, url, coverage, cost, alerts, notes}]   # aggregators / plan rooms
  community:[{name, url, type, notes}]                     # FB groups, chambers, APEX
"""
import csv, io, json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "bids.json").read_text())
OUT = ROOT / "bids"
OUT.mkdir(exist_ok=True)

TYPE_LABEL = {
    "city": "Cities", "county": "Counties", "school-district": "School Districts",
    "charter": "Charter Schools", "college": "Colleges", "university": "Universities",
    "esc": "Education Service Center", "port": "Ports", "utility": "Utilities & Districts",
    "airport": "Airports", "housing": "Housing Authorities",
    "federal": "Federal", "state": "State of Texas",
}
TYPE_ORDER = ["school-district", "charter", "city", "county", "college", "university",
              "esc", "port", "utility", "airport", "housing", "federal", "state"]

TRADE_COLORS = {
    "roofing": "#e8b64c", "electrical": "#4cc27e", "drywall": "#7fa8e8",
    "insulation": "#c78fe0", "structural": "#e08f8f", "cabling": "#5fd0c9",
    "construction": "#9db8a8",
}


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def trade_key(t):
    t = (t or "").lower()
    for k in TRADE_COLORS:
        if k in t or (k == "drywall" and "sheetrock" in t) or (k == "cabling" and ("low volt" in t or "network" in t)):
            return k
    return "construction"


def write_csv(path, rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    path.write_text(buf.getvalue())


def contact_str(e):
    parts = [e.get("contact_name"), e.get("contact_email"), e.get("contact_phone")]
    return " · ".join(p for p in parts if p)


def main():
    entities = DATA.get("entities", [])
    bids = sorted(DATA.get("open_bids", []), key=lambda b: b.get("due_date") or "9999")

    write_csv(OUT / "rgv-open-bids.csv", bids,
              ["entity", "title", "bid_number", "trade", "due_date", "url", "contact", "notes"])
    write_csv(OUT / "rgv-entity-directory.csv", entities,
              ["name", "type", "county", "purchasing_url", "platform",
               "contact_name", "contact_email", "contact_phone", "notes"])

    # --- open bids table ---
    bid_rows = []
    for b in bids:
        tk = trade_key(b.get("trade"))
        link = f'<a href="{esc(b.get("url"))}" target="_blank">{esc(b.get("title"))}</a>' if b.get("url") else esc(b.get("title"))
        bid_rows.append(
            f'<tr><td>{link}<div class="sub">{esc(b.get("bid_number"))}</div></td>'
            f'<td>{esc(b.get("entity"))}</td>'
            f'<td><span class="pill" style="border-color:{TRADE_COLORS[tk]};color:{TRADE_COLORS[tk]}">{esc(b.get("trade") or "construction")}</span></td>'
            f'<td class="due">{esc(b.get("due_date"))}</td>'
            f'<td class="notes">{esc(b.get("contact"))}{" — " if b.get("contact") and b.get("notes") else ""}{esc(b.get("notes"))}</td></tr>')

    # --- entity directory grouped by type ---
    dir_sections = []
    for t in TYPE_ORDER + sorted({e.get("type") for e in entities} - set(TYPE_ORDER)):
        group = [e for e in entities if e.get("type") == t]
        if not group:
            continue
        rows = []
        for e in sorted(group, key=lambda x: (x.get("county") or "", x.get("name") or "")):
            link = f'<a href="{esc(e.get("purchasing_url"))}" target="_blank">bids page ↗</a>' if e.get("purchasing_url") else "—"
            email = e.get("contact_email")
            contact = esc(e.get("contact_name") or "")
            if email:
                contact += f'{" · " if contact else ""}<a href="mailto:{esc(email)}">{esc(email)}</a>'
            if e.get("contact_phone"):
                contact += f'{" · " if contact else ""}{esc(e.get("contact_phone"))}'
            rows.append(
                f'<tr><td>{esc(e.get("name"))}<div class="sub">{esc(e.get("county"))} County</div></td>'
                f'<td>{link}</td><td>{esc(e.get("platform"))}</td>'
                f'<td class="notes">{contact or "—"}</td>'
                f'<td class="notes">{esc(e.get("notes"))}</td></tr>')
        dir_sections.append(
            f'<h3>{esc(TYPE_LABEL.get(t, t.title()))} <span class="count">({len(group)})</span></h3>'
            f'<div class="tablewrap"><table><thead><tr><th>Entity</th><th>Bids page</th>'
            f'<th>Platform</th><th>Purchasing contact</th><th>Notes</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')

    src_rows = "".join(
        f'<tr><td><a href="{esc(s.get("search_url"))}" target="_blank">{esc(s.get("name"))} ↗</a></td>'
        f'<td class="notes">{esc(s.get("how_to_use"))}</td><td class="notes">{esc(s.get("notes"))}</td></tr>'
        for s in DATA.get("sources", []))

    plat_rows = "".join(
        f'<tr><td><a href="{esc(p.get("url"))}" target="_blank">{esc(p.get("name"))} ↗</a></td>'
        f'<td>{esc(p.get("coverage"))}</td><td>{esc(p.get("cost"))}</td>'
        f'<td class="notes">{esc(p.get("alerts"))}</td><td class="notes">{esc(p.get("notes"))}</td></tr>'
        for p in DATA.get("platforms", []))

    portal_rows = "".join(
        f'<tr><td>{esc(p.get("entity"))}</td>'
        f'<td><a href="{esc(p.get("url"))}" target="_blank">{esc(p.get("url"))}</a></td>'
        f'<td>{"✓ verified" if p.get("verified") else "see notes"}</td>'
        f'<td class="notes">{esc(p.get("notes"))}</td></tr>'
        for p in DATA.get("ionwave_portals", []))

    comm_rows = "".join(
        f'<tr><td><a href="{esc(c.get("url"))}" target="_blank">{esc(c.get("name"))} ↗</a></td>'
        f'<td>{esc(c.get("type"))}</td><td class="notes">{esc(c.get("notes"))}</td></tr>'
        for c in DATA.get("community", []))

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>RGV Bid Opportunities — updated {esc(DATA.get("updated"))}</title>
<style>
:root{{--bg:#0f1a14;--panel:#16241c;--card:#1b2c22;--line:#2a4032;--text:#eef5f0;
--muted:#9db8a8;--accent:#4cc27e;--gold:#e8b64c}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif;padding:24px}}
main{{max-width:1200px;margin:0 auto}}
h1{{font-size:1.6rem;margin-bottom:4px}} h2{{margin:36px 0 12px;color:var(--gold);font-size:1.2rem}}
h3{{margin:24px 0 8px;font-size:1.02rem}} .count{{color:var(--muted);font-weight:400}}
p.meta{{color:var(--muted);margin-bottom:8px}}
a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
.tablewrap{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}}
table{{border-collapse:collapse;width:100%;min-width:720px;font-size:.92rem}}
th{{text-align:left;padding:9px 12px;background:var(--panel);color:var(--muted);font-weight:600;white-space:nowrap}}
td{{padding:9px 12px;border-top:1px solid var(--line);vertical-align:top}}
.sub{{color:var(--muted);font-size:.8rem}} .due{{white-space:nowrap;color:var(--gold)}}
.notes{{color:var(--muted);font-size:.85rem}}
.pill{{border:1px solid;border-radius:999px;padding:1px 9px;font-size:.78rem;white-space:nowrap}}
.dl a{{margin-right:16px}} .box{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;color:var(--muted);font-size:.92rem}}
</style></head><body><main>
<h1>RGV Bid Opportunities</h1>
<p class="meta">Roofing · Electrical · Drywall · Insulation · Structural · Cabling — Hidalgo, Cameron, Willacy &amp; Starr counties. Updated {esc(DATA.get("updated"))}.</p>
<p class="dl">📥 <a href="rgv-open-bids.csv">Download open bids (CSV)</a> <a href="rgv-entity-directory.csv">Download entity directory (CSV)</a></p>

<h2>Open solicitations ({len(bids)})</h2>
<div class="tablewrap"><table><thead><tr><th>Solicitation</th><th>Entity</th><th>Trade</th><th>Due</th><th>Contact / notes</th></tr></thead>
<tbody>{"".join(bid_rows) or '<tr><td colspan="5">None on file — run a sweep.</td></tr>'}</tbody></table></div>

<h2>Where to search (federal &amp; state)</h2>
<div class="tablewrap"><table><thead><tr><th>Source</th><th>How to use</th><th>Notes</th></tr></thead><tbody>{src_rows}</tbody></table></div>

<h2>Entity directory — every RGV purchasing division</h2>
{"".join(dir_sections)}

<h2>Vendor portal registrations (register on each — free)</h2>
<div class="tablewrap"><table><thead><tr><th>Entity</th><th>Portal</th><th>Status</th><th>Notes</th></tr></thead><tbody>{portal_rows}</tbody></table></div>

<h2>Bid platforms &amp; plan rooms</h2>
<div class="tablewrap"><table><thead><tr><th>Platform</th><th>Coverage</th><th>Cost</th><th>Alerts</th><th>Notes</th></tr></thead><tbody>{plat_rows}</tbody></table></div>

<h2>Community &amp; other sources</h2>
<div class="tablewrap"><table><thead><tr><th>Source</th><th>Type</th><th>Notes</th></tr></thead><tbody>{comm_rows}</tbody></table></div>
</main></body></html>"""
    (OUT / "index.html").write_text(html)
    print(f"bids/: {len(bids)} open bids, {len(entities)} entities")


if __name__ == "__main__":
    main()
