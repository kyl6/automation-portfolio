# AI automation for online sellers

I'm Kyle, an **AI automation builder**. I build with AI tools to help Shopify, TikTok Shop and Amazon sellers spend less time checking prices, assembling reports and sorting customer messages.

Work is **chat-only, no calls**, with written updates and Loom walkthroughs. These are practice demos, not client results or measured savings. Platform names describe the intended audience; these samples do not connect to live seller accounts.

- [Competitor price tracker](demo1-competitor-price-tracker/): saves a store owner manual price-checking and comparison work. Compare two saved runs and flag drops or raises over 5%; optionally collect practice-site prices and push them to Google Sheets.
- [Store profit dashboard](demo2-store-profit-dashboard/): saves a store owner spreadsheet assembly when checking product costs, fees, shipping and refunds. Includes a fake Shopify-format export and a [self-contained dashboard](demo2-store-profit-dashboard/dashboard.html).
- [AI review & customer message triage](demo3-review-message-triage/): saves a store owner a first sorting and reply-drafting pass. Includes 18 fake messages, priorities and drafts for human review; offline rules by default, optional AI mode.

## Run all three offline

Python 3.11+ and its standard library only. No install, API keys or network needed. From this repository:

```sh
python3 demo1-competitor-price-tracker/report.py
python3 demo2-store-profit-dashboard/dashboard.py
python3 demo3-review-message-triage/triage.py
python3 -m unittest discover -s tests -v
```

Open `demo2-store-profit-dashboard/dashboard.html` in a browser. CSV reports go into each demo's `output/` directory. Saved public report examples are linked in each demo README.

## Scope and handoff

The price scraper uses **books.toscrape.com**, a practice bookstore, not Shopify, TikTok Shop or Amazon scraping. The dashboard supports a documented Shopify export subset; other platforms need an agreed mapping. Message channels are fictional labels, not integrations. Reply drafts are never sent automatically.

Optional live scraping, Google Sheets and paid LLM usage require explicit commands and setup. Google Sheets signing uses the system `openssl` command; Python requires no third-party packages. Keep keys and service-account files outside this repository. Generated working outputs and credentials are ignored.

Each demo README includes a five-bullet Loom script. Samples and tests run offline; live API integrations require separate verification with the intended account.
