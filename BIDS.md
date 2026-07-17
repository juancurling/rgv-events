# RGV Bid Opportunity Tracker

Companion system to the events site. Finds and consolidates public construction
bid opportunities (roofing, electrical, drywall, insulation, structural,
low-voltage cabling) across the Rio Grande Valley.

## Pieces

- `data/bids.json` — the registry: every RGV purchasing division (cities, counties,
  ISDs, charters, colleges, ports, utilities, housing authorities), current open
  solicitations, federal/state search URLs, bid platforms, and community sources.
- `scripts/build_bids.py` — regenerates `bids/index.html` (dashboard, noindex) plus
  `bids/rgv-open-bids.csv` and `bids/rgv-entity-directory.csv` from the registry.
- Live at `https://events956.com/bids/` once merged to main (GitHub Pages).

## Weekly sweep (how to refresh)

0. Run the direct scraper: `python3 scripts/sweep_bids.py` (optionally filter:
   `python3 scripts/sweep_bids.py mcallen`). It fetches every entity's purchasing
   page directly, flags candidate solicitations in our trades, and writes
   `data/sweep-report.json`. Run it from a normal (residential/office) connection —
   cloud/datacenter IPs get 403-blocked by most government sites, including the
   Claude Code cloud sandbox.
1. For entities the scraper reports as `blocked` (or portals that need login/JS —
   IonWave, Bonfire, OpenGov, BidNet), check the `purchasing_url`/portal manually
   for new solicitations matching the six trades + general construction/CSP/JOC.
   Highest-volume sources first: Hidalgo County OpenGov, city ProcureWare portals
   (McAllen/Pharr/Mission), Brownsville Bonfire, the ISD IonWave portals,
   BidNet (Weslaco/Cameron County), Region One eBuyOne, IDEA bids page.
2. Check texaspublicnotices.com for "notice to bidders" in The Monitor, Valley
   Morning Star, Brownsville Herald, Progress Times (catches small entities with
   no portal).
3. Check SAM.gov saved searches (city keywords + NAICS 236220/238160/238210/238310/238120),
   ESBD, and TxDOT Pharr District lettings.
4. Update `open_bids` in `data/bids.json` (drop past-due, add new), bump `updated`,
   run `python3 scripts/build_bids.py`, commit.

Note: many gov sites 403-block datacenter fetches; solicitations found via search
indexes are flagged in `notes` as unverified — always confirm due dates on the
entity's own portal before pursuing.

## One-time registrations that do most of the work

Free vendor registrations (each emails you matching bids automatically):
ProcureWare (McAllen, Pharr, Mission), OpenGov (Hidalgo County, Edinburg, STC),
IonWave (McAllen ISD, BISD, HCISD `hcisdbid`, PSJA `psjaebid`, Weslaco ISD,
La Joya ISD, Sharyland ISD), Bonfire (Brownsville, Mission CISD, TSC, UTRGV),
BidNet Texas Purchasing Group (Weslaco, Cameron County, Port of Brownsville, BPUB,
Harlingen WaterWorks), DemandStar, Public Purchase, Region One eBuyOne, CivCastUSA.
Paid/membership: RGV AGC plan room (Pharr/Brownsville), CMBL ($70/yr) + free HUB certification.
UTRGV APEX Accelerator (free) sends daily bid-match emails: apex@utrgv.edu, (956) 665-7550.
