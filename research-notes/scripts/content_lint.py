"""Check editorial contracts and declared arithmetic, without asserting factual truth."""
import ast
import math
from pathlib import Path
import re

SECTIONS = ('我想釐清的問題', '一個算得出來的例子', '我會怎麼檢查', '還需要注意什麼')
PLACEHOLDERS = (
    '寫出具體的疑惑', '寫出例子', '寫出步驟', '寫出限制', '提供可以照做的步驟',
    '請填寫', '填寫你', '待補正文', 'replace-with', 'lorem ipsum', 'todo', 'tbd',
)
PERSONAL_REPORT = re.compile(r'我(?:親自|實際|實測)|我用相同本金測試|我在.{0,12}(?:測試|實測|操作)')
LINK = re.compile(r'\[([^\]]+)\]\(([^\s)]+)\)')


def arithmetic(expression):
    """Evaluate bounded arithmetic literals only. No names, calls or Python eval."""
    if not isinstance(expression, str) or len(expression) > 180:
        raise ValueError('Invalid arithmetic expression')
    tree = ast.parse(expression, mode='eval')
    if len(list(ast.walk(tree))) > 60:
        raise ValueError('Arithmetic expression too large')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            result = float(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            result = -value if isinstance(node.op, ast.USub) else value
        elif isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): result = left + right
            elif isinstance(node.op, ast.Sub): result = left - right
            elif isinstance(node.op, ast.Mult): result = left * right
            elif isinstance(node.op, ast.Div): result = left / right
            elif isinstance(node.op, ast.FloorDiv): result = left // right
            elif isinstance(node.op, ast.Pow) and abs(right) <= 20: result = left ** right
            else: raise ValueError('Unsupported arithmetic operation')
        else:
            raise ValueError('Arithmetic accepts numeric literals only')
        if not isinstance(result, (float, int)) or not math.isfinite(result) or abs(result) > 1e15:
            raise ValueError('Arithmetic outside finite bounds')
        return result
    try:
        return visit(tree.body)
    except (ZeroDivisionError, OverflowError) as error:
        raise ValueError('Undefined arithmetic') from error


def sections(body):
    parts = re.split(r'^## (.+)\n', body, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def lint_notes(notes, sources, root, examples):
    note_ids = {n['id'] for n in notes}
    if set(examples) != note_ids:
        raise ValueError('Example registry must match all note IDs')
    used_sources = set()
    report = dict(notes=len(notes), substantive_examples=0, teaching_labels=0,
                  cited_sources=0, arithmetic_checks=0, personal_records=0,
                  manual_claim_review_required=True)
    for note in notes:
        identifier, body = note['id'], note['body']
        def fail(message): raise ValueError(f'{identifier}: {message}')
        text = ' '.join([note['title'], note['summary'], note['origin'], body]).casefold()
        if any(token in text for token in PLACEHOLDERS):
            fail('Template placeholder or unfinished prose')
        parts = sections(body)
        if tuple(parts) != SECTIONS:
            fail('Four required sections missing or out of order')
        for name, content in parts.items():
            plain = re.sub(r'[\s#|`*_\-]', '', LINK.sub(r'\1', content))
            if len(plain) < 45:
                fail(f'Section has insufficient substance: {name}')
        example = parts[SECTIONS[1]]
        if not re.search(r'\d', example):
            fail('Worked example must include numeric inputs and results')
        if note['example_kind'] != 'teaching':
            fail('Only teaching examples currently supported')
        if '教學假設' not in example:
            fail('Teaching label required in example section')
        steps = re.findall(r'^- (.+)$', parts[SECTIONS[2]], flags=re.M)
        if len(steps) < 2 or any(len(step.strip()) < 10 for step in steps):
            fail('At least two explicit inspection steps required')
        content_without_code = re.sub(r'```.*?```|`[^`]*`', '', body, flags=re.S)
        cited_urls = {url for _, url in LINK.findall(content_without_code)}
        for source_id in note['sources']:
            if sources[source_id]['url'] not in cited_urls:
                fail(f'Registered source absent from body citations: {source_id}')
        registered_urls = {sources[key]['url'] for key in note['sources']}
        if any(url.startswith('https://') and url not in registered_urls for url in cited_urls):
            fail('Body contains an unregistered external citation')
        used_sources.update(note['sources'])
        record = note['experience_record']
        if record is not None and (not isinstance(record, str) or not record):
            fail('Experience record must be a path or null')
        if PERSONAL_REPORT.search(body) and not record:
            fail('Personal observation requires an author-supplied record')
        if record:
            path = (root / record).resolve()
            if not path.is_relative_to((root / 'content/observations').resolve()) or not path.is_file():
                fail('Experience record missing or outside observations')
            if '作者' not in note['origin']:
                fail('Author experience must be attributed in origin')
            report['personal_records'] += 1
        experiment = note['experiment']
        if experiment is not None:
            extensions = {'script': '.py', 'input': '.csv', 'output': '.json', 'chart': '.svg'}
            if not isinstance(experiment, dict) or set(experiment) != set(extensions):
                fail('Experiment needs script, input, output and chart')
            for key, suffix in extensions.items():
                if not isinstance(experiment[key], str):
                    fail('Experiment paths must be text')
                path = (root / experiment[key]).resolve()
                if not path.is_relative_to(root.resolve()) or not path.is_file() or path.suffix != suffix:
                    fail('Experiment file missing, wrong type or outside project')
        checks = examples[identifier]
        if not isinstance(checks, list) or not checks:
            fail('At least one independently computed example required')
        for check in checks:
            if set(check) != {'expression', 'expected', 'display'}:
                fail('Arithmetic check fields differ')
            expected = check['expected']
            if type(expected) not in (int, float) or not math.isfinite(expected):
                fail('Expected example result must be finite')
            computed = arithmetic(check['expression'])
            if not math.isclose(computed, expected, rel_tol=1e-10, abs_tol=1e-10):
                fail('Declared example result contradicts arithmetic')
            if not check['display'] or check['display'] not in example:
                fail('Declared example result absent from worked example')
            report['arithmetic_checks'] += 1
        report['substantive_examples'] += 1
        report['teaching_labels'] += 1
    report['cited_sources'] = len(used_sources)
    report['unused_sources'] = sorted(set(sources) - used_sources)
    if report['unused_sources']:
        raise ValueError('Uncited source registry entries: ' + ', '.join(report['unused_sources']))
    return report
