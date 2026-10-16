"""Recommended runner models per harness.

The catalog is a recommended list, not an allowlist. Setup shows it, config
defaults come from it, and catalog ids must match their harness. Any other
single-token model id is passed to the harness as entered; the provider
validates it on the first request. Refreshing the catalog means editing one
tuple per harness here. `scripts/check_model_catalog.py` reports drift between
this table and what the signed-in providers serve.
"""

from enum import StrEnum

from codealmanac.core.models import CodeAlmanacModel
from codealmanac.services.harnesses.kinds import HarnessKind


class CatalogModel(CodeAlmanacModel):
    id: str
    label: str
    detail: str


class ModelSource(StrEnum):
    CATALOG = "catalog"
    CUSTOM = "custom"


HARNESS_MODEL_CATALOG: dict[HarnessKind, tuple[CatalogModel, ...]] = {
    HarnessKind.CODEX: (
        CatalogModel(
            id="gpt-6.1-sol",
            label="GPT-6.1 Sol",
            detail="recommended wiki-writing runner",
        ),
        CatalogModel(
            id="gpt-6-astra",
            label="GPT-6 Astra",
            detail="deep rebuilds and hard gardens",
        ),
        CatalogModel(
            id="gpt-6-luna",
            label="GPT-6 Luna",
            detail="fast routine maintenance",
        ),
        CatalogModel(
            id="gpt-5.6-sol",
            label="GPT-5.6 Sol",
            detail="previous generation, served during the GPT-6 rollout",
        ),
    ),
    HarnessKind.CLAUDE: (
        CatalogModel(
            id="claude-sonnet-5-5",
            label="Claude Sonnet 5.5",
            detail="recommended maintenance runner",
        ),
        CatalogModel(
            id="claude-opus-5-5",
            label="Claude Opus 5.5",
            detail="deep rebuilds and hard gardens",
        ),
        CatalogModel(
            id="claude-haiku-5-5",
            label="Claude Haiku 5.5",
            detail="small routine updates",
        ),
        CatalogModel(
            id="claude-fable-5-1",
            label="Claude Fable 5.1",
            detail="frontier runner for the hardest rebuilds; needs Fable access",
        ),
    ),
}
DEFAULT_HARNESS_MODELS: dict[HarnessKind, str] = {
    harness: models[0].id for harness, models in HARNESS_MODEL_CATALOG.items()
}
DEFAULT_HARNESS_MODEL = DEFAULT_HARNESS_MODELS[HarnessKind.CODEX]


def catalog_models(harness: HarnessKind) -> tuple[CatalogModel, ...]:
    return HARNESS_MODEL_CATALOG[harness]


def catalog_model_ids(harness: HarnessKind) -> tuple[str, ...]:
    return tuple(model.id for model in catalog_models(harness))


def catalog_harness_for(model: str) -> HarnessKind | None:
    for harness in HarnessKind:
        if model in catalog_model_ids(harness):
            return harness
    return None


def model_source(model: str, harness: HarnessKind) -> ModelSource:
    if model in catalog_model_ids(harness):
        return ModelSource.CATALOG
    return ModelSource.CUSTOM


def normalize_model_id(value: str, label: str = "harness.model") -> str:
    model = value.strip()
    if not model:
        raise ValueError(f"{label} is required")
    if any(character.isspace() for character in model):
        raise ValueError(f"{label} must be a single model id without spaces")
    return model


def validate_harness_model(
    value: str,
    harness: HarnessKind,
    label: str = "harness.model",
) -> str:
    """Return the model id to run on `harness`.

    Catalog ids must belong to the selected harness. Any other id passes
    through unchanged; the provider decides whether it exists.
    """

    model = normalize_model_id(value, label)
    listed_under = catalog_harness_for(model)
    if listed_under is not None and listed_under != harness:
        allowed = ", ".join(catalog_model_ids(harness))
        raise ValueError(
            f'{label} "{model}" is a {listed_under.value} catalog model; '
            f"{harness.value} catalog models are {allowed}, and any other id "
            f"is passed to {harness.value} as entered"
        )
    return model

