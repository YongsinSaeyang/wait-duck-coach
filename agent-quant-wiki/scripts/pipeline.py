"""Execute late/early checks on identical declared fault cases and save real events."""
import argparse,copy,hashlib,json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from core import ROOT,load,ingest,evidence_gate,evidence_packs,result_gate
from research import PLAN,validate_plan,compute

CASES=[('normal',None),('unknown_claim','UNKNOWN_CLAIM'),('unknown_source','UNKNOWN_SOURCE'),('missing_cost','MISSING_COST_ASSUMPTION'),('same_bar_signal','LOOKAHEAD_SIGNAL_LAG'),('test_selection','TEST_SET_USED_FOR_SELECTION'),('wrong_result','RESULT_MISMATCH')]

def execute(case,placement,root=ROOT):
    sources,claims,wiki,slides=copy.deepcopy(load(root));plan=copy.deepcopy(PLAN);events=[];tool_calls=0;drafts=0
    def event(node,status='pass',detail=None):events.append(dict(node=node,status=status,detail=detail))
    ingest(sources,root);event('ingest');event('wiki',detail='Persisted content authored with Codex; this replay makes no model calls.')
    if case=='unknown_claim':slides[0]['claims'].append('C999')
    if case=='unknown_source':claims[0]['sources']=['S999']
    if case=='missing_cost':plan.pop('fee_per_side')
    if case=='same_bar_signal':plan['signal_lag']=0
    if case=='test_selection':plan['selection_scope']='final_test'
    event('query',detail='Explicit Wiki routes define the evidence pack.')
    node='evidence_gate';error=None;warnings=[]
    with TemporaryDirectory(prefix='week10-graph-') as tmp:
        try:
            if placement=='early':
                evidence_gate(sources,claims,wiki,slides);event('evidence_gate')
                node='plan_gate';validate_plan(plan);event('plan_gate')
            node='research_tool';primary,coverage=compute(root),compute(root,True);tool_calls+=1;event(node,detail='Computed both declared synthetic fixtures; no model or broker calls.')
            if case=='wrong_result':coverage['final_test_scenarios'][0]['ending_equity']='999999.00'
            if placement=='late':
                # An actual disposable draft is produced before the old checks.
                (Path(tmp)/'candidate.html').write_text('<!doctype html><html><title>Unverified candidate</title><body>'+json.dumps({'slide_ids':[s['id'] for s in slides]},ensure_ascii=False)+'</body></html>');drafts+=1;event('render_unverified_draft')
                node='evidence_gate';evidence_gate(sources,claims,wiki,slides);event(node)
                node='plan_gate';validate_plan(plan);event(node)
            node='result_gate';warnings=result_gate(primary,coverage);event(node,'pass_with_warning' if warnings else 'pass',warnings)
            if placement=='early':
                (Path(tmp)/'candidate.html').write_text('<!doctype html><html><title>Verified inputs</title></html>');drafts+=1;event('render_verified_draft')
            event('review',detail='Program checks passed; source meaning still needs human review.')
        except ValueError as failure:
            error=str(failure);event(node,'rejected',error)
    return dict(case=case,placement=placement,outcome='rejected' if error else 'pass_with_warning' if warnings else 'pass',error=error,tool_invocations=tool_calls,temporary_drafts=drafts,model_calls=0,events=events)


def repair_loop(case='missing_cost',max_revisions=2,restore=True,root=ROOT):
    if type(max_revisions) is not int or not 0<=max_revisions<=2:raise ValueError('REVISION_BUDGET_INVALID')
    attempts=[];current=case
    for revision in range(max_revisions+1):
        result=execute(current,'early',root);attempts.append(result)
        if result['error'] is None:return dict(case=case,status='recovered',attempts=attempts,correction='Restore the explicit approved teaching fixture; no model inference or guessed user parameter.')
        if revision<max_revisions and restore:current='normal'
    return dict(case=case,status='human_review_required',attempts=attempts,correction='Revision budget exhausted; no publication')


def run(root=ROOT,executed_on=None):
    results=[]
    for case,expected in CASES:
        for placement in ['late','early']:
            result=execute(case,placement,root)
            if result['error']!=expected:raise ValueError('UNEXPECTED_REPLAY_OUTCOME: '+case)
            results.append(result)
    failures=[r for r in results if r['case']!='normal']
    repair=repair_loop(root=root)
    if executed_on is None:executed_on=json.loads((root/'runs/graph-run.json').read_text())['executed_on'] if (root/'runs/graph-run.json').is_file() else date.today().isoformat()
    inputs=dict(knowledge=load(root),plan=PLAN,data=json.loads((root/'content/data/manifest.json').read_text()),coverage=json.loads((root/'content/data/coverage-manifest.json').read_text()),workflow=json.loads((root/'workflow.json').read_text()))
    code_hashes={name:hashlib.sha256((root/'scripts'/name).read_bytes()).hexdigest() for name in ['core.py','research.py','pipeline.py','build.py']}
    return dict(code_sha256=code_hashes,input_sha256=hashlib.sha256(json.dumps(inputs,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),repair_loop=repair,total_executions=len(results)+len(repair['attempts']),executed_on=executed_on,run_id='graph-'+hashlib.sha256(json.dumps(inputs,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12],scope='One normal scenario plus six deliberate fault injections, each replayed with late and early checks. Not natural model error rates.',cases=len(CASES),executions=len(results),matched=len(results),observed_retrieval='runs/retrieval-observation.json',observed_activity='runs/activity-observation.json',summary={p:dict(tool_invocations=sum(r['tool_invocations'] for r in failures if r['placement']==p),temporary_drafts=sum(r['temporary_drafts'] for r in failures if r['placement']==p)) for p in ['late','early']},results=results)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args();report=run(executed_on=None if args.check else date.today().isoformat());path=ROOT/'runs/graph-run.json';body=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.check:
        if not path.is_file() or path.read_text()!=body:raise ValueError('STALE_GRAPH_RUN')
    else:path.write_text(body)
    sources,claims,wiki,slides=load();pack_path=ROOT/'runs/evidence-packs.json';pack_body=json.dumps(evidence_packs(claims,wiki,slides),ensure_ascii=False,indent=2)+'\n'
    if args.check:
        if not pack_path.is_file() or pack_path.read_text()!=pack_body:raise ValueError('STALE_EVIDENCE_PACK')
    else:pack_path.write_text(pack_body)
    print(f"PASS · {report['matched']}/{report['executions']} comparison executions · {len(report['repair_loop']['attempts'])} repair attempts · {report['total_executions']} total · 0 model API calls")
    print(json.dumps(report['summary'],ensure_ascii=False))
