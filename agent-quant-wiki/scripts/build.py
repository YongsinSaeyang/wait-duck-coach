"""Build the Wiki, teaching deck and execution evidence with the standard library."""
from html import escape as E
import hashlib,json
from pathlib import Path
from core import ROOT,load,ingest,evidence_gate,evidence_packs,read
from research import compute


def jscript(value):return json.dumps(value,ensure_ascii=False).replace('<','\\u003c')
def asset(name,prefix=''):return prefix+'assets/'+name+'?v='+hashlib.sha256((ROOT/'assets'/name).read_bytes()).hexdigest()[:12]
def shell(title,body,prefix='',extra=''):
 return '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#f7f5ed"><title>'+E(title)+' · Agent × Quant</title><link rel="stylesheet" href="'+asset('site.css',prefix)+'"><script defer src="'+asset('site.js',prefix)+'"></script></head><body><a class="skip" href="#main">跳至內容</a><header class="top"><a class="brand" href="'+prefix+'index.html">等等鴨 <span>AGENT × QUANT</span></a><nav aria-label="主要導覽"><a href="'+prefix+'wiki/index.html">Wiki</a><a href="'+prefix+'slides.html">教學簡報</a><a href="'+prefix+'evidence.html">流程與紀錄</a><a href="'+prefix+'sources/index.html">來源</a></nav></header>'+body+extra+'<footer class="site-foot">楊祐宗｜第十週 LLM Wiki 教材 · 合成資料研究示範 · 整理 2026-11-17 · 驗收 2026-11-19</footer></body></html>'

