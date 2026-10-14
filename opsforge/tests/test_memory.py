from opsforge.memory import LongTermMemory, RunState, VectorMemory


def test_long_term_roundtrip_and_lessons(tmp_path):
    ltm = LongTermMemory(tmp_path)
    p = ltm.save_incident("DB pool exhausted", "503s on /pay", "long transactions", "cap txn time", ["checkout-api"])
    assert p.exists() and "long transactions" in p.read_text()
    ltm.add_lesson("Set statement timeouts on background jobs")
    ltm.add_lesson("Set statement timeouts on background jobs")  # dedupe
    assert ltm.lessons() == ["Set statement timeouts on background jobs"]


def test_vector_recall_finds_relevant_incident(tmp_path):
    ltm = LongTermMemory(tmp_path)
    ltm.save_incident("DB pool exhausted", "timeouts acquiring database connection", "long-lived transactions hold pool", "limit txn duration")
    ltm.save_incident("Disk full on logger", "log volume at 100 percent", "no log rotation", "enable logrotate")
    vm = VectorMemory(tmp_path / "idx.json")
    vm.reindex(ltm.all_documents())
    top = vm.search("connection pool timeout database", k=1)[0]
    assert "db-pool" in top[0]


def test_vector_persistence(tmp_path):
    vm = VectorMemory(tmp_path / "idx.json")
    vm.upsert("a", "kubernetes pod crashloop oomkilled")
    vm.save()
    vm2 = VectorMemory(tmp_path / "idx.json")
    assert vm2.search("pod oomkilled")[0][0] == "a"


def test_run_state_context_and_cost():
    s = RunState(ticket={"id": "T1"})
    s.record("triage", "severity: SEV2", 0.0, cost_usd=0.01)
    s.record("plan", "do x", 0.0, cost_usd=0.02)
    assert "severity: SEV2" in s.context_for("triage", "plan")
    assert round(s.total_cost_usd, 2) == 0.03
    assert '"T1"' in s.to_json()
