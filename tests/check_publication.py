"""Static release checks; intentionally never download data or fit models."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
count = 0
for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
    nb = json.loads(path.read_text(encoding='utf-8'))
    assert nb['cells'][0]['cell_type'] == 'code', path
    assert 'RAW_DIR' in ''.join(nb['cells'][0]['source']), path
    for index, cell in enumerate(nb['cells']):
        assert not re.search(r'[CDQ]:[\\/]', ''.join(cell['source'])), (path, index)
        if cell['cell_type'] != 'code':
            continue
        source = ''.join(cell['source'])
        assert not cell.get('outputs'), (path, index, 'saved outputs')
        assert cell.get('execution_count') is None, (path, index)
        assert not re.search(r'[CDQ]:[\\/]', source), (path, index, 'private drive')
        # IPython shell/magic lines are valid notebook syntax, not Python syntax.
        python = '\n'.join(line if not line.lstrip().startswith(('%', '!'))
                           else '# IPython command' for line in source.splitlines())
        ast.parse(python, filename=f'{path.name}:cell{index}')
        count += 1
    if path.name.startswith('06_'):
        assert any('EXECUTION_MODE = "review"' in ''.join(c['source']) for c in nb['cells'])

for path in list((ROOT / 'src').rglob('*.py')) + list((ROOT / 'pipelines').glob('published_*.py')):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    assert not re.search(r'[CDQ]:[\\/]', path.read_text(encoding='utf-8')), path
for name in ['README.md', 'LICENSE', 'CITATION.cff', 'docs/DATA_SOURCES.md',
             'docs/REPRODUCIBILITY.md', 'src/forecasting/feature_dictionary.csv']:
    assert (ROOT / name).is_file(), name
print(f'PASS: {count} code cells in nine notebooks; portable scripts and release documents.')
