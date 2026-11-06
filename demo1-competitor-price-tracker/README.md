# Competitor price tracker

Saves a store owner manual price comparisons by flagging price drops and raises **strictly greater than 5%**. Kyle builds this kind of workflow with AI tools; communication is chat-only, no calls.

## Offline demo

From the repository root:

```sh
python3 demo1-competitor-price-tracker/report.py
```

Compares [yesterday.csv](yesterday.csv) and [today.csv](today.csv), writes `output/price_changes.csv`. [Saved report](sample_price_changes.csv). These are **synthetic practice snapshots**, not observed competitor changes. Prices are GBP. The names “yesterday/today” denote comparison order, not actual collection dates.

The report matches URLs, computes `(today − yesterday) / yesterday × 100`, and keeps all products. Exactly ±5% stays within the threshold. Added and missing URLs are labeled; a zero baseline gets no percentage. Invalid prices and duplicate URLs fail visibly.

```sh
python3 demo1-competitor-price-tracker/report.py --yesterday previous.csv --today current.csv --output changes.csv
```

## Optional collection and Google Sheets

```sh
python3 demo1-competitor-price-tracker/scrape.py
```

Requires internet. Reads the first three pages of **books.toscrape.com**, a practice bookstore, and writes `output/books.csv`. [Existing practice catalog sample](sample_books.csv). Save each run under a different filename before comparing; the scraper overwrites its working CSV. This demonstrates a competitor-tracking workflow; it does not scrape seller platforms.

For optional Sheets push, enable the Google Sheets API for your project, create a service account and store its JSON **outside this repository**. Share a dedicated spreadsheet with the service-account email as editor and create a tab named `Books`. Requires the system `openssl` command for signing.

```sh
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/outside/repo/service-account.json
export GOOGLE_SHEET_ID=your_spreadsheet_id
python3 demo1-competitor-price-tracker/scrape.py --sheet
```

This replaces `Books!A1:E61` with the current catalog, clearing stale rows in that range. It pushes the catalog, not the change report. [Cron example](cron.example) schedules collection only; preserve dated snapshots separately for recurring comparisons. Live scraping and Sheets were not exercised in this rewrite.

## Loom script

- Show the practice-site source and explain the competitor price-checking task.
- Open the synthetic yesterday and today snapshots.
- Run the offline report and show the drop, raise and exact 5% boundary.
- Explain how saved collection runs and the optional Google Sheet fit the workflow.
- Close with chat-only setup and the store owner's target products and desired output.
