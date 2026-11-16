"""Check source contracts, generated artifacts and every local HTML link."""
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from build import ROOT, load_notes, render

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
    expected = render(notes, sources)
    count = 0
    for name, content in expected.items():
        path = ROOT / name
        if not path.is_file() or path.read_text() != content:
            raise ValueError(f'Stale artifact {name}; run scripts/build.py')
        if not name.endswith('.html'):
            continue
        parser = Links()
        parser.feed(content)
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme:
                if url.scheme != 'https':
                    raise ValueError(f'Unexpected protocol {link}')
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(ROOT) or not target.is_file():
                raise ValueError(f'Broken local link in {name}: {link}')
            count += 1
    for required in ['AGENTS.md', 'README.md', 'templates/note.md', 'CHANGELOG.md', '.nojekyll']:
        if not (ROOT / required).is_file():
            raise ValueError(f'Missing project file {required}')
    print(f'PASS · {len(notes)} notes · {len(sources)} sources · {count} local links · all generated artifacts match source.')

if __name__ == '__main__':
    check()
