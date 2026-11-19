"""A reproducible synthetic research tool, with development-only model selection."""
import argparse,csv,hashlib,json
from datetime import date,timedelta
from decimal import Decimal,ROUND_FLOOR,ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
D=Decimal
CANDIDATES=[(3,7),(5,12),(8,20)]
FOLDS=[dict(train=[0,22],gap=[22,24],validation=[24,36]),dict(train=[0,34],gap=[34,36],validation=[36,48]),dict(train=[0,46],gap=[46,48],validation=[48,60])]
FINAL=[62,92]
PLAN=dict(initial_cash='100000.00',candidates=[list(x) for x in CANDIDATES],signal_lag=1,fee_per_side='0.001',minimum_unit=1,selection_scope='development_validation_only',final_test=FINAL)


def synthetic_csv(coverage=False):
    import io
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerow(['date','open','close'])
    previous=D('100');day=date(2026,6,1);returns=['0.012','-0.004','0.008','0.003','-0.002']
    for i in range(92):
        while day.weekday()>4:day+=timedelta(days=1)
        if i<32:r=D(returns[i%5])
        elif i<62:r=D(['-0.014','0.012','-0.009','0.011','-0.003'][i%5])
        else:r=D((['0.02','0.012','0.018','-0.035','-0.02','-0.015','0.018','0.01','0.015','-0.03'][i%10]) if coverage else ['-0.018','0.008','-0.012','0.004','-0.006'][i%5])
        opening=(previous*(1+D(['0.001','-0.001','0'][i%3]))).quantize(D('.01'),rounding=ROUND_HALF_UP)
        close=(opening*(1+r)).quantize(D('.01'),rounding=ROUND_HALF_UP)
        writer.writerow([day.isoformat(),str(opening),str(close)]);previous=close;day+=timedelta(days=1)
    return stream.getvalue()


