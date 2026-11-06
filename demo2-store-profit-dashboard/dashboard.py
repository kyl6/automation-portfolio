#!/usr/bin/env python3
"""Build an offline profit dashboard from a supported Shopify CSV subset."""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZERO = Decimal('0')


def amount(value):
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f'Invalid amount: {value!r}') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Amounts must be finite and nonnegative')
    return result


def read_csv(path, required):
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if not set(required) <= set(reader.fieldnames or []):
            raise ValueError(f'Missing columns in {Path(path).name}')
        rows = list(reader)
    if not rows:
        raise ValueError('Empty input')
    return rows


def keyed_costs(path, key, fields):
    result = {}
    for row in read_csv(path, [key, *fields]):
        if not row[key] or row[key] in result:
            raise ValueError('Missing or duplicate cost key')
        result[row[key]] = {field: amount(row[field]) for field in fields}
    return result


def summarize(path, costs_path=ROOT / 'product_costs.csv', expenses_path=ROOT / 'order_expenses.csv'):
    costs = keyed_costs(costs_path, 'sku', ['unit_cost'])
    expenses = keyed_costs(expenses_path, 'order', ['fees', 'shipping_cost'])
    required = ['Name', 'Email', 'Currency', 'Financial Status', 'Subtotal', 'Shipping',
                'Taxes', 'Total', 'Discount Amount', 'Refunded Amount', 'Lineitem quantity',
                'Lineitem name', 'Lineitem price', 'Lineitem sku']
    orders = {}
    for row in read_csv(path, required):
        name = row['Name']
        if not name:
            raise ValueError('Every line must have an order Name')
        if row['Currency']:
            if name in orders:
                raise ValueError('Duplicate order header')
            if row['Currency'] != 'USD' or row['Financial Status'] not in ('paid', 'refunded', 'partially_refunded'):
                raise ValueError('Only USD paid/refunded orders are supported')
            orders[name] = dict(customer=row['Email'].strip().lower(), lines=[],
                                **{field: amount(row[field]) for field in required[4:10]})
            if not orders[name]['customer']:
                raise ValueError('Email is required for customer counts')
        elif name not in orders:
            raise ValueError('Continuation line precedes order header')
        elif any(row[field] for field in required[1:10]):
            raise ValueError('Continuation order-level fields must be blank')
        quantity = amount(row['Lineitem quantity'])
        if quantity == 0 or quantity != quantity.to_integral_value():
            raise ValueError('Quantity must be a positive integer')
        sku = row['Lineitem sku']
        if sku not in costs or name not in expenses:
            raise ValueError('Missing product cost or order expense')
        orders[name]['lines'].append((sku, row['Lineitem name'], quantity * amount(row['Lineitem price']),
                                      quantity * costs[sku]['unit_cost']))
    totals = defaultdict(lambda: ZERO)
    products = defaultdict(lambda: defaultdict(lambda: ZERO))
    customers = Counter()
    for name, order in orders.items():
        gross = sum((line[2] for line in order['lines']), ZERO)
        discount, refund = order['Discount Amount'], order['Refunded Amount']
        subtotal = gross - discount
        if gross <= 0 or subtotal < 0 or subtotal != order['Subtotal']:
            raise ValueError('Line totals less discounts must match Subtotal and gross must be positive')
        if order['Total'] != subtotal + order['Shipping'] + order['Taxes']:
            raise ValueError('Total does not reconcile')
        if refund > subtotal:
            raise ValueError('This demo supports merchandise-only refunds up to Subtotal')
        fees, shipping_cost = expenses[name]['fees'], expenses[name]['shipping_cost']
        cogs = sum((line[3] for line in order['lines']), ZERO)
        net = subtotal - refund
        gross_profit = net - cogs
        profit = gross_profit + order['Shipping'] - fees - shipping_cost
        values = dict(gross_sales=gross, discounts=discount, refunds=refund, net_sales=net,
                      cogs=cogs, gross_profit=gross_profit, shipping_collected=order['Shipping'],
                      fees=fees, shipping_cost=shipping_cost, profit=profit, aov_sales=subtotal)
        for field, value in values.items():
            totals[field] += value
        totals['refunded_orders'] += int(refund > 0)
        customers[order['customer']] += 1
        for sku, title, revenue, cost in order['lines']:
            share = revenue / gross
            product = products[sku]
            product['name'] = title
            product['net_sales'] += (subtotal - refund) * share
            product['cogs'] += cost
            product['profit'] += (subtotal - refund + order['Shipping'] - fees - shipping_cost) * share - cost
    totals.update(orders=len(orders), customers=len(customers), repeat=sum(n > 1 for n in customers.values()),
                  products=dict(products), aov=totals['aov_sales'] / len(orders))
    totals['repeat_rate'] = Decimal(totals['repeat']) / len(customers) * 100
    return dict(totals)


