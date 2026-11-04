import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from rigpilot.catalog.store import import_catalog

FIXTURE = Path(__file__).parent / "fixtures" / "catalog_test.json"
ROOT = Path(__file__).parents[1]


def cli(*args):
    env={**os.environ,"PYTHONPATH":str(ROOT / "src")}
    return subprocess.run([sys.executable,"-m","rigpilot.cli",*map(str,args)],cwd=ROOT,env=env,text=True,capture_output=True)


def test_cli_import_then_recommend_emits_one_structured_build(tmp_path):
    db=tmp_path / "pc.db"
    a=cli("import","--source",FIXTURE,"--db",db)
    assert a.returncode==0, a.stderr
    b=cli("recommend","--db",db,"--budget-vnd","25000000","--workload","gaming","--json")
    assert b.returncode==0, b.stderr
    output=json.loads(b.stdout)
    assert output["status"]=="PROVISIONAL"  # one item has unknown price
    assert len(output["selected"]["part_ids"])==8
    assert output["snapshot_id"]==json.loads(a.stdout)["snapshot_id"]
    assert output["constraints"]["budget_verified"] is False


def test_cli_known_cpu_socket_conflict_keeps_incompatible_issue(tmp_path):
    data=json.loads(FIXTURE.read_text())
    data['products'][0]['specs']['socket']='LGA1700'
    source=tmp_path/'conflict.json'
    source.write_text(json.dumps(data))
    db=tmp_path/'x.db'
    assert cli('import','--source',source,'--db',db).returncode==0
    result=cli('recommend','--db',db,'--budget-vnd','25000000','--workload','gaming','--json')
    assert result.returncode==0
    payload=json.loads(result.stdout)
    assert payload['compatibility']['status']=='INCOMPATIBLE'
    assert 'CPU_SOCKET_MISMATCH' in [i['code'] for i in payload['compatibility']['issues']]
    assert payload['status']!='RECOMMENDED'


def test_cli_missing_price_is_provisional(tmp_path):
    db=tmp_path/'db.sqlite'
    import_catalog(FIXTURE,db)
    result=cli('recommend','--db',db,'--budget-vnd','25000000','--workload','gaming','--json')
    assert result.returncode==0
    payload=json.loads(result.stdout)
    assert payload['constraints']['total_purchase_vnd'] is None
    assert payload['status']=='PROVISIONAL'


def test_cli_reimport_is_idempotent(tmp_path):
    db=tmp_path/'db.sqlite'
    one=cli('import','--source',FIXTURE,'--db',db)
    two=cli('import','--source',FIXTURE,'--db',db)
    assert one.returncode==two.returncode==0
    assert json.loads(one.stdout)==json.loads(two.stdout)
    with sqlite3.connect(db) as conn:
        assert conn.execute('select count(*) from catalog_snapshots').fetchone()[0]==1


def test_cli_rejects_bad_budget_without_creating_db(tmp_path):
    db=tmp_path/'bad.db'
    result=cli('recommend','--db',db,'--budget-vnd','-1','--workload','gaming','--json')
    assert result.returncode==2 and not db.exists()


def test_cli_output_contains_no_unsourced_fps_claim(tmp_path):
    db=tmp_path/'db.sqlite'
    import_catalog(FIXTURE,db)
    result=cli('recommend','--db',db,'--budget-vnd','25000000','--workload','gaming','--json')
    assert result.returncode==0
    import re
    assert re.search(r'\d+(?:\.\d+)?\s*fps',result.stdout,re.IGNORECASE) is None


def test_cli_snapshot_id_matches_result_during_concurrent_import(tmp_path, monkeypatch, capsys):
    from rigpilot import cli as cli_module
    from rigpilot.application.recommend import recommend_from_db as real_recommend

    db = tmp_path / "race.db"
    initial_id = import_catalog(FIXTURE, db)
    newer_doc = json.loads(FIXTURE.read_text())
    newer_doc["offers"][1]["price_vnd"] = 9_000_000
    newer_file = tmp_path / "updated.json"
    newer_file.write_text(json.dumps(newer_doc))

    def mutate_after_recommend(request, path, snapshot_id=None):
        result = real_recommend(request, path, snapshot_id)
        import_catalog(newer_file, path)
        return result

    monkeypatch.setattr(cli_module, "recommend_from_db", mutate_after_recommend)
    assert cli_module.main(["recommend", "--db", str(db), "--budget-vnd", "25000000", "--workload", "gaming", "--json"]) == 0
    answer = json.loads(capsys.readouterr().out)
    assert answer["snapshot_id"] == initial_id
    assert answer["constraints"]["total_purchase_vnd"] is None
