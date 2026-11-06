# Store profit dashboard

Saves a store owner assembling separate sales, cost and refund spreadsheets. Built with AI tools; chat-only handoff, no calls.

```sh
python3 demo2-store-profit-dashboard/dashboard.py
```

Run from the repository root; open [dashboard.html](dashboard.html). Fully offline, self-contained HTML with inline SVG and no external assets.

## Fake inputs and supported scope

All inputs are **FAKE SAMPLE DATA**, not store or client results:

- [sample_orders.csv](sample_orders.csv): four orders, five product lines, three fictional customer emails. Uses a subset of [Shopify order-export columns](https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders). Order-level values appear on the first line only; the order `Name` repeats on continuation lines.
- [product_costs.csv](product_costs.csv): unit cost by SKU.
- [order_expenses.csv](order_expenses.csv): actual-style fee and outbound shipping amounts per order, supplied separately because these are not product costs in the order export.

The demo accepts USD paid/refunded orders only. It rejects missing cost mappings, duplicate headers, inconsistent totals, invalid numbers and malformed continuation rows. Export columns beyond the supported subset are ignored. This is not a general importer: edited/canceled orders, tax/shipping refunds, restocked returns and other currencies need additional mapping. Shopify, TikTok Shop and Amazon integrations are separately scoped.

## Metric definitions

- Net merchandise sales = quantity × line price − order discounts − merchandise refunds.
- Gross profit = net merchandise sales − product costs.
- Profit after fees and shipping = gross profit + shipping collected − fees − shipping paid. Ads, overhead and income taxes are excluded.
- Profit by product allocates order discounts, refunds, fees and shipping by pre-discount merchandise sales share. This is an estimate when refunds concern a specific item. Product costs are retained for refunded items; no assumed restocking recovery.
- AOV = merchandise sales after discounts, before refunds / unique orders. Excludes shipping and taxes.
- Refunds show merchandise refund dollars and the count of refunded orders.
- Repeat-customer rate = emails with more than one unique order / all identified customer emails in the export. It is a sample-period rate, not lifetime retention; refunded orders still count.

The sample reconciles to $145 net merchandise sales, $89 gross profit, $72 after fees/shipping and $41.25 AOV. One of three customers repeats. Calculations use decimal arithmetic; product allocations retain precision until display rounding.

```sh
python3 demo2-store-profit-dashboard/dashboard.py --input orders.csv --costs costs.csv --expenses expenses.csv --output report.html
```

The renderer labels output as a fake demo; adapt labeling before using it for a real store.

## Loom script

- Start with the fake-data label and the store owner's profit question.
- Show Shopify-style order rows plus the separate product costs and order expenses.
- Run the dashboard and explain gross profit versus profit after fees and shipping.
- Show product profit, AOV, refunds and repeat customers, including the refund allocation assumption.
- Close with a chat-only request for an anonymized export and the metrics the seller needs.
