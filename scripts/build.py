#!/usr/bin/env python3
"""Events956 static site builder.

Reads data/events.json and generates:
  event/<id>/index.html     — per-event pages with schema.org/Event JSON-LD
  city/<slug>/index.html    — city landing pages (SEO)
  category/<slug>/index.html— category landing pages (SEO)
  sitemap.xml, robots.txt

Run from the repo root:  python3 scripts/build.py
Idempotent: regenerates all pages from current events.json, removes pages for
events no longer listed.
"""
import json, re, shutil, unicodedata
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://events956.com"
TZ = "America/Chicago"

CATLABEL = {
    "run": "5K / 10K Runs", "cycling": "Cycling", "gala": "Galas & Banquets",
    "market": "Markets", "expo": "Expos", "city": "City Events",
    "nonprofit": "Nonprofit & Community", "networking": "Networking & Mixers",
    "other": "More Events",
}
# County map comes from the source registry's cities list (all RGV cities,
# Hidalgo/Cameron/Willacy/Starr counties)
_sources = json.loads((Path(__file__).resolve().parent.parent / "data" / "sources.json").read_text())
COUNTY = {c["name"]: c["county"] for c in _sources.get("cities", [])}

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))

def fmt_dt(iso):
    if not iso:
        return ""
    d = datetime.fromisoformat(iso)
    t = d.strftime("%-I:%M %p").lstrip("0")
    return f"{d.strftime('%A, %B %-d, %Y')} · {t}"

STYLE = """
:root{--bg:#0f1a14;--panel:#16241c;--card:#1b2c22;--line:#2a4032;--text:#eef5f0;
--muted:#9db8a8;--accent:#4cc27e;--gold:#e8b64c}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:var(--bg);color:var(--text);line-height:1.55}
a{color:var(--accent)}.wrap{max-width:860px;margin:0 auto;padding:0 20px}
header{padding:26px 0;border-bottom:1px solid var(--line)}
header a.logo{font-size:1.3rem;font-weight:700;color:var(--text);text-decoration:none}
header a.logo span{color:var(--accent)}
h1{font-size:1.7rem;line-height:1.25;margin:26px 0 8px}
.meta{color:var(--muted);margin:4px 0}
.badge{display:inline-block;font-size:.8rem;border:1px solid var(--line);border-radius:999px;
padding:3px 12px;color:var(--muted);margin:2px 4px 2px 0}
.badge.cat{border-color:var(--accent);color:var(--accent)}
.badge.sp{border-color:var(--gold);color:var(--gold)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin:18px 0}
.cta{display:inline-block;background:var(--accent);color:#08130c;font-weight:700;text-decoration:none;
padding:12px 22px;border-radius:10px;margin:10px 0}
ul.evlist{list-style:none;margin:20px 0}
ul.evlist li{border-bottom:1px solid var(--line);padding:14px 0}
ul.evlist .d{color:var(--accent);font-size:.85rem;text-transform:uppercase;letter-spacing:.06em}
footer{margin-top:60px;padding:26px 0;border-top:1px solid var(--line);color:var(--muted);
font-size:.85rem;text-align:center}
"""

def page(title, desc, canonical, body, jsonld=None):
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
{ld}<style>{STYLE}</style>
</head>
<body>
<header><div class="wrap"><a class="logo" href="/">Events<span>956</span></a></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">Events956.com — The Rio Grande Valley's event calendar. Free for everyone, always.</div></footer>
</body>
</html>"""

def event_jsonld(e):
    ld = {
        "@context": "https://schema.org", "@type": "Event",
        "name": e["title"], "startDate": e["start"],
        "description": e.get("description", ""),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "url": f"{BASE}/event/{e['id']}/",
        "location": {
            "@type": "Place", "name": e.get("venue") or e.get("city", ""),
            "address": {"@type": "PostalAddress",
                        "streetAddress": e.get("address", ""),
                        "addressLocality": e.get("city", ""),
                        "addressRegion": "TX", "addressCountry": "US"},
        },
    }
    if e.get("end"):
        ld["endDate"] = e["end"]
    if e.get("image"):
        ld["image"] = [e["image"]]
    org = e.get("organization") or e.get("source")
    if org:
        ld["organizer"] = {"@type": "Organization", "name": org}
    price = (e.get("price") or "").strip()
    if price.lower() == "free" or price.lower().startswith("free"):
        ld["isAccessibleForFree"] = True
        ld["offers"] = {"@type": "Offer", "price": "0", "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock", "url": e.get("url", "")}
    return ld

def event_page(e):
    cat = CATLABEL.get(e.get("category", "other"), "Event")
    when = fmt_dt(e.get("start"))
    county = COUNTY.get(e.get("city", ""), "")
    badges = f'<span class="badge cat">{esc(cat)}</span>'
    if e.get("price"):
        badges += f'<span class="badge">{esc(e["price"])}</span>'
    if e.get("sponsorship"):
        badges += '<span class="badge sp">★ Sponsorship / vendor opportunities</span>'
    if e.get("booth"):
        badges += '<span class="badge sp">🏪 Booth space available</span>'
    where = " · ".join(x for x in [e.get("venue"), e.get("address") or e.get("city")] if x)
    src = f'<p class="meta">Source: {esc(e.get("source",""))}</p>' if e.get("source") else ""
    link = f'<a class="cta" href="{esc(e["url"])}" target="_blank" rel="noopener">Official page & registration →</a>' if e.get("url") else ""
    body = f"""
