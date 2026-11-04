import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'data' / 'catalog' / 'curated.json'


def cli(*args):
    env=dict(os.environ)
    env['PYTHONPATH']=str(SOURCE.parents[2]/'src')
    return subprocess.run([sys.executable,'-m','rigpilot.cli',*map(str,args)],text=True,capture_output=True,env=env)


def seed(tmp_path, source=SOURCE):
    db=tmp_path/'catalog.sqlite'
    result=cli('import','--source',source,'--db',db)
    assert result.returncode==0,result.stderr
    return db


def modified(tmp_path, change):
    catalog=json.loads(SOURCE.read_text())
    change(catalog)
    source=tmp_path/'modified.json'
    source.write_text(json.dumps(catalog))
    return source


def test_cli_import_then_recommend_emits_one_structured_build(tmp_path):
    db=seed(tmp_path)
    out=cli('recommend','--db',db,'--budget-vnd','26000000','--workload','gaming','--json')
    assert out.returncode==0,out.stderr
    payload=json.loads(out.stdout)
    assert set(payload['selected']['part_ids']) == {'cpu','motherboard','ram','gpu','storage','psu','case','cooler'}
    assert payload['compatibility']['status'] == 'COMPATIBLE'
    assert isinstance(payload['snapshot_id'],str)
    assert payload['status']=='PROVISIONAL' # No curated performance comparisons yet.


def test_cli_known_cpu_socket_conflict_keeps_incompatible_issue(tmp_path):
    def clash(data):
        for board in (x for x in data['products'] if x['kind']=='motherboard'):
            board['specs']['socket']='UNSUPPORTED' 
    db=seed(tmp_path,modified(tmp_path,clash))
    out=cli('recommend','--db',db,'--budget-vnd','26000000','--workload','gaming','--json')
    assert out.returncode==0
    payload=json.loads(out.stdout)
    assert payload['status']=='PROVISIONAL'
    assert payload['compatibility']['status']=='INCOMPATIBLE'
    assert 'CPU_SOCKET_MISMATCH' in {issue['code'] for issue in payload['compatibility']['issues']}


def test_cli_missing_price_is_provisional(tmp_path):
    def no_price(data):
        for offer in data['offers']:
            if next(p for p in data['products'] if p['product_id'] == offer['product_id'])['kind'] == 'cpu':
                offer['price_vnd']=None
    db=seed(tmp_path,modified(tmp_path,no_price))
    out=cli('recommend','--db',db,'--budget-vnd','26000000','--workload','gaming','--json')
    assert out.returncode==0
    payload=json.loads(out.stdout)
    assert payload['status']=='PROVISIONAL'
    assert payload['constraints']['total_purchase_vnd'] is None


def test_cli_reimport_is_idempotent(tmp_path):
    db=seed(tmp_path)
    second=cli('import','--source',SOURCE,'--db',db)
    assert second.returncode==0
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT COUNT(*) FROM catalog_snapshots').fetchone()[0]==1


def test_cli_rejects_bad_budget_without_creating_db(tmp_path):
    db=tmp_path/'should-not-create.db'
    out=cli('recommend','--db',db,'--budget-vnd','-1','--workload','gaming','--json')
    assert out.returncode==2
    assert not db.exists()


def test_cli_output_contains_no_unsourced_fps_claim(tmp_path):
    db=seed(tmp_path)
    out=cli('recommend','--db',db,'--budget-vnd','26000000','--workload','gaming','--json')
    assert out.returncode==0
    payload=json.loads(out.stdout)
    assert 'fps' not in ' '.join(payload['explanation']).lower()
