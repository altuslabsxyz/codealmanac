from datetime import timedelta

from humanfriendly import InvalidTimespan, parse_timespan

from codealmanac.app import CodeAlmanac
from codealmanac.core.errors import ValidationFailed
from codealmanac.services.config.model_catalog import (
    DEFAULT_HARNESS_MODELS,
    validate_harness_model,
)
from codealmanac.services.config.models import UserConfig
from codealmanac.services.harnesses.models import HarnessKind


def load_user_cli_config(app: CodeAlmanac) -> UserConfig:
    return app.config.load_user()


def resolve_harness(value: str | None, config: UserConfig) -> HarnessKind:
    if value is None:
        return config.harness.default
    return HarnessKind(value)


def resolve_harness_model(
    harness: HarnessKind,
    config: UserConfig,
    requested: str | None = None,
) -> str:
    """Pick the model for one command: `--model`, then config, then catalog."""

    if requested is not None:
        return requested_harness_model(harness, requested)
    if harness == config.harness.default:
        return config.harness.model
    return DEFAULT_HARNESS_MODELS[harness]


def requested_harness_model(harness: HarnessKind, requested: str) -> str:
    """Validate an explicit `--model` value against the runner it will use."""

    try:
        return validate_harness_model(requested, harness, "--model")
    except ValueError as error:
        raise ValidationFailed(str(error)) from error


def parse_optional_duration(value: str | None, flag: str) -> timedelta | None:
    if value is None:
        return None
    try:
        seconds = parse_timespan(value)
    except InvalidTimespan as error:
        raise ValidationFailed(f"invalid {flag} value: {value}") from error
    return timedelta(seconds=seconds)
