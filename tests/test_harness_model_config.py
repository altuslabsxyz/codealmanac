from pathlib import Path

import pytest

from codealmanac.core.errors import ValidationFailed
from codealmanac.services.config.model_catalog import (
    DEFAULT_HARNESS_MODELS,
    HARNESS_MODEL_CATALOG,
    ModelSource,
    catalog_model_ids,
    model_source,
    validate_harness_model,
)
from codealmanac.services.config.models import (
    ConfigKey,
    HarnessConfig,
)
from codealmanac.services.config.requests import SetConfigValueRequest
from codealmanac.services.config.service import ConfigService
from codealmanac.services.config.store import ConfigStore
from codealmanac.services.harnesses.models import HarnessKind
from codealmanac.services.setup.requests import RunSetupRequest
from codealmanac.services.telemetry.models import telemetry_model_value


class UnusedAutomation:
    def reconcile_task(self, request):
        raise AssertionError("automation is not used for harness config")


def config_service(tmp_path: Path) -> ConfigService:
    return ConfigService(
        store=ConfigStore(),
        user_config_path=tmp_path / "config.toml",
        automation=UnusedAutomation(),
    )


def test_catalog_lists_every_harness_with_defaults_first() -> None:
    all_ids: list[str] = []
    for harness in HarnessKind:
        models = HARNESS_MODEL_CATALOG[harness]
        assert len(models) > 0
        assert DEFAULT_HARNESS_MODELS[harness] == models[0].id
        for model in models:
            assert model.id.strip() == model.id
            assert model.label
            assert model.detail
        all_ids.extend(model.id for model in models)

    assert len(all_ids) == len(set(all_ids))
    assert "gpt-6.1-sol" in catalog_model_ids(HarnessKind.CODEX)
    assert "claude-sonnet-5-5" in catalog_model_ids(HarnessKind.CLAUDE)


def test_harness_config_rejects_catalog_model_of_other_harness() -> None:
    with pytest.raises(ValueError, match="is a codex catalog model"):
        HarnessConfig(default=HarnessKind.CLAUDE, model="gpt-6.1-sol")


def test_harness_config_accepts_custom_model_id() -> None:
    config = HarnessConfig(default=HarnessKind.CLAUDE, model="claude-opus-6")

    assert config.model == "claude-opus-6"
    assert model_source(config.model, config.default) is ModelSource.CUSTOM
    assert model_source("claude-sonnet-5-5", HarnessKind.CLAUDE) is (
        ModelSource.CATALOG
    )


@pytest.mark.parametrize("value", ["", "   ", "gpt 6"])
def test_harness_config_rejects_blank_or_spaced_model(value: str) -> None:
    with pytest.raises(ValueError, match="harness.model"):
        HarnessConfig(default=HarnessKind.CODEX, model=value)


def test_validate_harness_model_strips_and_labels_errors() -> None:
    assert validate_harness_model(" gpt-6.1-sol ", HarnessKind.CODEX) == "gpt-6.1-sol"

    with pytest.raises(ValueError, match='--model "claude-haiku-5-5" is a claude'):
        validate_harness_model("claude-haiku-5-5", HarnessKind.CODEX, "--model")


def test_setup_request_rejects_catalog_model_of_other_harness() -> None:
    with pytest.raises(ValueError, match="setup model"):
        RunSetupRequest(harness=HarnessKind.CODEX, model="claude-sonnet-5-5")


def test_config_set_harness_default_resets_model_to_harness_default(
    tmp_path: Path,
) -> None:
    service = config_service(tmp_path)

    service.set(SetConfigValueRequest(key=ConfigKey.HARNESS_DEFAULT, value="claude"))

    entries = {entry.key: entry.value for entry in service.list()}
    assert entries[ConfigKey.HARNESS_DEFAULT] == "claude"
    assert entries[ConfigKey.HARNESS_MODEL] == "claude-sonnet-5-5"


def test_config_set_harness_model_rejects_other_harness_catalog_model(
    tmp_path: Path,
) -> None:
    service = config_service(tmp_path)
    service.set(SetConfigValueRequest(key=ConfigKey.HARNESS_DEFAULT, value="claude"))

    with pytest.raises(ValidationFailed, match="is a codex catalog model"):
        service.set(
            SetConfigValueRequest(key=ConfigKey.HARNESS_MODEL, value="gpt-6.1-sol")
        )


def test_config_set_harness_model_accepts_custom_id_and_reports_source(
    tmp_path: Path,
) -> None:
    service = config_service(tmp_path)

    custom = service.set(
        SetConfigValueRequest(key=ConfigKey.HARNESS_MODEL, value=" gpt-6.2-nova ")
    )
    listed = service.set(
        SetConfigValueRequest(key=ConfigKey.HARNESS_MODEL, value="gpt-6-luna")
    )

    assert custom.value == "gpt-6.2-nova"
    assert custom.model_source is ModelSource.CUSTOM
    assert listed.model_source is ModelSource.CATALOG
    assert service.load_user().harness.model == "gpt-6-luna"


def test_telemetry_model_value_exports_custom_marker_for_unlisted_ids() -> None:
    assert telemetry_model_value(HarnessKind.CODEX, "gpt-6.1-sol") == "gpt-6.1-sol"
    assert telemetry_model_value(HarnessKind.CODEX, "/Users/alice/secret") == "custom"
    assert telemetry_model_value(HarnessKind.CODEX, "claude-sonnet-5-5") == "custom"
