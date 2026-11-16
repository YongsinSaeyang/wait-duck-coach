"""Build a small, auditable Markdown notebook with the Python standard library."""
from datetime import date
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from content_lint import lint_notes

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ('量化入門', '回測實作', '研究方法')
SECTIONS = ('我想釐清的問題', '一個算得出來的例子', '我會怎麼檢查', '還需要注意什麼')
REPOSITORY = 'https://github.com/YongsinSaeyang/wait-duck-coach/tree/main/research-notes'


def load_notes():
    sources = json.loads((ROOT / 'content/sources.json').read_text())
    for key, source in sources.items():
        if not re.fullmatch(r'[a-z][a-z0-9-]+', key):
            raise ValueError(f'Invalid source ID {key}')
        if set(source) != {'title', 'publisher', 'url', 'checked'}:
            raise ValueError(f'Source fields differ: {key}')
        date.fromisoformat(source['checked'])
        if urlsplit(source['url']).scheme != 'https' or not urlsplit(source['url']).hostname:
            raise ValueError(f'Source URL must use HTTPS: {key}')
    notes = []
    for path in sorted((ROOT / 'content/notes').glob('*.md')):
        parts = path.read_text().split('\n---\n', 1)
        if len(parts) != 2 or not parts[0].startswith('---\n'):
            raise ValueError(f'Missing JSON front matter: {path.name}')
        meta = json.loads(parts[0][4:])
        required = {'id', 'title', 'date', 'updated', 'category', 'tags', 'summary', 'sources', 'related', 'origin', 'example_kind', 'experience_record', 'experiment'}
        if set(meta) != required:
            raise ValueError(f'Metadata fields differ: {path.name}')
        for key in ('id', 'title', 'date', 'updated', 'category', 'summary', 'origin'):
            if not isinstance(meta[key], str) or not meta[key].strip():
                raise ValueError(f'Missing text {key}: {path.name}')
        if not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', meta['id']):
            raise ValueError(f'Invalid slug: {path.name}')
        if path.name != f"{meta['date']}-{meta['id']}.md":
            raise ValueError(f'Filename differs from metadata: {path.name}')
        if date.fromisoformat(meta['updated']) < date.fromisoformat(meta['date']):
            raise ValueError(f'Updated date precedes creation: {path.name}')
        if meta['category'] not in CATEGORIES or not 30 <= len(meta['summary']) <= 120:
            raise ValueError(f'Category or summary invalid: {path.name}')
        for key, minimum, maximum in [('tags', 1, 4), ('sources', 1, 8), ('related', 1, 3)]:
            values = meta[key]
            if not isinstance(values, list) or not minimum <= len(values) <= maximum:
                raise ValueError(f'Invalid {key}: {path.name}')
            if any(not isinstance(x, str) or not x.strip() for x in values) or len(set(values)) != len(values):
                raise ValueError(f'Duplicate or invalid {key}: {path.name}')
        if not set(meta['sources']) <= sources.keys():
            raise ValueError(f'Unregistered source: {path.name}')
        body = parts[1].strip()
        if tuple(re.findall(r'^## (.+)$', body, re.M)) != SECTIONS:
            raise ValueError(f'Required four sections differ: {path.name}')
        notes.append({**meta, 'body': body, 'source_path': path.relative_to(ROOT).as_posix()})
    ids = [note['id'] for note in notes]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Empty notebook or duplicate IDs')
    for note in notes:
        if not set(note['related']) <= set(ids) or note['id'] in note['related']:
            raise ValueError(f"Broken related note: {note['id']}")
    examples = json.loads((ROOT / 'content/examples.json').read_text())
    lint_notes(notes, sources, ROOT, examples)
    return notes, sources


def inline(text):
    tokens = re.split(r'(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^\s)]+\))', text)
    result = []
    for token in tokens:
        if token.startswith('`') and token.endswith('`'):
            result.append('<code>' + escape(token[1:-1]) + '</code>')
        elif token.startswith('**') and token.endswith('**'):
            result.append('<strong>' + escape(token[2:-2]) + '</strong>')
        elif re.fullmatch(r'\[[^\]]+\]\([^\s)]+\)', token):
            label, url = re.fullmatch(r'\[([^\]]+)\]\(([^\s)]+)\)', token).groups()
            if urlsplit(url).scheme != 'https' or not urlsplit(url).hostname:
                raise ValueError(f'Unsupported content link {url}')
            result.append(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(label)} ↗</a>')
        else:
            result.append(escape(token))
    return ''.join(result)


