from pathlib import Path

from opsforge.memory import LongTermMemory, VectorMemory
from opsforge.tools import recall_impl, save_incident_impl, search_logs_impl, service_metrics_impl

LOG = Path(__file__).resolve().parent.parent / "data" / "logs" / "sample.log"


def test_search_logs_filters():
    out = search_logs_impl(LOG, "checkout-api", "timeout")
    assert "timeout acquiring db connection" in out
    assert "payments-worker" not in out


def test_metrics_known_and_unknown():
    assert "db_pool_active" in service_metrics_impl("checkout-api")
    assert "no metrics" in service_metrics_impl("nope")


def test_save_then_recall(tmp_path):
    ltm = LongTermMemory(tmp_path)
    vm = VectorMemory(tmp_path / "i.json")
    save_incident_impl(ltm, vm, "Pool exhaustion", "db connection timeouts", "reconciler long transactions", "limit txn", "Cap txn duration")
    assert "Pool exhaustion" in recall_impl(vm, "database connection timeout")
    assert ltm.lessons() == ["Cap txn duration"]
