"""Verify the lesson's persisted knowledge, experiment, graph and local links."""
import json
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
from core import ROOT,load,ingest,evidence_gate,result_gate
from research import outputs as research_outputs,compute,data_outputs
from pipeline import run
from build import render

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=set();self.slide_count=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.add(attrs['id'])
        if 'data-slide' in attrs:self.slide_count+=1
        for key in ['href','src']:
            if key in attrs:self.links.append(attrs[key])

def check():
    sources,claims,wiki,slides=load();ingest(sources);evidence_gate(sources,claims,wiki,slides)
    if len(slides)!=18 or len(wiki)!=8:raise ValueError('LESSON_STRUCTURE_CHANGED')
    result_gate(compute(),compute(coverage=True));expected=render(write=False)
    for name,body in {**expected,**research_outputs(),**data_outputs()}.items():
        if not (ROOT/name).is_file() or (ROOT/name).read_text()!=body:raise ValueError('STALE_ARTIFACT: '+name)
    graph=run();saved=json.loads((ROOT/'runs/graph-run.json').read_text())
    if graph!=saved:raise ValueError('STALE_GRAPH_RUN')
    occurrence=0;parsers={}
    for name,body in expected.items():
        if name.endswith('.html'):
            parser=Links();parser.feed(body);parsers[name]=parser
    for name,parser in parsers.items():
        for link in parser.links:
            url=urlsplit(link)
            if url.scheme:
                if url.scheme!='https':raise ValueError('UNEXPECTED_PROTOCOL')
                continue
            if url.netloc:raise ValueError('UNEXPECTED_LINK_HOST')
            target=((ROOT/name).parent/unquote(url.path)).resolve() if url.path else (ROOT/name).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():raise ValueError('BROKEN_LOCAL_LINK: '+link)
            if url.fragment and target.suffix=='.html':
                target_name=target.relative_to(ROOT.resolve()).as_posix()
                if url.fragment not in parsers[target_name].ids:raise ValueError('BROKEN_FRAGMENT: '+link)
            occurrence+=1
    if parsers['slides.html'].slide_count!=18:raise ValueError('MISSING_SLIDE')
    return dict(sources=len(sources),wiki=len(wiki),slides=len(slides),claims=len(claims),html_pages=len(parsers),local_links=occurrence,comparison_executions=graph['executions'],repair_attempts=len(graph['repair_loop']['attempts']),total_executions=graph['total_executions'],model_api_calls=0,semantic_review='human reading still required')

if __name__=='__main__':print(json.dumps(check(),ensure_ascii=False,indent=2))