<h1>{esc(e['title'])}</h1>
<p class="meta">{esc(when)}</p>
<p class="meta">{esc(where)}</p>
<div>{badges}</div>
<div class="panel"><p>{esc(e.get('description',''))}</p></div>
{link}
{src}
<p class="meta"><a href="/city/{slugify(e.get('city','rgv'))}/">More events in {esc(e.get('city','the RGV'))}</a> ·
<a href="/category/{e.get('category','other')}/">More {esc(cat)}</a> · <a href="/">All RGV events</a></p>
"""
    desc = f"{e['title']} — {when} at {e.get('venue') or e.get('city','')}. {e.get('description','')[:140]}"
    title = f"{e['title']} | {e.get('city','RGV')} | Events956"
    return page(title, desc, f"{BASE}/event/{e['id']}/", body, event_jsonld(e))

def listing_page(kind, key, label, events):
    items = ""
    for e in sorted(events, key=lambda x: x["start"]):
        d = datetime.fromisoformat(e["start"])
        items += f"""<li><div class="d">{d.strftime('%a %b %-d, %Y')}</div>
<a href="/event/{e['id']}/">{esc(e['title'])}</a>
<div class="meta">{esc(e.get('venue',''))}{' · ' + esc(e['city']) if e.get('city') else ''}</div></li>"""
    if kind == "city":
        h1, desc = f"Events in {label}, TX", f"Upcoming events in {label}, Texas — updated continuously. Free community calendar by Events956."
    else:
        h1, desc = f"{label} in the Rio Grande Valley", f"Upcoming {label.lower()} across the RGV — McAllen, Edinburg, Harlingen, Brownsville and more."
    body = f"<h1>{esc(h1)}</h1><p class='meta'>{len(events)} upcoming</p><ul class='evlist'>{items}</ul><p><a href='/'>← All RGV events</a></p>"
    return page(f"{h1} | Events956", desc, f"{BASE}/{kind}/{key}/", body)

def main():
    data = json.loads((ROOT / "data" / "events.json").read_text())
    today = date.today().isoformat()
    events = [e for e in data["events"] if (e.get("end") or e.get("start", ""))[:10] >= today]

    # Schema v2 soft defaults (never invent facts; only structural fields)
    for e in events:
        e.setdefault("tags", sorted({e.get("category", "other"), slugify(e.get("city", ""))} - {""}))
        e.setdefault("organization", e.get("source", ""))
        e.setdefault("county", COUNTY.get(e.get("city", ""), ""))
        e.setdefault("confidence", "high" if e.get("verified") else "medium")
        e.setdefault("recurring", False)

    # Clean regenerate
    for d in ("event", "city", "category"):
        shutil.rmtree(ROOT / d, ignore_errors=True)

    urls = [f"{BASE}/"]
    for e in events:
        p = ROOT / "event" / e["id"]
        p.mkdir(parents=True)
        (p / "index.html").write_text(event_page(e))
        urls.append(f"{BASE}/event/{e['id']}/")

    cities = {}
    for e in events:
        if e.get("city"):
            cities.setdefault(e["city"], []).append(e)
    for city, evs in cities.items():
        s = slugify(city)
        p = ROOT / "city" / s
        p.mkdir(parents=True)
        (p / "index.html").write_text(listing_page("city", s, city, evs))
        urls.append(f"{BASE}/city/{s}/")

    for cat, label in CATLABEL.items():
        evs = [e for e in events if e.get("category") == cat]
        if not evs:
            continue
        p = ROOT / "category" / cat
        p.mkdir(parents=True)
        (p / "index.html").write_text(listing_page("category", cat, label, evs))
        urls.append(f"{BASE}/category/{cat}/")

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
    sitemap += "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sitemap)
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")

    # Persist schema v2 fields back to events.json
    (ROOT / "data" / "events.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))

    print(f"Built {len(events)} event pages, {len(cities)} city pages, "
          f"{len([c for c in CATLABEL if (ROOT/'category'/c).exists()])} category pages, sitemap ({len(urls)} URLs)")

if __name__ == "__main__":
    main()