def markdown(body):
    lines = body.splitlines()
    result = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith('```'):
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith('```'):
                code.append(lines[index])
                index += 1
            if index == len(lines):
                raise ValueError('Unclosed code block')
            result.append('<pre><code>' + escape('\n'.join(code)) + '</code></pre>')
        elif re.match(r'^#{1,3} ', line):
            title = line.lstrip('#').strip()
            level = len(line) - len(line.lstrip('#'))
            result.append(f'<h{level}>' + inline(title) + f'</h{level}>')
        elif re.match(r'^\d+\. ', line):
            items = []
            while index < len(lines) and re.match(r'^\d+\. ', lines[index]):
                items.append('<li>' + inline(re.sub(r'^\d+\. ', '', lines[index])) + '</li>')
                index += 1
            result.append('<ol>' + ''.join(items) + '</ol>')
            continue
        elif line.startswith('- '):
            items = []
            while index < len(lines) and lines[index].startswith('- '):
                items.append('<li>' + inline(lines[index][2:]) + '</li>')
                index += 1
            result.append('<ul>' + ''.join(items) + '</ul>')
            continue
        elif line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].startswith('|'):
                row = [cell.strip() for cell in lines[index].strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', cell) for cell in row):
                    rows.append(row)
                index += 1
            if rows:
                header = '<thead><tr>' + ''.join('<th scope="col">' + inline(c) + '</th>' for c in rows[0]) + '</tr></thead>'
                content = ''.join('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in row) + '</tr>' for row in rows[1:])
                result.append('<div class="table-wrap"><table>' + header + '<tbody>' + content + '</tbody></table></div>')
            continue
        else:
            paragraph = []
            while index < len(lines) and lines[index].strip() and not re.match(r'^(#{1,3} |\||- |```|\d+\. )', lines[index]):
                paragraph.append(lines[index])
                index += 1
            result.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            continue
        index += 1
    return '\n'.join(result)


def shell(title, body, prefix='', description='把投資問題慢慢拆開，留下可回查、可重做的筆記。', active='home'):
    return f'''<!doctype html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{escape(description, quote=True)}"><meta name="theme-color" content="#f8f6ee">
<title>{escape(title)} · 等等鴨研究筆記</title><link rel="icon" href="{prefix}assets/duck.svg" type="image/svg+xml">
<link rel="stylesheet" href="{prefix}assets/site.css"><script defer src="{prefix}assets/site.js"></script></head>
<body><a class="skip" href="#main">跳至主要內容</a>
<header class="site-header"><div class="header-inner"><a class="brand" href="{prefix}index.html"><img src="{prefix}assets/duck.svg" alt="" width="42" height="42"><span>等等鴨<small>RESEARCH NOTES</small></span></a>
<nav aria-label="主要導覽"><a {'aria-current="page"' if active == 'home' else ''} href="{prefix}index.html">筆記庫</a><a {'aria-current="page"' if active == 'rules' else ''} href="{prefix}rules.html">AI 工作規則</a><a href="{REPOSITORY}" target="_blank" rel="noopener noreferrer">GitHub ↗</a></nav></div></header>
{body}
<footer class="site-footer"><span>等等鴨研究筆記 <b>·</b> 先看懂，再往前。</span><a href="{prefix}AGENTS.md">閱讀 AGENTS.md ↗</a><span>楊祐宗 · 2026</span></footer>
<div id="toast" role="status" aria-live="polite"></div></body></html>'''


def card(note, prefix='', number=''):
    tags = ''.join('<span>' + escape(tag) + '</span>' for tag in note['tags'])
    return f'''<article class="note-card" data-note="{note['id']}"><div class="card-meta"><span class="category">{escape(note['category'])}</span><span>{escape(number)}</span></div>
<h3><a href="{prefix}notes/{note['id']}.html">{escape(note['title'])}</a></h3><p>{escape(note['summary'])}</p><div class="tags">{tags}</div>
<div class="card-footer"><span>{note['updated'].replace('-', '.')} · {max(2, round(len(note['body'])/320))} 分鐘</span><button type="button" class="save" data-save="{note['id']}" aria-label="收藏 {escape(note['title'], quote=True)}" aria-pressed="false">♡ 收藏</button></div></article>'''


def render(notes, sources):
    lookup = {n['id']: n for n in notes}
    incoming = {n['id']: [item for item in notes if n['id'] in item['related']] for n in notes}
    cards = ''.join(card(n, number=f'{i:02d}') for i, n in enumerate(notes, 1))
    filters = ''.join(f'<button type="button" data-category="{c}" aria-pressed="false">{c}</button>' for c in CATEGORIES)
    home = f'''<main id="main" class="wrap"><section class="hero"><div class="hero-copy"><div class="eyebrow"><span class="dot"></span> 一個慢慢長大的投資研究筆記庫</div>
<h1>讓每個「為什麼」，<br>都有一張<span>查得到的筆記。</span></h1><p>量化、回測、資料與那些踩過的坑。<br>陪你把看起來很懂的數字，變成自己真的理解的事。</p>
<div class="hero-actions"><a class="primary" href="#library">從一篇筆記開始 <span>↘</span></a><a class="text-link" href="rules.html">這個筆記庫怎麼長大？ →</a></div>
<div class="hero-facts"><span><b>{len(notes):02d}</b> 篇研究筆記</span><span><b>03</b> 個閱讀方向</span><span><b>01</b> 套可重用規則</span></div></div>
<aside class="hero-board"><span class="board-label">DUCK'S FIELD NOTES <span>✧</span></span><img class="hero-duck" src="assets/duck.svg" alt="抱著筆記本的等等鴨"><div class="sticky"><span class="tiny">今天先想清楚一件事</span><strong>0% 報酬，<br>真的安全嗎？</strong><a href="notes/no-trade-no-proof.html">從「未進場」開始查 →</a></div><span class="board-footer">一頁一頁，把自己的判斷留下來。</span></aside></section>
<section id="library" class="library"><div class="section-title"><div><div class="eyebrow">THE NOTEBOOK</div><h2>選一個問題，慢慢讀。</h2></div><p>每篇都有例子、檢查步驟和來源。</p></div>
<div class="library-layout"><aside class="library-sidebar"><label class="search-label" for="search">搜尋筆記</label><div class="search-box"><span aria-hidden="true">⌕</span><input id="search" type="search" placeholder="例如 回撤、費用、資料" autocomplete="off"></div><fieldset class="filters"><legend>閱讀方向</legend><button type="button" data-category="all" aria-pressed="true">全部筆記 <span>{len(notes)}</span></button>{filters}<button type="button" data-category="saved" aria-pressed="false">♡ 我的收藏</button></fieldset>
<div class="sidebar-note"><span>等等鴨的小提醒</span><p>先看這個數字怎麼來，<br>再看它漂不漂亮。</p></div><a class="rule-link" href="rules.html">打開 AI 工作手冊 ↗</a></aside>
<div class="library-content"><div class="results-head"><p id="result-count" role="status">共 {len(notes)} 篇筆記</p><button id="reset" type="button">重設篩選 ↻</button></div><div id="note-grid" class="note-grid">{cards}</div><div id="empty" hidden><h3>這裡還沒有符合的筆記。</h3><p>換個關鍵字，或試著讀讀其他方向。</p></div></div></div></section>
<section class="bottom-grid"><div class="try-panel" id="drawdown-tool"><div class="eyebrow">TRY A LITTLE</div><h2>跌下去，要漲多少才回得來？</h2><p>教學假設 · 無加減碼與費用，以固定本金計算。</p><label for="decline">從高點下跌 <output id="decline-value">20%</output></label><input id="decline" type="range" min="0" max="90" step="1" value="20"><div class="tool-result"><div><small>回本需要上漲</small><strong id="recovery" role="status" aria-live="polite" aria-atomic="true">25.00%</strong></div><p>計算方式<br><code id="recovery-formula">20% ÷ (1 − 20%)</code></p></div><a href="notes/drawdown-recovery.html">把這個例子讀完整 →</a></div>
<div class="grow-panel"><div class="eyebrow">BUILT TO GROW</div><h2>下次丟一份新資料，<br>讓 AI 照同一套規則接著做。</h2><ol><li><span>01</span>先讀 AGENTS.md，確認邊界和格式。</li><li><span>02</span>補來源，用同一份模板寫筆記。</li><li><span>03</span>檢查、建置，再更新整個筆記庫。</li></ol><a href="rules.html">看規則怎麼對上實作 ↗</a></div></section></main>'''
    output = {'index.html': shell('首頁', home)}
    for note in notes:
        source_cards = ''.join(f'<li><span>{escape(sources[k]["publisher"])}</span><a href="{escape(sources[k]["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(sources[k]["title"])} ↗</a><small>查閱 {sources[k]["checked"]}</small></li>' for k in note['sources'])
        related = ''.join(card(lookup[key], prefix='../') for key in note['related'])
        backlinks = ''.join(f'<li><a href="{item["id"]}.html">{escape(item["title"])}</a></li>' for item in incoming[note['id']])
        backlink_panel = '<section class="backlinks"><h2>哪些筆記連到這裡</h2><ul>' + backlinks + '</ul></section>' if backlinks else ''
        experiment = note['experiment']
        experiment_html = ''
        if experiment:
            experiment_html = '<section class="experiment"><h2>重現這個實驗</h2><p>教學輸入、可重跑腳本與產生的結果放在同一份專案。</p>'
            experiment_html += '<figure><img src="../' + escape(experiment['chart'], quote=True) + '" alt="三條教學執行路徑的期末資產比較"><figcaption>教學假設，依 CSV 輸入由 Python 重新產生。</figcaption></figure><div class="rule-actions">'
            for key, label in [('script', 'Python 腳本'), ('input', '教學輸入 CSV'), ('output', '計算結果 JSON')]:
                experiment_html += '<a href="../' + escape(experiment[key], quote=True) + '">' + label + ' ↗</a>'
            experiment_html += '</div></section>'
        record_link = '<a href="../' + escape(note['experience_record'], quote=True) + '">閱讀作者提供的觀察與限制 ↗</a>' if note['experience_record'] else ''
        origin = f'<div class="origin"><strong>這篇內容的依據</strong><p>{escape(note["origin"])}</p>{record_link}</div>'
        article = f'''<main id="main" class="article-wrap"><a class="back-link" href="../index.html#library">← 回到筆記庫</a><header class="article-header"><span class="category">{escape(note['category'])}</span><h1>{escape(note['title'])}</h1><p class="article-summary">{escape(note['summary'])}</p><div class="article-meta"><span>{note['updated']} 更新</span><span>{max(2, round(len(note['body'])/320))} 分鐘閱讀</span><button class="save" data-save="{note['id']}" aria-label="收藏 {escape(note['title'], quote=True)}" aria-pressed="false">♡ 收藏</button></div></header>{origin}<article class="prose">{markdown(note['body'])}</article>{experiment_html}<section class="sources"><h2>這篇的來源</h2><ul>{source_cards}</ul><a class="text-link" href="../{note['source_path']}">查看原始 Markdown ↗</a></section><section class="related"><div class="eyebrow">KEEP READING</div><h2>也許你會想接著看</h2><div class="note-grid">{related}</div></section>{backlink_panel}</main>'''
        output[f'notes/{note["id"]}.html'] = shell(note['title'], article, prefix='../', description=note['summary'], active='article')
    rules = (ROOT / 'AGENTS.md').read_text()
    manifest = '<ul class="file-tree">' + ''.join(f'<li><a href="{escape(n["source_path"])}">{escape(n["source_path"])}</a></li>' for n in notes) + '</ul>'
    rules_html = markdown(rules).replace("<h1>", "<h2>").replace("</h1>", "</h2>")
    body = f'''<main id="main" class="article-wrap rules-page"><a class="back-link" href="index.html">← 回到筆記庫</a><div class="eyebrow">THE RULEBOOK</div><h1>讓下一位 AI，<br>也知道怎麼接著做。</h1><p class="article-summary">這份工作手冊直接取自專案根目錄的 AGENTS.md。內容、檔案位置與檢查方式都能在儲存庫找到。</p><div class="rule-actions"><a class="primary" href="AGENTS.md">讀取原始 AGENTS.md ↗</a><a href="templates/note.md">下載筆記模板 ↗</a><a href="CHANGELOG.md">修改紀錄 ↗</a></div><div class="rule-summary"><div><strong>01</strong><span>固定文章格式</span></div><div><strong>02</strong><span>來源與原文對得上</span></div><div><strong>03</strong><span>產物自動更新</span></div></div><div class="prose">{rules_html}</div><details class="source-tree"><summary>目前的原始筆記清單</summary>{manifest}<a href="content/sources.json">來源登記 JSON ↗</a></details></main>'''
    output['rules.html'] = shell('AI 工作規則', body, active='rules')
    output['assets/notes.json'] = json.dumps(notes, ensure_ascii=False, indent=2) + '\n'
    return output


def build():
    notes, sources = load_notes()
    output = render(notes, sources)
    for name, content in output.items():
        path = ROOT / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(content)
    expected = {f'{note["id"]}.html' for note in notes}
    for old in (ROOT / 'notes').glob('*.html'):
        if old.name not in expected:
            old.unlink()
    print(f'Built {len(notes)} note pages, homepage, rulebook and search index.')


if __name__ == '__main__':
    build()
