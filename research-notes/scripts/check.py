"""Audit content contracts, arithmetic, artifacts, links and reverse navigation."""
import argparse
from html.parser import HTMLParser
import json
from urllib.parse import unquote, urlsplit
from build import ROOT, load_notes, render
from content_lint import lint_notes
from execution_demo import outputs as experiment_outputs

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'href', 'src'} and value:
                self.links.append(value)


def check():
    notes, sources = load_notes()
    report = lint_notes(notes, sources, ROOT, json.loads((ROOT/'content/examples.json').read_text()))
    expected = render(notes, sources)
    targets = set()
    occurrences = 0
    html_links = {}
    for name, content in expected.items():
        path = ROOT / name
        if not path.is_file() or path.read_text() != content:
            raise ValueError(f'Stale artifact {name}; run scripts/build.py')
        if not name.endswith('.html'):
            continue
        parser = Links()
        parser.feed(content)
        html_links[name] = parser.links
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme:
                if url.scheme != 'https':
                    raise ValueError(f'Unexpected protocol {link}')
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if url.netloc or not target.is_relative_to(ROOT) or not target.is_file():
                raise ValueError(f'Broken local link in {name}: {link}')
            occurrences += 1
            targets.add(target.relative_to(ROOT).as_posix())
    for name, body in experiment_outputs().items():
        path = ROOT/name
        if not path.is_file() or path.read_text()!=body:
            raise ValueError(f'Stale experiment artifact: {name}')
    authored_edges = {(n['id'], other) for n in notes for other in n['related']}
    one_way = {(a,b) for a,b in authored_edges if (b,a) not in authored_edges}
    for a,b in authored_edges:
        if a+'.html' not in html_links[f'notes/{b}.html']:
            raise ValueError(f'Missing generated backlink: {b} -> {a}')
    for required in ['AGENTS.md', 'README.md', 'templates/note.md', 'CHANGELOG.md', '.nojekyll']:
        if not (ROOT / required).is_file():
            raise ValueError(f'Missing project file {required}')
    report.update(local_link_occurrences=occurrences,unique_local_files=len(targets),broken_local_links=0,
                  authored_related_edges=len(authored_edges),one_way_authored_edges=len(one_way),
                  generated_backlinks=len(authored_edges),missing_backlinks=0,experiment_paths=3)
    return report

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    report=check()
    if args.json:
        print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print(f"PASS · {report['notes']} notes · {report['substantive_examples']} worked examples · {report['arithmetic_checks']} arithmetic checks")
        print(f"Links · {report['local_link_occurrences']} occurrences · {report['unique_local_files']} unique local files · 0 broken")
        print(f"Sources · {report['cited_sources']} cited · {len(report['unused_sources'])} uncited · Backlinks · {report['missing_backlinks']} missing")
        print('Scope · Editorial and arithmetic checks passed; source meaning and personal-report authenticity require human review.')
