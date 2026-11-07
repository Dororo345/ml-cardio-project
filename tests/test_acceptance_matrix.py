import json
from scripts.lz9.synthetic_acceptance import cases, run
from test_end_to_end import live_url

def test_matrix_is_unique_and_has_negative_cases():
    matrix=cases()
    assert len(matrix)==50
    assert len({json.dumps(row[1],sort_keys=True) for row in matrix})==50
    assert sum(row[2]!=200 for row in matrix)==10

def test_all_50_real_http_cases(live_url):
    results=run(live_url)
    assert len(results)==50
    assert all(r['passed'] for r in results), [r for r in results if not r['passed']]
