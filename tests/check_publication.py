"""Static release checks; intentionally never download data or fit models."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
count = 0
names = ['01_data_ingestion.ipynb', '02a_prepare_hourly_2021_2023.ipynb',
         '02b_prepare_hourly_2024_2025.ipynb', '02c_validate_selected_repairs.ipynb',
         '03_analysis_baseline_demand.ipynb', '04_analysis_temporal_patterns.ipynb',
         '05_analysis_spatial_patterns.ipynb', '06_model_hourly_demand_forecasting.ipynb']
for name in names:
    path = ROOT / 'notebooks' / name
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
    if path.name.startswith(('03_', '04_', '05_')):
        source = '\n'.join(''.join(c['source']) for c in nb['cells'])
        assert 'YEARS = [2021, 2022, 2023, 2024, 2025]' in source
        assert "DIRECTIONS = ['pickup']" in source
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
print(f'PASS: {count} code cells in {len(names)} notebooks; scope, paths and README links.')
