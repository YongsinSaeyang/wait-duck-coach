from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from shutil import copytree
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from core import load,ingest,evidence_gate,evidence_packs,result_gate
from research import PLAN,FOLDS,FINAL,validate_plan,load_prices,simulate,compute,require_activity,synthetic_csv
from pipeline import execute,run,repair_loop
from build import render
from check import check,Links

class LessonTests(unittest.TestCase):
    def setUp(self):self.sources,self.claims,self.wiki,self.slides=deepcopy(load())
    def sandbox(self):
        tmp=TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)/'project';copytree(ROOT,root,ignore=lambda p,n:['__pycache__'] if '__pycache__' in n else []);return root
    def test_at_least_five_actual_ingests(self):self.assertEqual(ingest(self.sources)['sources'],7)
    def test_source_hash_tampering_is_rejected(self):
        root=self.sandbox();path=root/self.sources[0]['path'];path.write_text(path.read_text()+'changed')
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH'):ingest(self.sources,root)
    def test_only_abstract_source_is_labelled(self):self.assertEqual(next(s for s in self.sources if s['id']=='S07')['read_scope'],'摘要')
    def test_unknown_source_is_rejected(self):
        self.claims[0]['sources']=['S999']
        with self.assertRaisesRegex(ValueError,'UNKNOWN_SOURCE'):evidence_gate(self.sources,self.claims,self.wiki,self.slides)
    def test_empty_source_claim_is_rejected(self):
        self.claims[0]['sources']=[]
        with self.assertRaisesRegex(ValueError,'MISSING_CLAIM_EVIDENCE'):evidence_gate(self.sources,self.claims,self.wiki,self.slides)
    def test_unknown_slide_claim_is_rejected(self):
        self.slides[0]['claims']=['C999']
        with self.assertRaisesRegex(ValueError,'UNKNOWN_CLAIM'):evidence_gate(self.sources,self.claims,self.wiki,self.slides)
    def test_wrong_wiki_route_is_rejected(self):
        self.slides[0]['wiki']=['W08']
        with self.assertRaisesRegex(ValueError,'MISMATCH'):evidence_gate(self.sources,self.claims,self.wiki,self.slides)
    def test_wiki_related_links_exist(self):self.assertTrue(evidence_gate(self.sources,self.claims,self.wiki,self.slides))
    def test_all_sources_reach_the_teaching_deck(self):
        packs=evidence_packs(self.claims,self.wiki,self.slides)
        self.assertEqual({s for p in packs for s in p['sources']},{s['id'] for s in self.sources});self.assertEqual(len(packs),18)
    def test_missing_cost_is_not_silently_defaulted(self):
        plan=deepcopy(PLAN);plan.pop('fee_per_side')
        with self.assertRaisesRegex(ValueError,'MISSING_COST'):validate_plan(plan)
    def test_same_bar_signal_is_rejected(self):
        plan=deepcopy(PLAN);plan['signal_lag']=0
        with self.assertRaisesRegex(ValueError,'LOOKAHEAD'):validate_plan(plan)
    def test_final_test_cannot_be_selection_scope(self):
        plan=deepcopy(PLAN);plan['selection_scope']='final_test'
        with self.assertRaisesRegex(ValueError,'TEST_SET'):validate_plan(plan)
    def test_fee_must_be_finite_ratio(self):
        for value in ['NaN','0.1','-0.1']:
            plan=deepcopy(PLAN);plan['fee_per_side']=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'FEE_UNIT'):validate_plan(plan)
    def test_input_has_92_ordered_synthetic_bars(self):
        rows=load_prices();self.assertEqual(len(rows),92);self.assertTrue(all(a['date']<b['date'] for a,b in zip(rows,rows[1:])))
    def test_manifest_row_count_is_checked(self):
        root=self.sandbox();path=root/'content/data/manifest.json';m=json.loads(path.read_text());m['rows']=91;path.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'MANIFEST'):load_prices(root)
    def test_fold_validation_blocks_do_not_overlap(self):
        self.assertEqual([f['validation'] for f in FOLDS],[[24,36],[36,48],[48,60]])
        self.assertTrue(all(f['train'][1]==f['gap'][0] and f['gap'][1]==f['validation'][0] for f in FOLDS))
        self.assertGreater(FINAL[0],FOLDS[-1]['validation'][1])
    def test_changing_final_test_does_not_change_selection(self):
        root=self.sandbox();path=root/'content/data/synthetic-prices.csv';lines=path.read_text().splitlines();last=lines[-1].split(',');last[2]='999.00';lines[-1]=','.join(last);raw='\n'.join(lines)+'\n';path.write_text(raw)
        mp=root/'content/data/manifest.json';m=json.loads(mp.read_text());m['sha256']=sha256(raw.encode()).hexdigest();mp.write_text(json.dumps(m))
        self.assertEqual(compute()['selected_pair'],compute(root)['selected_pair'])
    def test_prefix_transactions_do_not_use_future_prices(self):
        rows=load_prices(coverage=True);baseline=simulate(rows,(3,7),62,92);changed=deepcopy(rows);changed[85]['close']=Decimal('999')
        later=simulate(changed,(3,7),62,92)
        self.assertEqual([x for x in baseline['ledger'] if x['index']<85],[x for x in later['ledger'] if x['index']<85])
    def test_original_zero_return_is_zero_activity(self):
        result=compute();self.assertEqual(result['final_test_scenarios'][1]['round_trips'],0)
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_ACTIVITY'):require_activity(result)
    def test_coverage_does_not_change_development_prefix(self):
        self.assertEqual(synthetic_csv().splitlines()[:63],synthetic_csv(True).splitlines()[:63]);self.assertEqual(compute()['selected_pair'],compute(coverage=True)['selected_pair'])
    def test_cash_flow_reconciles_independently(self):
        for row in compute(coverage=True)['final_test_scenarios']:
            value=Decimal('100000')+sum((Decimal(x['cash_flow']) for x in row['ledger']),Decimal('0'))
            self.assertEqual(value,Decimal(row['ending_equity']));self.assertEqual(row['round_trips'],14)
    def test_cost_results_are_frozen_for_this_fixture(self):
        self.assertEqual([r['return_pct'] for r in compute(coverage=True)['final_test_scenarios']],[-3.59738,-6.25421,-11.36149])
    def test_numeric_tampering_fails_result_gate(self):
        primary,coverage=compute(),compute(coverage=True);coverage['final_test_scenarios'][0]['return_pct']=999
        with self.assertRaisesRegex(ValueError,'RESULT_MISMATCH'):result_gate(primary,coverage)
    def test_early_check_stops_tool_before_bad_plan(self):
        late=execute('missing_cost','late');early=execute('missing_cost','early')
        self.assertEqual(late['error'],early['error']);self.assertEqual(late['tool_invocations'],1);self.assertEqual(early['tool_invocations'],0);self.assertEqual(early['temporary_drafts'],0)
    def test_six_faults_and_normal_match_expected_results(self):
        report=run();self.assertEqual(report['matched'],14);self.assertEqual(report['total_executions'],16)
        self.assertEqual(report['summary']['late'],dict(tool_invocations=6,temporary_drafts=6));self.assertEqual(report['summary']['early'],dict(tool_invocations=1,temporary_drafts=0))
    def test_real_repair_loop_recovers_from_explicit_snapshot(self):
        result=repair_loop();self.assertEqual(result['status'],'recovered');self.assertEqual(len(result['attempts']),2);self.assertEqual(result['attempts'][0]['error'],'MISSING_COST_ASSUMPTION')
    def test_retry_budget_exhaustion_hands_off(self):
        result=repair_loop(restore=False);self.assertEqual(result['status'],'human_review_required');self.assertEqual(len(result['attempts']),3)
    def test_revision_limit_cannot_be_infinite(self):
        with self.assertRaisesRegex(ValueError,'BUDGET'):repair_loop(max_revisions=999)
    def test_18_slides_with_source_and_wiki_links(self):
        html=render(write=False)['slides.html'];parser=Links();parser.feed(html);self.assertEqual(parser.slide_count,18);self.assertIn('wiki/',html);self.assertIn('sources/s07.html',html)
    def test_render_is_deterministic_and_does_not_write(self):
        before=(ROOT/'slides.html').stat().st_mtime_ns;self.assertEqual(render(write=False),render(write=False));self.assertEqual((ROOT/'slides.html').stat().st_mtime_ns,before)
    def test_full_project_check(self):
        report=check();self.assertEqual(report['wiki'],8);self.assertEqual(report['model_api_calls'],0)

if __name__=='__main__':unittest.main()
