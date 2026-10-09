#!/usr/bin/env python3
"""Submit every URL in sitemap.xml to the IndexNow API (Bing, Yandex, Seznam, etc.)
so new/changed pages get crawled quickly instead of waiting for organic discovery.

Usage: python3 scripts/indexnow_submit.py
Requires the INDEXNOW_KEY env var (also the filename of the key file served at
the site root, e.g. https://events956.com/<key>.txt).
"""
import json
import os
import re
import sys
import urllib.request

HOST = "events956.com"
KEY = os.environ.get("INDEXNOW_KEY")
SITEMAP = "sitemap.xml"
ENDPOINT = "https://api.indexnow.org/indexnow"


def main():
    if not KEY:
        print("INDEXNOW_KEY env var not set", file=sys.stderr)
        sys.exit(1)

    xml = open(SITEMAP, encoding="utf-8").read()
    urls = re.findall(r"<loc>(.*?)</loc>", xml)
    if not urls:
        print("No URLs found in sitemap.xml", file=sys.stderr)
        sys.exit(1)

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"IndexNow: submitted {len(urls)} URLs, status {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"IndexNow HTTP error {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
