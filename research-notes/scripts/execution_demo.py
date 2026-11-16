"""Reproduce three local execution paths from explicit teaching fixtures."""
import argparse
import csv
from decimal import Decimal, ROUND_FLOOR
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'content/experiments/execution-input.csv'


def evaluate(row):
    cash = Decimal(row['cash'])
    price = Decimal(row['signal_price'])
    lot = int(row['lot_size'])
    if cash < 0 or price <= 0 or lot <= 0:
        raise ValueError('Invalid fixture input')
    quantity = int((cash / (price * lot)).to_integral_value(rounding=ROUND_FLOOR)) * lot
    submitted = quantity > 0
    filled = submitted and row['liquidity_available'] == 'true'
    status = 'FILLED' if filled else ('UNFILLED' if submitted else 'NO_ENTRY')
    position = quantity if filled else 0
    ending_cash = cash - price * position
    # Each row uses the explicitly supplied final mark, not an inferred market price.
    equity = ending_cash + Decimal(row['ending_price']) * position
    return dict(case=row['case'],status=status,order_created=submitted,
                requested_quantity=quantity,filled_quantity=position,
                ending_cash=float(ending_cash),ending_equity=float(equity),
                return_pct=float((equity/cash-1)*100) if cash else None)


def outputs():
    with INPUT.open(newline='') as file:
        rows = [evaluate(row) for row in csv.DictReader(file)]
    report = dict(basis='Teaching fixtures; no broker connection, tax or transaction cost.',
                  schema_version=1,results=rows)
    labels = {'NO_ENTRY':'未進場', 'UNFILLED':'建立模擬單但未成交', 'FILLED':'模擬成交後持有'}
    circles = []
    for index, row in enumerate(rows):
        y = 90 + index * 105
        width = (row['ending_equity']/100000)*340
        color = '#c1cdb0' if row['status']=='NO_ENTRY' else '#e9c99a' if row['status']=='UNFILLED' else '#739578'
        circles.append(f'<text x="24" y="{y}" font-size="15">{escape(row["case"])}</text>'
            f'<text x="24" y="{y+24}" fill="#647064" font-size="12">{labels[row["status"]]}</text>'
            f'<rect x="260" y="{y-17}" width="{width:.2f}" height="32" rx="6" fill="{color}"/>'
            f'<text x="{270+width:.2f}" y="{y+4}" font-size="14">{row["ending_equity"]:,.0f}</text>')
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 390" role="img" '
        'aria-labelledby="title desc"><title id="title">三條執行路徑的期末資產</title>'
        '<desc id="desc">兩條路徑皆為十萬元且零報酬，但一條未建立模擬單，另一條建立後未成交。成交路徑期末為九萬一千六百七十元。</desc>'
        '<rect width="760" height="390" rx="14" fill="#f0eee4"/>'
        '<g font-family="sans-serif" fill="#263d34"><text x="24" y="35" font-size="18">同樣 0%，停在不同的執行階段</text>'
        + ''.join(circles) + '<text x="24" y="368" fill="#647064" font-size="12">教學假設 · 本金 100,000 元 · 期末資產單位為元 · 無費用</text></g></svg>')
    return {'assets/execution-paths.json':json.dumps(report,ensure_ascii=False,indent=2)+'\n',
            'assets/execution-paths.svg':svg+'\n'}


def run(check=False):
    for name, body in outputs().items():
        path = ROOT / name
        if check:
            if not path.is_file() or path.read_text()!=body:
                raise ValueError('Stale experiment artifact: '+name)
        else:
            path.write_text(body)
    print('PASS · 3 reproducible execution paths' if check else 'Generated 3 teaching execution paths.')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    run(parser.parse_args().check)
