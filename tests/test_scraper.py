"""Offline behavior checks: calculations, invalid inputs, parsing, and API contracts."""
import csv
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scraper = load("scraper", "demo1-competitor-price-tracker/scrape.py")

class ScraperTests(unittest.TestCase):
    def test_practice_page_card(self):
        parser = scraper.BookParser("https://books.toscrape.com/catalogue/page-1.html")
        parser.feed('''<article class="product_pod"><p class="star-rating Three"></p>
            <h3><a href="demo_1000/index.html" title="A &amp; B">A &amp; B</a></h3>
            <div class="product_price"><p class="price_color">£51.77</p>
            <p class="instock availability"><i></i> In stock </p></div></article>''')
        self.assertEqual(parser.rows, [dict(title="A & B", price="51.77", rating=3, stock="In stock",
                                          url="https://books.toscrape.com/catalogue/demo_1000/index.html")])

    def test_missing_card_fields_rejected(self):
        with self.assertRaises(ValueError):
            scraper.BookParser(scraper.BASE).feed('<article class="product_pod"></article>')

    def test_sheet_missing_config_fails_locally(self):
        with patch.dict(scraper.os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "requires"):
                scraper.sheet_config()


if __name__ == "__main__":
    unittest.main()