def money(value):return f'{float(value):,.2f}'
def pct(value):return f'{value:+.2f}%'.replace('-', '−')
def table(headers,rows):return '<div class="table-wrap"><table><thead><tr>'+''.join('<th scope="col">'+E(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+E(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def graph():
 labels=[('取得資料','實際讀取章節與定位'),('整理 Wiki','LLM 協作作者節點'),('查詢證據','依 Wiki ID 取得主張'),('檢查規格','先驗來源與輸入'),('研究工具','固定合成資料試算'),('結果核對','算術、活動度與限制'),('產生教材','18 頁 HTML 簡報')]
 return '<ol class="flow">'+''.join('<li><strong>'+E(a)+'</strong><span>'+E(b)+'</span></li>' for a,b in labels)+'</ol><p class="loop-return">缺來源 ↩ 回 Wiki　｜　錯規格 ↩ 回研究問題　｜　數字不符 ↩ 回工具　｜　最多兩次修訂後交人工</p>'
def plot(report):
 values=[float(p['equity']) for row in report['final_test_scenarios'] for p in row['curve']];low=min(values+[100000])-1000;high=max(values+[100000])+1000
 y=lambda n:260-(n-low)/(high-low)*190
 parts=['<svg class="data-chart" viewBox="0 0 680 315" role="img" aria-labelledby="curve-title curve-description"><title id="curve-title">Coverage 合成資料成本補測</title><desc id="curve-description">三種每邊費率，凍結相同均線參數，均為合成資料機制測試。</desc>']
 for i in range(4):
  v=low+(high-low)*i/3;yp=y(v);parts.append(f'<line x1="72" x2="655" y1="{yp:.2f}" y2="{yp:.2f}" class="grid-line"/><text x="60" y="{yp+4:.2f}" text-anchor="end">{v:,.0f}</text>')
 for i,row in enumerate(report['final_test_scenarios']):
  points=' '.join(f'{72+n*583/(len(row["curve"])-1):.2f},{y(float(p["equity"])):.2f}' for n,p in enumerate(row['curve']))
  parts.append(f'<polyline class="equity-line line-{i}" points="{points}"/><text x="{72+i*200}" y="28" class="label-{i}">每邊 {float(row["fee_per_side"])*100:g}%</text>')
 parts.append('<text x="72" y="296">30 筆 coverage 測試資料｜資產單位：元</text></svg>');return ''.join(parts)


def render(write=True):
 sources,claims,wiki,slides=load();ingest(sources);evidence_gate(sources,claims,wiki,slides)
 smap={s['id']:s for s in sources};cmap={c['id']:c for c in claims};wmap={w['id']:w for w in wiki};packs=evidence_packs(claims,wiki,slides)
 primary,coverage=compute(),compute(coverage=True);run=read('runs/graph-run.json');out={}
 head='<main id="main" class="home"><section class="home-hero"><div><p class="eyebrow">AI AGENT 與量化研究</p><h1>可驗證的<br>量化研究流程</h1><p class="lead">讓研究問題、工具計算與每一句結論，都有可以回查的依據。</p><div class="actions"><a class="primary" href="slides.html">開始 18 頁教學 ↗</a><a href="wiki/index.html">進入 Wiki →</a></div><p class="meta">7 份來源整理 · 8 篇 Wiki · 18 頁教材</p></div><img src="assets/duck.svg" alt="抱著筆記本的等等鴨" width="280" height="320"></section><section class="reading"><h2>這份教材會帶你完成什麼？</h2><p>先區分 Agent 的自主決策和固定 workflow，再用一個合成資料任務，檢查工具規格、參數選擇、時間切分與成本。最後回到本次真實遇到的問題，說明如何把檢查往前移。</p>'+graph()+'</section><section class="two-columns"><div><h2>先討論，再生成</h2><p>作者把主題改為 AI Agent 與量化研究，再要求提高架構與驗證深度。需求、作者指令與實際執行各自保留。</p><a href="docs/discussion.md">需求確認紀錄 →</a></div><div><h2>執行與證據範圍</h2><p>本次 Codex 對話的 LLM 協助整理 Wiki 與教材；命令列重播使用已保存的內容，不會私下呼叫模型或券商。</p><a href="evidence.html">查看 14 次流程重播 →</a></div></section></main>'
 out['index.html']=shell('首頁',head)
 wiki_list=''.join('<article data-wiki="'+w['id']+'"><p class="eyebrow">'+w['id']+'</p><h2><a href="'+w['slug']+'.html">'+E(w['title'])+'</a></h2><p>'+E(w['sections'][0]['text'])+'</p></article>' for w in wiki)
 out['wiki/index.html']=shell('Wiki','<main id="main" class="reading"><p class="eyebrow">KNOWLEDGE BASE</p><h1>AI Agent × 量化研究 Wiki</h1><p class="lead">八篇概念頁串接七份來源，每一個主張保留類型與來源定位。</p><label for="wiki-search">搜尋 Wiki</label><input id="wiki-search" type="search" placeholder="例如 成本、LLM、時間"><p id="wiki-count" role="status" aria-live="polite">8 篇 Wiki</p><div class="wiki-list">'+wiki_list+'</div><p id="wiki-empty" hidden>沒有符合的 Wiki，請換個詞。</p></main>',prefix='../')
 for w in wiki:
  sids=sorted({s for c in w['claims'] for s in cmap[c]['sources']})
  sections=''.join('<section><h2>'+E(s['title'])+'</h2><p>'+E(s['text'])+'</p></section>' for s in w['sections'])
  claimhtml=''.join('<li><code>'+c+'</code> <span class="kind">'+E(cmap[c]['kind'])+'</span> '+E(cmap[c]['text'])+'</li>' for c in w['claims'])
  refs=''.join('<li><a href="../sources/'+sid.lower()+'.html">'+sid+'｜'+E(smap[sid]['title'])+'</a><small>'+E(smap[sid]['locator'])+'</small></li>' for sid in sids) or '<li>本頁主要為本作工程設計與合成結果；外部概念可沿相關 Wiki 回查。</li>'
  related=''.join('<li><a href="'+wmap[k]['slug']+'.html">'+E(wmap[k]['title'])+'</a></li>' for k in w['related'])
  out['wiki/'+w['slug']+'.html']=shell(w['title'],'<main id="main" class="reading"><a href="index.html">← Wiki 目錄</a><p class="eyebrow">'+w['id']+'</p><h1>'+E(w['title'])+'</h1>'+sections+'<section><h2>主張與證據</h2><ul class="claims">'+claimhtml+'</ul><ul>'+refs+'</ul></section><section><h2>相關 Wiki</h2><ul>'+related+'</ul></section><p><a href="../content/wiki/'+w['slug']+'.json">Wiki 原始結構 JSON →</a></p></main>',prefix='../')
 source_rows=[]
 for s in sources:
  raw=(ROOT/s['path']).read_text();text=raw.split('## Ingest 內容\n\n')[1].split('\n\n## 證據邊界')[0]
  out['sources/'+s['id'].lower()+'.html']=shell(s['title'],'<main id="main" class="reading"><a href="index.html">← 來源清單</a><p class="eyebrow">'+s['id']+' · 已讀取相關範圍</p><h1>'+E(s['title'])+'</h1><p>'+E(s['publisher'])+'</p><p><a href="'+E(s['url'],quote=True)+'" target="_blank" rel="noopener">前往原文 ↗</a></p><dl><dt>本次讀取</dt><dd>'+s['retrieved_on']+'</dd><dt>定位與範圍</dt><dd>'+E(s['locator'])+'；'+E(s['read_scope'])+'</dd><dt>Ingest 型態</dt><dd>閱讀後的章節整理，不是全文快照</dd></dl><h2>實際 ingest 內容</h2><p>'+E(text)+'</p><h2>版本</h2><p class="hash">SHA-256 '+s['sha256']+'</p><p><a href="../'+s['path']+'">讀取本地整理檔 →</a></p><p>雜湊只核對本地整理版本；沒有宣稱是原網頁全文的雜湊。</p></main>',prefix='../')
  source_rows.append([s['id'],s['title'],s['read_scope'],s['retrieved_on']])
 out['sources/index.html']=shell('七份來源','<main id="main" class="reading"><h1>七份實際 ingest 的資料</h1><p class="lead">這些資料在本次對話中讀取相關章節後整理。S07 僅摘要；所有整理檔都保留 URL、定位與本地雜湊。</p>'+table(['ID','資料','讀取範圍','日期'],source_rows)+'<ul>'+''.join('<li><a href="'+s['id'].lower()+'.html">'+s['id']+'｜'+E(s['title'])+'</a></li>' for s in sources)+'</ul><p><a href="../content/sources.json">來源登記與雜湊 JSON →</a></p></main>',prefix='../')
 sections=[]
 for slide,pack in zip(slides,packs):
  layout=slide['layout'];extra=''
  if layout=='cover':extra='<div class="cover-type">MODEL<br>TOOLS<br>EVIDENCE</div>'
  elif layout=='graph':extra=graph()
  elif layout=='contract':extra='<pre><code>input: data_sha256, fee_per_side, signal_lag, split\noutput: ledger, cash_flow, metrics, provenance\nerror: missing cost / lookahead / test contamination</code></pre>'
  elif layout=='plan':extra='<pre><code>fee_per_side: "0.001"  # 每邊 0.1%\nsignal_lag: 1\nselection_scope: "development_validation_only"\nfinal_test: [62, 92)  # 30 筆</code></pre>'
  elif layout=='split':extra=table(['階段','歷史前綴','gap','驗證'],[[str(i+1),str(f['train']),str(f['gap']),str(f['validation'])] for i,f in enumerate(primary['folds'])])+'<p class="meta">索引為從 0 起算的左閉右開區間；最終測試 [62,92)，gap [60,62)。</p>'
  elif layout=='selection':extra=table(['候選（短／長）','開發驗證合成報酬'],[['／'.join(map(str,r['pair'])),pct(r['selection_score_pct'])] for r in primary['development']])+'<p class="metric">凍結參數 <strong>'+ '／'.join(map(str,primary['selected_pair']))+'</strong></p>'
  elif layout=='activity':extra='<div class="activity-metrics"><div><span>最後測試報酬</span><strong>0.00%</strong></div><div><span>完整交易次數</span><strong>'+str(primary['final_test_scenarios'][1]['round_trips'])+'</strong></div></div><p class="warning">INSUFFICIENT_ACTIVITY｜保留結果，停止解讀策略績效</p>'
  elif layout=='cost':extra=plot(coverage)+table(['每邊費率','淨報酬','交易來回','累積費用'],[[f'{float(r["fee_per_side"])*100:g}%',pct(r['return_pct']),r['round_trips'],money(r['total_fees'])+' 元'] for r in coverage['final_test_scenarios']])
  elif layout=='replay':extra=table(['六個故意錯誤案例','拒絕前工具執行次數','已產生暫存草稿'],[['後置檢查',run['summary']['late']['tool_invocations'],run['summary']['late']['temporary_drafts']],['前置檢查',run['summary']['early']['tool_invocations'],run['summary']['early']['temporary_drafts']]])+'<p class="meta">同一案例在兩種位置實際執行，共 14 次：正常 2 次、錯誤案例 12 次。</p>'
  elif layout=='quiz':extra='<fieldset class="quiz"><legend>如果 30 筆測試得到 0%，但交易次數為零，較合理的解讀是？</legend><label><input type="radio" name="lesson-quiz" value="safe">策略沒有風險</label><label><input type="radio" name="lesson-quiz" value="activity">這段資料不足以評估交易後的績效</label><button type="button" id="quiz-check">檢查答案</button><p id="quiz-result" role="status" aria-live="polite"></p></fieldset>'
  points='<ul class="teaching-points">'+''.join('<li>'+E(p)+'</li>' for p in slide['points'])+'</ul>'
  refs=''.join('<a href="wiki/'+wmap[w]['slug']+'.html">'+w+' '+E(wmap[w]['title'])+'</a>' for w in slide['wiki'])
  src=' '.join('<a href="sources/'+sid.lower()+'.html">'+sid+'</a>' for sid in pack['sources']) or '本作設計／合成結果／觀察'
  sections.append('<section class="slide layout-'+layout+'" id="'+slide['id']+'" data-slide="'+slide['id']+'" aria-label="第 '+str(slide['number'])+' 頁，共 18 頁"'+(' hidden' if slide['number']>1 else '')+'><header><p class="slide-number">'+str(slide['number']).zfill(2)+' / 18</p><h1>'+E(slide['title'])+'</h1><p class="subtitle">'+E(slide['subtitle'])+'</p></header><div class="slide-content">'+extra+points+'</div><div class="slide-references">Wiki：'+refs+'<span>依據：'+src+'</span></div><details class="speaker"><summary>講者筆記與限制</summary><p>'+E(slide['notes'])+'</p><small>Claims：'+', '.join(slide['claims'])+'</small></details></section>')
 menu=''.join('<a href="#'+s['id']+'">'+str(s['number']).zfill(2)+' '+E(s['title'])+'</a>' for s in slides)
 deck='<main id="main" class="deck"><div class="deck-toolbar"><button id="previous" type="button" aria-label="上一頁">←</button><output id="slide-status" aria-live="polite">1 / 18</output><button id="next" type="button" aria-label="下一頁">→</button><button id="reading-mode" type="button" aria-pressed="false">閱讀模式</button><button id="contents" type="button">目錄</button></div><div class="slide-stage">'+''.join(sections)+'</div><dialog id="slide-menu"><h2>教學目錄</h2><button type="button" id="close-menu">關閉</button><nav aria-label="投影片目錄">'+menu+'</nav></dialog><p class="deck-hint">← → 或 PageUp／PageDown 切頁；Home／End 到首尾。表單內按鍵保留原功能。</p></main>'
 out['slides.html']=shell('教學簡報',deck)
 rows=[[r['case'],r['placement'],r['outcome'],r['error'] or '活動度限制已註明',r['tool_invocations'],r['temporary_drafts']] for r in run['results']]
 evidence='<main id="main" class="reading"><h1>Loop／graph 與實際執行紀錄</h1><p class="lead">七種情境 × 前後兩種檢查位置，14 次實際重播。六個錯誤案例是故意注入，不是模型自然錯誤率。</p>'+graph()+'<h2>本次自然觀察</h2><p>資料取得有一次 PDF 逾時；研究工具主要測試期沒有交易，活動度檢查拒絕解讀績效。各只觀察一次，沒有足夠樣本宣稱哪個節點最常出錯。</p><h2>檢查移動的理由</h2><p>來源完整性在 ingest 先查；工具所需的成本與時間規格在計算前先查。結果產生後再核對算術與活動度，避免把結構檢查誤當成研究有效。</p>'+table(['案例','檢查位置','結果','原因／限制','工具次數','暫存草稿'],rows)+'<h2>一次真的回復迴圈</h2><p>missing_cost 第一次在 plan_gate 被拒絕；回復明列的教學規格快照後，第二次通過並保留無交易警示。程式沒有猜使用者參數，也沒有宣稱模型自行修復。這兩次另計，因此本輪共 16 次執行：14 次前後對照＋2 次回復。</p><h2>真的執行紀錄</h2><ul>'+''.join('<li><a href="'+name+'">'+E(label)+'</a></li>' for name,label in [('runs/graph-run.json','14 次節點事件 JSON'),('runs/evidence-packs.json','投影片→Wiki→主張→來源'),('runs/research-result.json','主要合成資料結果'),('runs/coverage-result.json','Coverage 機制補測結果'),('runs/retrieval-observation.json','取得資料的真實問題'),('runs/activity-observation.json','活動度的真實發現'),('workflow.json','Graph 與退回條件'),('docs/discussion.md','先討論後生成的需求'),('prompts/01-wiki.md','Wiki 作者指令'),('prompts/02-teaching.md','教學簡報指令'),('prompts/03-review.md','審閱指令')])+'</ul><h2>本次 LLM 的角色</h2><p>本次 Codex 對話讀取來源、協作 Wiki 與教材。重播命令使用已保存的 LLM 作者輸出，沒有呼叫即時模型、沒有量測模型 token 或延遲，也沒有接券商。程式驗證通過不等於來源語意已獨立核實。</p></main>'
 out['evidence.html']=shell('流程與紀錄',evidence)
 out['runs/traceability.json']=json.dumps(packs,ensure_ascii=False,indent=2)+'\n'
 if write:
  for name,body in out.items():
   path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
  print('Built 18 slides · 8 Wiki chapters · 7 source pages · workflow evidence')
 return out

if __name__=='__main__':render()
