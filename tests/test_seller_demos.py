"""Offline checks for financial reconciliation, thresholds and draft-only triage."""
import csv
from decimal import Decimal
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, folder, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / folder / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = load('report', 'demo1-competitor-price-tracker', 'report.py')
dashboard = load('dashboard', 'demo2-store-profit-dashboard', 'dashboard.py')
triage = load('triage', 'demo3-review-message-triage', 'triage.py')


def write_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class PriceTests(unittest.TestCase):
    def test_sample_and_saved_report(self):
        rows = report.compare(report.ROOT / 'yesterday.csv', report.ROOT / 'today.csv')
        self.assertCountEqual([row['flag'] for row in rows], ['drop >5%', 'raise >5%', 'within 5%', 'within 5%'])
        with (report.ROOT / 'sample_price_changes.csv').open() as handle:
            self.assertEqual(list(csv.DictReader(handle)), [{k: str(v) for k, v in row.items()} for row in rows])

    def test_thresholds_new_missing_and_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            old, new = Path(folder) / 'old.csv', Path(folder) / 'new.csv'
            def row(url, price):
                return dict(url=url, title=url, price=price)
            write_csv(old, [row('drop', '100'), row('raise', '100'), row('zero', '0'), row('gone', '3')])
            write_csv(new, [row('drop', '95'), row('raise', '105'), row('zero', '1'), row('added', '3')])
            values = {r['url']: r for r in report.compare(old, new)}
            self.assertEqual(values['drop']['flag'], 'within 5%')
            self.assertEqual(values['raise']['flag'], 'within 5%')
            self.assertEqual(values['zero']['flag'], 'no baseline')
            self.assertEqual(values['gone']['flag'], 'missing')
            self.assertEqual(values['added']['flag'], 'new')
            write_csv(new, [row('drop', '94.999'), row('raise', '105.001')])
            flags = {r['url']: r['flag'] for r in report.compare(old, new)}
            self.assertEqual(flags['drop'], 'drop >5%')
            self.assertEqual(flags['raise'], 'raise >5%')

    def test_invalid_snapshots(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.csv'
            for body in ['title,url,price\n', 'title,url,price\nx,u,NaN\n',
                         'title,url,price\nx,u,-1\n', 'title,url,price\nx,u,2\nx,u,3\n']:
                path.write_text(body)
                with self.assertRaises(ValueError):
                    report.read_snapshot(path)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        with (dashboard.ROOT / 'sample_orders.csv').open() as handle:
            self.rows = list(csv.DictReader(handle))

    def test_independent_expected_totals(self):
        data = dashboard.summarize(dashboard.ROOT / 'sample_orders.csv')
        expected = dict(orders=4, customers=3, repeat=1, gross_sales=175, discounts=10,
                        refunds=20, net_sales=145, cogs=56, gross_profit=89, profit=72,
                        fees=6, shipping_cost=26, shipping_collected=15, refunded_orders=1)
        for field, value in expected.items():
            self.assertEqual(data[field], value, field)
        self.assertEqual(data['aov'], Decimal('41.25'))
        self.assertAlmostEqual(float(data['repeat_rate']), 100 / 3)
        self.assertAlmostEqual(sum(p['profit'] for p in data['products'].values()), Decimal(72))
        self.assertEqual(data['products']['MUG']['profit'], 11)

    def test_html_is_current_self_contained_and_escaped(self):
        data = dashboard.summarize(dashboard.ROOT / 'sample_orders.csv')
        html = dashboard.render(data)
        self.assertEqual(html, (dashboard.ROOT / 'dashboard.html').read_text())
        self.assertIn('<svg ', html)
        self.assertIn('FAKE SAMPLE DATA', html)
        self.assertNotIn('src=', html)
        self.assertNotIn('href=', html)
        data['products']['MUG']['name'] = '<script>alert(1)</script>'
        data['products']['MUG']['profit'] = Decimal('-10')
        html = dashboard.render(data)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('#b42318', html)

    def test_bad_inputs_fail_instead_of_misleading_profit(self):
        changes = [('Lineitem quantity', '0'), ('Lineitem quantity', '1.5'),
                   ('Lineitem price', 'NaN'), ('Lineitem sku', 'UNKNOWN'),
                   ('Currency', 'EUR'), ('Financial Status', 'pending'), ('Total', '999'),
                   ('Discount Amount', '999'), ('Refunded Amount', '999'), ('Email', '')]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'orders.csv'
            for field, value in changes:
                rows = [dict(row) for row in self.rows]
                rows[0][field] = value
                write_csv(path, rows)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    dashboard.summarize(path)
            for rows in [self.rows + [self.rows[0]], [self.rows[1]],
                         [self.rows[0], dict(self.rows[1], Shipping='5')]]:
                write_csv(path, rows)
                with self.assertRaises(ValueError):
                    dashboard.summarize(path)

    def test_changed_costs_change_profit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'costs.csv'
            path.write_text('sku,unit_cost\nMUG,7\nTOTE,10\nCAP,8\n')
            data = dashboard.summarize(dashboard.ROOT / 'sample_orders.csv', path)
            self.assertEqual(data['gross_profit'], 86)
            self.assertEqual(data['profit'], 69)
            path.write_text('sku,unit_cost\nMUG,7\nMUG,8\n')
            with self.assertRaises(ValueError):
                dashboard.summarize(dashboard.ROOT / 'sample_orders.csv', path)


class TriageTests(unittest.TestCase):
    def test_sample_categories_and_offline_output(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(triage, 'urlopen') as network:
            output = Path(folder) / 'triage.csv'
            with patch.dict(triage.os.environ, {'OPENAI_API_KEY': 'fake'}, clear=True):
                rows = triage.run(triage.ROOT / 'sample_messages.csv', output)
            network.assert_not_called()
            self.assertEqual(len(rows), 18)
            self.assertEqual(set(row['category'] for row in rows), set(triage.CATEGORIES))
            self.assertTrue(all(row['mode'] == 'rule-based' and row['review_required'] == 'yes' for row in rows))
            self.assertEqual(rows[15]['priority'], 'high')
            self.assertEqual(rows[16]['category'], 'refund request')
            self.assertEqual(rows[17]['category'], 'question')
            self.assertEqual(output.read_bytes(), (triage.ROOT / 'sample_triage.csv').read_bytes())

    def test_missing_key_does_not_send_or_write(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(triage.os.environ, {}, clear=True), patch.object(triage, 'urlopen') as network:
            path = Path(folder) / 'output.csv'
            with self.assertRaisesRegex(ValueError, 'requires'):
                triage.run(triage.ROOT / 'sample_messages.csv', path, True)
            self.assertFalse(path.exists())
            network.assert_not_called()

    def test_both_api_contracts_and_provider_precedence(self):
        result = dict(category='question', priority='medium', reply='Which size do you need?')
        for provider in ('openai', 'anthropic'):
            payload = ({'choices': [{'message': {'content': json.dumps(result)}}]} if provider == 'openai'
                       else {'content': [{'type': 'text', 'text': json.dumps(result)}]})
            with patch.object(triage, 'urlopen', return_value=io.BytesIO(json.dumps(payload).encode())) as network:
                self.assertEqual(triage.classify_llm('Which size?', (provider, 'fake-key', 'test-model')), result)
                request = network.call_args.args[0]
                body = json.loads(request.data)
                self.assertEqual(body['model'], 'test-model')
                self.assertIn('Which size?', body['messages'][-1]['content'])
                self.assertEqual(request.get_method(), 'POST')
                if provider == 'openai':
                    self.assertEqual(request.get_header('Authorization'), 'Bearer fake-key')
                    self.assertEqual(body['response_format'], {'type': 'json_object'})
                else:
                    self.assertEqual(request.get_header('X-api-key'), 'fake-key')
                    self.assertIn('system', body)
        with patch.dict(triage.os.environ, {'ANTHROPIC_API_KEY': 'a', 'OPENAI_API_KEY': 'b'}, clear=True):
            self.assertEqual(triage.llm_config()[0], 'anthropic')

    def test_invalid_api_responses_and_formula_protection(self):
        for result in [[], {}, dict(category='other', priority='low', reply='x'),
                       dict(category='praise', priority='urgent', reply='x'),
                       dict(category='praise', priority='low', reply='x'*401)]:
            with self.assertRaises(ValueError):
                triage.validate(result)
        with patch.object(triage, 'urlopen', return_value=io.BytesIO(b'{"choices": []}')):
            with self.assertRaisesRegex(ValueError, 'Invalid LLM response'):
                triage.classify_llm('hi', ('openai', 'fake', 'test'))
        self.assertEqual(triage.csv_safe(' =1+1'), "' =1+1")
        self.assertEqual(triage.csv_safe('Thanks'), 'Thanks')


if __name__ == '__main__':
    unittest.main()
