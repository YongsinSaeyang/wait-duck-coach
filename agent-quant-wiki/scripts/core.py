"""Knowledge contracts and explicit evidence routing, without an LLM API."""
import hashlib,json,math
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]

def read(path,root=ROOT):return json.loads((root/path).read_text())

def load(root=ROOT):
    sources=read('content/sources.json',root);claims=read('content/claims.json',root)
    wiki=[json.loads(p.read_text()) for p in sorted((root/'content/wiki').glob('*.json'))]
    slides=read('content/slides.json',root)
    return sources,claims,wiki,slides


def ingest(sources,root=ROOT):
    if len(sources)<5:raise ValueError('LESS_THAN_FIVE_SOURCES')
    ids=set()
    for source in sources:
        if source['id'] in ids:raise ValueError('DUPLICATE_SOURCE')
        ids.add(source['id']);path=(root/source['path']).resolve()
        if not path.is_relative_to((root/'content/sources').resolve()) or not path.is_file():raise ValueError('SOURCE_PATH_INVALID')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('SOURCE_HASH_MISMATCH')
        if len(raw.decode())<150 or not source['locator'] or source['status']!='read':raise ValueError('SOURCE_NOT_INGESTED')
    return {'sources':len(sources),'mode':'read section notes with explicit scope, not full-document mirrors'}


def evidence_gate(sources,claims,wiki,slides):
    source_ids={s['id'] for s in sources};lookup={c['id']:c for c in claims};wiki_ids={w['id'] for w in wiki}
    if len(lookup)!=len(claims) or len(wiki_ids)!=len(wiki):raise ValueError('DUPLICATE_KNOWLEDGE_ID')
    for claim in claims:
        if claim['kind'] not in ['source','design','synthetic','observation']:raise ValueError('BAD_CLAIM_TYPE')
        if not set(claim['sources'])<=source_ids:raise ValueError('UNKNOWN_SOURCE')
        if claim['kind']=='source' and not claim['sources']:raise ValueError('MISSING_CLAIM_EVIDENCE')
        if claim['wiki'] not in wiki_ids:raise ValueError('UNKNOWN_WIKI')
    for page in wiki:
        if not set(page['claims'])<=lookup.keys() or not set(page['related'])<=wiki_ids:raise ValueError('BROKEN_WIKI_LINK')
        if len(page['sections'])<3 or any(len(x['text'])<40 for x in page['sections']):raise ValueError('EMPTY_WIKI')
    for slide in slides:
        if not set(slide['claims'])<=lookup.keys():raise ValueError('UNKNOWN_CLAIM')
        if not slide['claims'] or not set(slide['wiki'])<=wiki_ids:raise ValueError('SLIDE_WITHOUT_WIKI')
        if any(lookup[c]['wiki'] not in slide['wiki'] for c in slide['claims']):raise ValueError('SLIDE_WIKI_MISMATCH')
    return True


def evidence_packs(claims,wiki,slides):
    lookup={c['id']:c for c in claims};pages={w['id']:w for w in wiki};packs=[]
    for slide in slides:
        packs.append(dict(slide=slide['id'],query=slide['subtitle'],retrieval='explicit Wiki ID routing, not semantic/vector retrieval',wiki=[pages[k]['slug'] for k in slide['wiki']],claims=slide['claims'],sources=sorted({s for c in slide['claims'] for s in lookup[c]['sources']})))
    return packs


def result_gate(primary,coverage):
    for report in [primary,coverage]:
        for row in report['final_test_scenarios']:
            cash=Decimal(report['initial_cash'])+sum((Decimal(x['cash_flow']) for x in row['ledger']),Decimal('0'))
            if cash!=Decimal(row['ending_equity']):raise ValueError('RESULT_MISMATCH')
            value=float((cash/Decimal(report['initial_cash'])-1)*100)
            if not math.isclose(value,row['return_pct'],abs_tol=1e-9):raise ValueError('RESULT_MISMATCH')
    if primary['final_test_scenarios'][1]['round_trips']!=0 or primary['final_test_scenarios'][1]['return_pct']!=0:raise ValueError('PRIMARY_ACTIVITY_NARRATIVE_STALE')
    if primary['selected_pair']!=coverage['selected_pair']:raise ValueError('COVERAGE_CHANGED_SELECTION')
    return ['Primary final-test activity is zero; performance interpretation is blocked.'] if not primary['final_test_scenarios'][1]['round_trips'] else []
