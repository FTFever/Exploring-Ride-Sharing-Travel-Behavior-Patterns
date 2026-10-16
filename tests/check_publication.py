"""Check the executed research record without downloading data or fitting models."""
import ast
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
count = 0
names = ['01_data_ingestion.ipynb', '02_data_preparation_2019_2025.ipynb',
         '03_analysis_baseline_demand.ipynb', '04_analysis_temporal_patterns.ipynb',
         '05_analysis_spatial_patterns.ipynb', '06_model_hourly_demand_forecasting.ipynb']
for name in names:
    path = ROOT / 'notebooks' / name
    nb = json.loads(path.read_text(encoding='utf-8'))
    assert nb['cells'][0]['cell_type'] == 'code', path
    assert 'RAW_DIR' in ''.join(nb['cells'][0]['source']), path
    figures = 0
    executions = []
    for index, cell in enumerate(nb['cells']):
        assert not re.search(r'[CDQ]:[\\/]', ''.join(cell['source'])), (path, index)
        if cell['cell_type'] != 'code':
            continue
        source = ''.join(cell['source'])
        if name.startswith('02_'):
            assert not cell.get('outputs'), (path, index, '02 must remain unexecuted')
            assert cell.get('execution_count') is None, (path, index)
        else:
            assert isinstance(cell.get('execution_count'), int), (path, index, 'not executed')
            executions.append(cell['execution_count'])
            for output in cell.get('outputs', []):
                assert output['output_type'] != 'error', (path, index, output)
                if 'image/png' in output.get('data', {}):
                    raw = base64.b64decode(output['data']['image/png'])
                    assert raw.startswith(b'\x89PNG\r\n\x1a\n'), (path, index)
                    figures += 1
                for value in [output.get('text', ''), output.get('data', {}).get('text/plain', ''),
                              output.get('data', {}).get('text/html', '')]:
                    assert not re.search(r'[CDQ]:[\\/]', str(value)), (path, index, 'private output path')
        assert not re.search(r'[CDQ]:[\\/]', source), (path, index, 'private drive')
        # IPython shell/magic lines are valid notebook syntax, not Python syntax.
        python = '\n'.join(line if not line.lstrip().startswith(('%', '!'))
                           else '# IPython command' for line in source.splitlines())
        ast.parse(python, filename=f'{path.name}:cell{index}')
        count += 1
    if not name.startswith('02_'):
        assert figures > 0, (path, 'missing embedded figures')
        assert executions == sorted(set(executions)), (path, 'invalid execution sequence')
        assert nb['metadata']['research_execution']['model_training_executed'] is False
    else:
        source = '\n'.join(''.join(c['source']) for c in nb['cells'])
        assert 'SOURCE_YEARS = [2019, 2021, 2022, 2023, 2024, 2025]' in source
        assert 'len(TARGET_MONTHS) == 71' in source
        assert 'len(validation) == 213' in source
        assert 'errorifexists' in source
    if path.name.startswith('06_'):
        assert any('EXECUTION_MODE = "review"' in ''.join(c['source']) for c in nb['cells'])
    if path.name.startswith(('03_', '04_', '05_')):
        source = '\n'.join(''.join(c['source']) for c in nb['cells'])
        assert 'YEARS = [2021, 2022, 2023, 2024, 2025]' in source
        assert 'DIRECTIONS = ["pickup"]' in source
        assert 'Findings to record' in source or path.name.startswith('03_')
    if path.name.startswith('05_'):
        assert 'COMPARISONS = [(2021, 2024), (2024, 2025)]' in source

for path in list((ROOT / 'src').rglob('*.py')) + list((ROOT / 'pipelines').glob('published_*.py')):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    assert not re.search(r'[CDQ]:[\\/]', path.read_text(encoding='utf-8')), path
for name in ['README.md', 'LICENSE', 'CITATION.cff', 'docs/DATA_SOURCES.md',
             'docs/REPRODUCIBILITY.md', 'src/forecasting/feature_dictionary.csv']:
    assert (ROOT / name).is_file(), name
readme = (ROOT / 'README.md').read_text(encoding='utf-8-sig')
for target in re.findall(r'\]\(([^)]+)\)', readme):
    if not target.startswith(('https:', 'http:', '#')):
        assert (ROOT / target).exists(), target
print(f'PASS: {count} code cells in {len(names)} notebooks; executed results, 02 scope, paths and links.')
