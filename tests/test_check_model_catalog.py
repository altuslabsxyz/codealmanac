import importlib.util
from pathlib import Path
from types import ModuleType

from codealmanac.services.config.model_catalog import catalog_model_ids
from codealmanac.services.harnesses.models import HarnessKind

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/check_model_catalog.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_model_catalog", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_drift_counts_hidden_models_as_served_but_not_candidates() -> None:
    script = load_script()

    drift = script.catalog_drift(
        HarnessKind.CODEX,
        served=("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-sol"),
        hidden=("gpt-6-luna", "gpt-5.6-luna"),
    )

    assert drift.harness is HarnessKind.CODEX
    assert drift.stale == ("gpt-6.1-sol", "gpt-6-astra")
    assert drift.hidden == ("gpt-6-luna",)
    assert drift.candidates == ("gpt-5.6-terra",)


def test_report_lines_mark_stale_hidden_candidates_and_skipped() -> None:
    script = load_script()
    report = script.CatalogReport(
        listings=(
            script.ProviderListing(
                harness=HarnessKind.CODEX,
                served=("gpt-5.6-sol", "gpt-5.6-terra"),
                hidden=("gpt-6-luna", "gpt-5.6-luna"),
            ),
            script.ProviderListing(
                harness=HarnessKind.CLAUDE,
                skipped="ANTHROPIC_API_KEY is not set",
            ),
        )
    )

    lines = script.report_lines(report)

    statuses = {
        line.split()[1]: line.split()[-1]
        for line in lines
        if line.startswith("  catalog  ")
    }
    assert "codex: 2 served, 2 hidden" in lines
    assert statuses["gpt-6.1-sol"] == "stale"
    assert statuses["gpt-6-astra"] == "stale"
    assert statuses["gpt-6-luna"] == "hidden"
    assert statuses["gpt-5.6-sol"] == "served"
    assert any(
        line.startswith("  served   gpt-5.6-terra") and line.endswith("candidate")
        for line in lines
    )
    assert any(
        line.startswith("  hidden   gpt-5.6-luna") and line.endswith("picker")
        for line in lines
    )
    assert "claude: skipped" in lines
    assert "  ANTHROPIC_API_KEY is not set" in lines
    assert lines[-1].startswith("stale catalog ids: refresh ")
    assert report.stale() is True


def test_report_is_clean_when_every_catalog_id_is_served_or_hidden() -> None:
    script = load_script()
    claude_ids = catalog_model_ids(HarnessKind.CLAUDE)
    report = script.CatalogReport(
        listings=(
            script.ProviderListing(
                harness=HarnessKind.CLAUDE,
                served=claude_ids[:-1],
                hidden=claude_ids[-1:],
            ),
            script.ProviderListing(harness=HarnessKind.CODEX, skipped="offline"),
        )
    )

    assert report.stale() is False
    assert not any("stale" in line for line in script.report_lines(report))
