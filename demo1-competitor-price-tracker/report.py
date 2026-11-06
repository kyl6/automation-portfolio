#!/usr/bin/env python3
"""Compare price snapshots offline, matching products by URL."""
import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = ['title', 'url', 'yesterday', 'today', 'change_percent', 'flag']


def read_snapshot(path):
    products = {}
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if not {'title', 'url', 'price'} <= set(reader.fieldnames or []):
            raise ValueError('Snapshot requires title, url, price')
        for row in reader:
            key = row['url']
            try:
                price = Decimal(row['price'])
            except (InvalidOperation, TypeError) as exc:
                raise ValueError('Invalid price') from exc
            if not key or key in products or not price.is_finite() or price < 0:
                raise ValueError('Duplicate/missing URL or invalid price')
            products[key] = (row['title'], price)
    if not products:
        raise ValueError('Empty snapshot')
    return products


def compare(yesterday, today):
    old, new = read_snapshot(yesterday), read_snapshot(today)
    rows = []
    for url in sorted(old.keys() | new.keys()):
        title = (new.get(url) or old[url])[0]
        before = old[url][1] if url in old else None
        after = new[url][1] if url in new else None
        percent = None
        if before is None:
            flag = 'new'
        elif after is None:
            flag = 'missing'
        elif before == 0:
            flag = 'unchanged' if after == 0 else 'no baseline'
        else:
            percent = (after - before) / before * 100
            flag = 'drop >5%' if percent < -5 else 'raise >5%' if percent > 5 else 'within 5%'
        rows.append(dict(title=title, url=url, yesterday=before if before is not None else '',
                         today=after if after is not None else '',
                         change_percent=f'{percent:.2f}' if percent is not None else '', flag=flag))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--yesterday', type=Path, default=ROOT / 'yesterday.csv')
    parser.add_argument('--today', type=Path, default=ROOT / 'today.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/price_changes.csv')
    args = parser.parse_args()
    try:
        rows = compare(args.yesterday, args.today)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(f'{len(rows)} products compared; report: {args.output}')


if __name__ == '__main__':
    main()
