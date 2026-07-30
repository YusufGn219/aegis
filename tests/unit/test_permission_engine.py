from aegis.permission.engine import PermissionEngine
from aegis.tools.base import RiskLevel


class _FakeTool:
    def __init__(self, name, risk_level):
        self.name = name
        self.risk_level = risk_level


def test_low_risk_auto_passes_without_prompt(monkeypatch):
    def fail_if_called(_):
        raise AssertionError("LOW risk icin input() cagrilmamali")

    monkeypatch.setattr("builtins.input", fail_if_called)
    engine = PermissionEngine()
    tool = _FakeTool("list_files", RiskLevel.LOW)
    assert engine.check_and_confirm(tool, {"folder": "/x"}) is True


def test_medium_risk_confirmed_with_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    engine = PermissionEngine()
    tool = _FakeTool("move_file", RiskLevel.MEDIUM)
    assert engine.check_and_confirm(tool, {"source": "/a", "destination": "/b"}) is True


def test_medium_risk_declined_with_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    engine = PermissionEngine()
    tool = _FakeTool("move_file", RiskLevel.MEDIUM)
    assert engine.check_and_confirm(tool, {"source": "/a", "destination": "/b"}) is False


def test_high_risk_confirmed_with_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    engine = PermissionEngine()
    tool = _FakeTool("delete_file", RiskLevel.HIGH)
    assert engine.check_and_confirm(tool, {"path": "/a"}) is True