def data_outputs():
    raw=synthetic_csv();manifest=dict(data_type='synthetic',source_url=None,retrieved_at=None,created_on='2026-11-17',rows=92,columns=['date','open','close'],sha256=hashlib.sha256(raw.encode()).hexdigest(),license='CC0-1.0 (this project numeric fixture)',generated_by='Fixed return and gap lists in scripts/research.py; no randomness. Dates are synthetic business-day labels, not an exchange calendar.')
    extra=synthetic_csv(coverage=True);coverage=dict(manifest,sha256=hashlib.sha256(extra.encode()).hexdigest(),generated_by='Same fixed development prefix as primary; mixed-sign final segment for execution coverage testing, not evidence of market performance.')
    return {'content/data/synthetic-prices.csv':raw,'content/data/manifest.json':json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','content/data/coverage-prices.csv':extra,'content/data/coverage-manifest.json':json.dumps(coverage,ensure_ascii=False,indent=2)+'\n'}


def load_prices(root=ROOT,coverage=False):
    manifest=json.loads((root/('content/data/coverage-manifest.json' if coverage else 'content/data/manifest.json')).read_text());raw=(root/('content/data/coverage-prices.csv' if coverage else 'content/data/synthetic-prices.csv')).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['sha256']:raise ValueError('DATA_HASH_MISMATCH')
    import io
    reader=csv.DictReader(io.StringIO(raw.decode()));rows=list(reader)
    if manifest['data_type']!='synthetic' or manifest['source_url'] is not None or len(rows)!=92 or len(rows)!=manifest['rows'] or reader.fieldnames!=manifest['columns']:raise ValueError('DATA_MANIFEST_INVALID')
    previous=None
    for row in rows:
        current=date.fromisoformat(row['date'])
        if previous and current<=previous:raise ValueError('DATES_NOT_SORTED')
        previous=current
        for field in ['open','close']:
            row[field]=D(row[field])
            if not row[field].is_finite() or row[field]<=0:raise ValueError('BAD_PRICE')
    return rows


def validate_plan(plan):
    if type(plan.get('signal_lag')) is not int or plan['signal_lag']<1:raise ValueError('LOOKAHEAD_SIGNAL_LAG')
    if plan.get('selection_scope')!='development_validation_only':raise ValueError('TEST_SET_USED_FOR_SELECTION')
    if 'fee_per_side' not in plan:raise ValueError('MISSING_COST_ASSUMPTION')
    fee=D(plan['fee_per_side'])
    if not fee.is_finite() or not D('0')<=fee<=D('.01'):raise ValueError('FEE_UNIT_INVALID')
    return True


def simulate(rows,pair,start,end,fee=D('.001'),initial=D('100000.00')):
    fast,slow=pair;cash=initial;curve=[];ledger=[]
    for i in range(start,end):
        history=[row['close'] for row in rows[:i]]
        hold=len(history)>=slow and sum(history[-fast:])*slow>sum(history[-slow:])*fast
        before=cash
        if hold:
            opening,closing=rows[i]['open'],rows[i]['close']
            quantity=int((cash/(opening*(1+fee))).to_integral_value(rounding=ROUND_FLOOR))
            commission=lambda amount:(amount*fee).quantize(D('.01'),rounding=ROUND_HALF_UP)
            if quantity and opening*quantity+commission(opening*quantity)>cash:quantity-=1
            if quantity:
                entry_fee=commission(opening*quantity);exit_fee=commission(closing*quantity)
                cash+=quantity*(closing-opening)-entry_fee-exit_fee
                ledger.append(dict(index=i,date=rows[i]['date'],signal_available=rows[i-1]['date']+' close',entry='open',exit='same bar close',quantity=quantity,entry_price=str(opening),exit_price=str(closing),fee=str(entry_fee+exit_fee),cash_flow=str(cash-before)))
        curve.append(dict(index=i,date=rows[i]['date'],equity=str(cash)))
    peak=initial;drawdown=D('0')
    for point in curve:
        value=D(point['equity']);peak=max(peak,value);drawdown=max(drawdown,1-value/peak)
    return dict(pair=list(pair),range=[start,end],ending_equity=str(cash),return_pct=float((cash/initial-1)*100),max_drawdown_pct=float(drawdown*100),round_trips=len(ledger),total_fees=str(sum((D(x['fee']) for x in ledger),D('0'))),ledger=ledger,curve=curve)


def compute(root=ROOT,coverage=False):
    validate_plan(PLAN);rows=load_prices(root,coverage)
    development=[]
    for pair in CANDIDATES:
        folds=[simulate(rows,pair,*fold['validation']) for fold in FOLDS]
        combined=D('1')
        for fold in folds:combined*=D(fold['ending_equity'])/D('100000')
        development.append(dict(pair=list(pair),fold_returns_pct=[x['return_pct'] for x in folds],selection_score_pct=float((combined-1)*100)))
    selected=sorted(development,key=lambda x:(-x['selection_score_pct'],x['pair']))[0]['pair']
    scenarios=[dict(fee_per_side=str(fee),**simulate(rows,selected,*FINAL,fee=fee)) for fee in [D('0'),D('.001'),D('.003')]]
    return dict(fixture='coverage' if coverage else 'primary',data_type='synthetic',scope='Fixed research workflow demonstration, not real market evidence',initial_cash='100000.00',bars=len(rows),folds=FOLDS,development_span=[0,60],embargo=[60,62],final_test=FINAL,development=development,selected_pair=selected,selection_rule='Highest compounded validation-fold return at 0.1% per side; final test is not consulted',final_test_scenarios=scenarios,execution='Prior-close SMA decides next-open entry; every position exits same bar close; integer units; fees ROUND_HALF_UP to cents.',not_modelled=['tax','minimum commission','slippage','partial fills','price limits','dividends','actual calendar'],model_calls=0)


def require_activity(report):
    if not report['final_test_scenarios'][1]['round_trips']:raise ValueError('INSUFFICIENT_ACTIVITY')
    return True

def outputs(root=ROOT):
    return {name:json.dumps(compute(root,coverage),ensure_ascii=False,indent=2)+'\n' for name,coverage in [('runs/research-result.json',False),('runs/coverage-result.json',True)]}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--generate-data',action='store_true');parser.add_argument('--check',action='store_true');args=parser.parse_args()
    generated=data_outputs() if args.generate_data else outputs()
    for name,body in generated.items():
        path=ROOT/name
        if args.check:
            if not path.is_file() or path.read_text()!=body:raise ValueError('STALE_RESEARCH_OUTPUT: '+name)
        else:path.write_text(body)
    print('PASS · deterministic synthetic input' if args.generate_data and args.check else 'PASS · research outputs match' if args.check else 'Generated research inputs' if args.generate_data else 'Generated synthetic research result')