def money(value):
    return f'${value:,.2f}'


def render(data):
    cards = [('Orders', str(data['orders'])), ('Net merchandise sales', money(data['net_sales'])),
             ('Gross profit', money(data['gross_profit'])), ('Profit after fees & shipping', money(data['profit'])),
             ('AOV before refunds', money(data['aov'])), ('Refunds', money(data['refunds'])),
             ('Refunded orders', str(data['refunded_orders'])),
             ('Repeat customers', f"{data['repeat_rate']:.1f}% ({data['repeat']}/{data['customers']})")]
    tiles = ''.join(f'<article><h2>{escape(label)}</h2><strong>{value}</strong></article>' for label, value in cards)
    rows, bars = [], []
    scale = max([abs(p['profit']) for p in data['products'].values()] + [Decimal(1)])
    for index, (sku, product) in enumerate(sorted(data['products'].items())):
        title = escape(product['name'])
        rows.append(f'<tr><th scope="row">{title} ({escape(sku)})</th>' + ''.join(
            f'<td>{money(product[field])}</td>' for field in ['net_sales', 'cogs', 'profit']) + '</tr>')
        width = float(abs(product['profit']) / scale * 180)
        x = 400 - width if product['profit'] < 0 else 400
        y = 35 + index * 50
        bars.append(f'<text x="10" y="{y+18}">{title}</text><rect x="{x}" y="{y}" width="{width}" height="26" fill="{"#b42318" if product["profit"] < 0 else "#087f70"}"/><text x="600" y="{y+18}">{money(product["profit"])}</text>')
    bridge = ''.join(f'<li>{label}: <b>{money(data[field])}</b></li>' for label, field in [
        ('Gross merchandise sales', 'gross_sales'), ('Less discounts', 'discounts'), ('Less refunds', 'refunds'),
        ('Less product costs', 'cogs'), ('Plus shipping collected', 'shipping_collected'),
        ('Less fees', 'fees'), ('Less shipping paid', 'shipping_cost')])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Store profit dashboard | Fake sample</title><style>
*{{box-sizing:border-box}}body{{font:16px system-ui,sans-serif;color:#18352f;background:#f3f6f3;margin:0;padding:32px}}main{{max-width:1100px;margin:auto}}h1{{font-size:38px;margin-bottom:8px}}h2{{font-size:16px}}.notice{{color:#854d0e;font-weight:bold}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:28px 0}}article,section{{background:white;padding:22px;border:1px solid #dce5de;border-radius:12px}}strong{{font-size:27px}}section{{margin:20px 0}}svg{{width:100%;height:auto;min-width:620px}}.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:right;padding:12px;border-bottom:1px solid #dce5de}}th:first-child{{text-align:left}}li{{margin:8px 0}}.notes{{line-height:1.6;color:#465b55}}
</style></head><body><main><p class="notice">FAKE SAMPLE DATA · USD · All orders in supplied export</p>
<h1>Store profit dashboard</h1><p>See what remains after product costs, refunds, fees and shipping.</p>
<div class="cards">{tiles}</div><section><h2>Profit by product after fees and shipping</h2><div class="scroll">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 {len(bars)*50+45}" role="img" aria-label="Profit by product in USD"><title>Profit by product after fees and shipping</title>{''.join(bars)}</svg>
<table><thead><tr><th>Product</th><th>Net sales</th><th>Product cost</th><th>Profit</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section><h2>From sales to profit</h2><ul>{bridge}</ul><p><b>Profit after fees and shipping: {money(data['profit'])}</b></p></section>
<p class="notes">Gross profit = merchandise sales − discounts − refunds − product costs. Profit adds shipping collected and subtracts fees and shipping paid. Taxes are excluded; ads, overhead and income taxes are not modeled. AOV = merchandise sales after discounts, before refunds, divided by unique orders. Repeat rate = customers with multiple orders / identified customers in this sample. Order discounts, refunds, fees and shipping are allocated to products by pre-discount sales share. Refunded stock is not credited back to product costs. All inputs are fictional; this is a supported Shopify export subset, not a live store connection.</p>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'sample_orders.csv')
    parser.add_argument('--costs', type=Path, default=ROOT / 'product_costs.csv')
    parser.add_argument('--expenses', type=Path, default=ROOT / 'order_expenses.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'dashboard.html')
    args = parser.parse_args()
    try:
        data = summarize(args.input, args.costs, args.expenses)
        args.output.write_text(render(data), encoding='utf-8')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(f"{data['orders']} orders; gross profit {money(data['gross_profit'])}; after fees/shipping {money(data['profit'])}")


if __name__ == '__main__':
    main()
