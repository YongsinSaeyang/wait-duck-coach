"""Regression cases drawn from the review's blank-note counterexample."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build
from check import check
from content_lint import arithmetic, lint_notes, sections
from execution_demo import evaluate

class ContentRegressionTests(unittest.TestCase):
    def setUp(self):
        self.notes,self.sources=build.load_notes()
        self.examples=json.loads((ROOT/'content/examples.json').read_text())
    def validate(self):
        return lint_notes(self.notes,self.sources,ROOT,self.examples)
    def test_existing_notes_have_explicit_examples_and_citations(self):
        report=self.validate()
        self.assertEqual(report['substantive_examples'],7)
        self.assertEqual(report['arithmetic_checks'],11)
        self.assertEqual(report['teaching_labels'],7)
        self.assertEqual(report['unused_sources'],[])
        self.assertTrue(report['manual_claim_review_required'])
    def test_reviewers_blank_eighth_note_is_rejected(self):
        blank=deepcopy(self.notes[0])
        blank['id']='blank-eighth'
        blank['body']='\n\n'.join('## '+h+'\n\n'+p for h,p in zip(build.SECTIONS,
            ['寫出具體的疑惑','寫出例子','寫出步驟','寫出限制']))
        self.notes.append(blank)
        self.examples['blank-eighth']=deepcopy(self.examples[self.notes[0]['id']])
        with self.assertRaisesRegex(ValueError,'Template placeholder'):
            self.validate()
        # Reproduce the reviewer's actual build/check commands in an isolated copy.
        with TemporaryDirectory() as tmp:
            from shutil import copytree
            import subprocess
            sandbox=Path(tmp)/'project'
            copytree(ROOT,sandbox,ignore=lambda path,names:[n for n in names if n=='__pycache__'])
            metadata={k:v for k,v in blank.items() if k not in ('body','source_path')}
            path=sandbox/'content/notes/2026-11-16-blank-eighth.md'
            path.write_text('---\n'+json.dumps(metadata,ensure_ascii=False)+'\n---\n'+blank['body'])
            (sandbox/'content/examples.json').write_text(json.dumps(self.examples))
            for command in ['scripts/build.py','scripts/check.py']:
                result=subprocess.run([sys.executable,command],cwd=sandbox,capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Template placeholder',result.stderr)
    def test_meaningless_short_section_is_rejected(self):
        self.notes[0]['body']=self.notes[0]['body'].replace('## 我想釐清的問題','## 我想釐清的問題\n\n只有標題。\n\n## 額外的標題')
        with self.assertRaisesRegex(ValueError,'sections'):
            self.validate()
    def test_example_without_numeric_input_is_rejected(self):
        note=self.notes[0]
        parts=sections(note['body'])
        parts[build.SECTIONS[1]]='教學假設。'+'這段只有泛泛的說明，沒有具體數字可以讓讀者自己重新核對。'*4
        note['body']='\n\n'.join('## '+h+'\n\n'+parts[h] for h in build.SECTIONS)
        with self.assertRaisesRegex(ValueError,'numeric inputs'):
            self.validate()
    def test_unlabelled_teaching_example_is_rejected(self):
        self.notes[0]['body']=self.notes[0]['body'].replace('教學假設','假定條件')
        with self.assertRaisesRegex(ValueError,'Teaching label'):
            self.validate()
    def test_source_only_in_registry_is_rejected(self):
        note=self.notes[0]
        source_id=note['sources'][0]
        url=self.sources[source_id]['url']
        note['body']=re.sub(r'\[([^\]]+)\]\('+re.escape(url)+r'\)',r'\1',note['body'])
        with self.assertRaisesRegex(ValueError,'absent from body citations'):
            self.validate()
    def test_fake_citation_in_code_is_rejected(self):
        note=self.notes[0]
        note['body']=re.sub(r'(\[[^\]]+\]\(https://[^)]+\))',r'`\1`',note['body'])
        with self.assertRaisesRegex(ValueError,'absent from body citations'):
            self.validate()
    def test_unknown_source_is_rejected_by_real_loader(self):
        with TemporaryDirectory() as tmp:
            from shutil import copytree
            sandbox=Path(tmp)/'project'
            copytree(ROOT,sandbox,ignore=lambda path,names:[n for n in names if n=='__pycache__'])
            path=next((sandbox/'content/notes').glob('*.md'))
            text=path.read_text().replace('"sources": [','"sources": ["unavailable-source",',1)
            path.write_text(text)
            with patch.object(build,'ROOT',sandbox), self.assertRaisesRegex(ValueError,'Unregistered source'):
                build.load_notes()
    def test_new_personal_experience_without_record_is_rejected(self):
        note=next(n for n in self.notes if n['experience_record'] is None)
        note['body']=note['body'].replace('## 我想釐清的問題','## 我想釐清的問題\n\n我親自測試發現這個結果。',1)
        with self.assertRaisesRegex(ValueError,'Personal observation requires'):
            self.validate()
    def test_unrelated_experience_path_is_rejected(self):
        self.notes[0]['experience_record']='README.md'
        with self.assertRaisesRegex(ValueError,'outside observations'):
            self.validate()
    def test_wrong_example_result_is_rejected(self):
        self.examples[self.notes[0]['id']][0]['expected']=999
        with self.assertRaisesRegex(ValueError,'contradicts arithmetic'):
            self.validate()
    def test_missing_result_in_prose_is_rejected(self):
        self.examples[self.notes[0]['id']][0]['display']='不存在的結果值 99999'
        with self.assertRaisesRegex(ValueError,'absent from worked example'):
            self.validate()
    def test_arithmetic_cannot_execute_code(self):
        for text in ['__import__("os")','a+1','2**99','1/0']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                arithmetic(text)
    def test_reverse_links_are_generated_without_rewriting_editorial_links(self):
        rendered=build.render(self.notes,self.sources)
        self.assertIn('annualization-is-a-scale.html',rendered['notes/dataset-version.html'])
        self.assertNotIn('annualization-is-a-scale',next(n for n in self.notes if n['id']=='dataset-version')['related'])
        report=check()
        self.assertEqual(report['one_way_authored_edges'],4)
        self.assertEqual(report['missing_backlinks'],0)
        self.assertGreater(report['local_link_occurrences'],report['unique_local_files'])
    def test_uncommitted_generated_edit_is_rejected(self):
        rendered=build.render
        def changed(notes,sources):
            out=rendered(notes,sources)
            out['index.html']+='stale'
            return out
        with patch('check.render',changed),self.assertRaisesRegex(ValueError,'Stale artifact'):
            check()
    def test_cash_failure_stops_before_local_order_creation(self):
        row=dict(case='cash',cash='100000',signal_price='120',lot_size='1000',liquidity_available='true',ending_price='110')
        result=evaluate(row)
        self.assertEqual(result['status'],'NO_ENTRY')
        self.assertFalse(result['order_created'])
        self.assertEqual(result['return_pct'],0)
    def test_unfilled_and_no_entry_have_different_states(self):
        row=dict(case='liquidity',cash='100000',signal_price='120',lot_size='1',liquidity_available='false',ending_price='110')
        result=evaluate(row)
        self.assertEqual(result['status'],'UNFILLED')
        self.assertTrue(result['order_created'])
        self.assertEqual(result['return_pct'],0)
    def test_filled_path_has_marked_equity(self):
        row=dict(case='fill',cash='100000',signal_price='120',lot_size='1',liquidity_available='true',ending_price='110')
        result=evaluate(row)
        self.assertEqual(result['filled_quantity'],833)
        self.assertEqual(result['ending_cash'],40)
        self.assertEqual(result['ending_equity'],91670)
        self.assertAlmostEqual(result['return_pct'],-8.33)

if __name__=='__main__':
    unittest.main()
