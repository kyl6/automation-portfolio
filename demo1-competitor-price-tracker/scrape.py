#!/usr/bin/env python3
"""Read three practice bookstore pages and export CSV; optionally sync a sheet."""
import argparse
import base64
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urljoin

from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
FIELDS = ["title", "price", "rating", "stock", "url"]
BASE = "https://books.toscrape.com/"
RATINGS = dict(zip(["One", "Two", "Three", "Four", "Five"], range(1, 6)))


class BookParser(HTMLParser):
    """Extract only product cards, preserving decoded titles and relative links."""
    def __init__(self, page_url):
        super().__init__()
        self.page_url = page_url
        self.rows = []
        self.card = None
        self.in_heading = False
        self.capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "article" and "product_pod" in classes:
            self.card = {}
        if self.card is None:
            return
        if tag == "h3":
            self.in_heading = True
        if tag == "a" and self.in_heading:
            self.card.update(title=attrs.get("title", ""), url=urljoin(self.page_url, attrs.get("href", "")))
        if "star-rating" in classes:
            self.card["rating"] = next((RATINGS[c] for c in classes if c in RATINGS), None)
        if tag == "p":
            self.capture = "price" if "price_color" in classes else "stock" if "availability" in classes else None
            if self.capture:
                self.card[self.capture] = ""

    def handle_data(self, data):
        if self.card is not None and self.capture:
            self.card[self.capture] += data

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_heading = False
        if tag == "p":
            self.capture = None
        if tag == "article" and self.card is not None:
            if not all(self.card.get(field) for field in FIELDS):
                raise ValueError("Incomplete book card; site layout may have changed")
            self.card["price"] = self.card["price"].strip().removeprefix("£")
            self.card["stock"] = " ".join(self.card["stock"].split())
            self.rows.append(self.card)
            self.card = None


def scrape():
    rows = []
    for page in range(1, 4):
        url = urljoin(BASE, f"catalogue/page-{page}.html")
        request = Request(url, headers={"User-Agent": "PortfolioBookDemo/1.0 (practice-site-only)"})
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8")
        parser = BookParser(url)
        parser.feed(html)
        parser.close()
        if len(parser.rows) != 20:
            raise ValueError(f"Expected 20 books on page {page}; site layout may have changed")
        rows.extend(parser.rows)
        if page < 3:
            time.sleep(1)
    return rows


def post_json(url, data, headers=None, method="POST"):
    request = Request(url, data=json.dumps(data).encode(), method=method,
                      headers={"Content-Type": "application/json", **(headers or {})})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def sheet_config():
    """Called only on explicit --sheet; credentials never enter the repository."""
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not path or not sheet_id:
        raise ValueError("--sheet requires GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_SHEET_ID")
    if not shutil.which("openssl"):
        raise ValueError("--sheet requires the openssl command for service-account signing")
    account = json.loads(Path(path).expanduser().read_text())
    if account.get("type") != "service_account" or not all(account.get(k) for k in ("client_email", "private_key")):
        raise ValueError("Expected a service-account JSON file")
    return account, sheet_id


def push_sheet(rows, account, sheet_id):
    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=")

    now = int(time.time())
    claims = {"iss": account["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets",
              "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600}
    signing_input = b".".join(encode(json.dumps(x).encode()) for x in ({"alg": "RS256", "typ": "JWT"}, claims))
    with tempfile.TemporaryDirectory() as directory:
        key_path = Path(directory) / "key.pem"
        key_path.write_text(account["private_key"])
        key_path.chmod(0o600)
        signed = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key_path)],
                                input=signing_input, capture_output=True, check=True).stdout
    assertion = (signing_input + b"." + encode(signed)).decode()
    request = Request("https://oauth2.googleapis.com/token", data=urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(request, timeout=30) as response:
        token = json.load(response)["access_token"]
    # Fixed 60-book export, with blanks to clear stale rows from previous runs.
    values = [FIELDS] + [[row[field] for field in FIELDS] for row in rows]
    values += [[""] * len(FIELDS) for _ in range(max(0, 61 - len(values)))]
    post_json(f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Books!A1:E{len(values)}?valueInputOption=RAW",
              {"values": values}, {"Authorization": f"Bearer {token}"}, method="PUT")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", action="store_true", help="Also replace the Books tab export (requires environment setup)")
    args = parser.parse_args()
    try:
        config = sheet_config() if args.sheet else None
        rows = scrape()
        output = ROOT / "output" / "books.csv"
        output.parent.mkdir(exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved {len(rows)} books to {output}")
        if config:
            push_sheet(rows, *config)
            print("Updated Google Sheets Books tab")
    except (OSError, ValueError, KeyError, AttributeError, URLError, subprocess.SubprocessError) as exc:
        # Do not print provider responses or credentials.
        parser.exit(1, f"Export failed: {exc if isinstance(exc, ValueError) else type(exc).__name__}. Check network and optional Sheets setup.\n")


if __name__ == "__main__":
    main()
