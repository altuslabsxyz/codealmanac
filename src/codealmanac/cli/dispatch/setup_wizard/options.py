from dataclasses import dataclass, replace

from codealmanac.cli.dispatch.config import requested_harness_model
from codealmanac.cli.dispatch.setup_wizard.models import SetupSelections
from codealmanac.cli.render.setup import SetupChoiceOption, SetupChoiceScreen
from codealmanac.services.config.model_catalog import (
    DEFAULT_HARNESS_MODELS,
    ModelSource,
    catalog_models,
    model_source,
)
from codealmanac.services.harnesses.models import (
    HarnessKind,
    HarnessModelListing,
    HarnessReadiness,
)
from codealmanac.services.setup.models import SetupTarget


def target_options() -> tuple[SetupChoiceOption, ...]:
    return (
        SetupChoiceOption(
            "Codex + Claude",
            (),
            ("b",),
        ),
        SetupChoiceOption(
            "Codex only",
            (),
            ("c",),
        ),
        SetupChoiceOption(
            "Claude only",
            (),
            ("l",),
        ),
    )


def maintenance_options() -> tuple[SetupChoiceOption, ...]:
    return (
        SetupChoiceOption(
            "Automatic",
            (
                "Sync learns from recent sessions",
                "Garden improves your wiki",
                "Both run locally in background",
            ),
        ),
        SetupChoiceOption("Manual", ("Run Sync or Garden yourself",)),
    )


def runner_options(
    readiness: tuple[HarnessReadiness, ...] = (),
) -> tuple[SetupChoiceOption, ...]:
    by_kind = {item.kind: item for item in readiness}
    return (
        runner_option(HarnessKind.CODEX, by_kind.get(HarnessKind.CODEX), ("c",)),
        runner_option(HarnessKind.CLAUDE, by_kind.get(HarnessKind.CLAUDE), ("l",)),
    )


def runner_option(
    kind: HarnessKind,
    readiness: HarnessReadiness | None,
    shortcuts: tuple[str, ...],
) -> SetupChoiceOption:
    label = RUNNER_LABELS[kind]
    if readiness is None:
        return SetupChoiceOption(label, ("checking status in setup",), shortcuts)
    if readiness.available:
        return SetupChoiceOption(
            label,
            ("ready", readiness.message),
            shortcuts,
        )
    details = ("not configured", readiness.repair or readiness.message)
    return SetupChoiceOption(label, details, shortcuts, disabled=True)


@dataclass(frozen=True)
class WizardModel:
    id: str
    option: SetupChoiceOption


def listing_for(
    harness: HarnessKind,
    listings: tuple[HarnessModelListing, ...],
) -> HarnessModelListing | None:
    """The account model listing for `harness`, when the runner could list."""

    for listing in listings:
        if listing.kind == harness and listing.listed:
            return listing
    return None


def wizard_models(
    harness: HarnessKind,
    current: str,
    listing: HarnessModelListing | None = None,
) -> tuple[WizardModel, ...]:
    """Catalog models for `harness`, plus the current model when it is custom.

    When the account listing serves at least one catalog model, catalog models
    it does not serve are disabled, except the current one so an explicit
    choice is never moved silently.
    """

    catalog = catalog_models(harness)
    filtering = listing is not None and any(listing.serves(m.id) for m in catalog)
    unserved_note = f"not served by your {harness.value} account"
    models: list[WizardModel] = []
    for model in catalog:
        unserved = listing is not None and not listing.serves(model.id)
        if not unserved:
            option = SetupChoiceOption(model.label, (model.detail,))
        elif filtering and model.id != current:
            option = SetupChoiceOption(model.label, (unserved_note,), disabled=True)
        else:
            option = SetupChoiceOption(model.label, (model.detail, unserved_note))
        models.append(WizardModel(model.id, option))
    if model_source(current, harness) is ModelSource.CUSTOM:
        details = [f"custom model id, passed to {harness.value} as entered"]
        if listing is not None and not listing.serves(current):
            details.append(f"not in your {harness.value} account's model list")
        models.append(WizardModel(current, SetupChoiceOption(current, tuple(details))))
    return tuple(models)


def model_options(
    harness: HarnessKind,
    current: str,
    listing: HarnessModelListing | None = None,
) -> tuple[SetupChoiceOption, ...]:
    return tuple(model.option for model in wizard_models(harness, current, listing))


def update_options() -> tuple[SetupChoiceOption, ...]:
    return (
        SetupChoiceOption(
            "Automatic",
            (
                "Keep CodeAlmanac updated",
                "Runs locally in background",
            ),
        ),
        SetupChoiceOption(
            "Manual",
            ("Run codealmanac update yourself",),
        ),
    )


def change_options() -> tuple[SetupChoiceOption, ...]:
    return (
        SetupChoiceOption("Commit changes", ()),
        SetupChoiceOption("Leave in worktree", ()),
    )


def telemetry_options() -> tuple[SetupChoiceOption, ...]:
    return (
        SetupChoiceOption(
            "Yes, help improve CodeAlmanac",
            (
                "Recommended",
                "Anonymous usage and crash reports",
                "Never code, prompts, or transcripts",
            ),
        ),
        SetupChoiceOption(
            "No thanks",
            (
                "Do not share usage or crashes",
                "You can change this later",
            ),
        ),
    )


def shortcut_option_index(screen: SetupChoiceScreen, key: str) -> int | None:
    normalized = key.casefold()
    for index, option in enumerate(screen.options):
        if option.disabled:
            continue
        if normalized in option.shortcuts:
            return index
    return None


def target_default_index(targets: tuple[SetupTarget, ...]) -> int:
    if targets == (SetupTarget.CODEX,):
        return 1
    if targets == (SetupTarget.CLAUDE,):
        return 2
    return 0


def targets_for_index(index: int) -> tuple[SetupTarget, ...]:
    if index == 1:
        return (SetupTarget.CODEX,)
    if index == 2:
        return (SetupTarget.CLAUDE,)
    return (SetupTarget.CODEX, SetupTarget.CLAUDE)


def runner_for_index(index: int) -> HarnessKind:
    if index == 1:
        return HarnessKind.CLAUDE
    return HarnessKind.CODEX


def runner_index(harness: HarnessKind) -> int:
    if harness == HarnessKind.CLAUDE:
        return 1
    return 0


def wizard_current_model(
    harness: HarnessKind,
    defaults: SetupSelections,
    requested: str | None,
    listing: HarnessModelListing | None = None,
) -> str:
    """Model to preselect for the runner chosen on the wizard's first screen.

    An explicit `--model` always wins. Otherwise a configured or default
    catalog model the account does not serve yields to the first catalog model
    it does serve, so the preselected choice is one that can run.
    """

    if requested is not None:
        return requested_harness_model(harness, requested)
    current = defaults.model if harness == defaults.harness else None
    current = current or DEFAULT_HARNESS_MODELS[harness]
    if (
        listing is None
        or listing.serves(current)
        or model_source(current, harness) is ModelSource.CUSTOM
    ):
        return current
    for model in catalog_models(harness):
        if listing.serves(model.id):
            return model.id
    return current


def requested_model_selections(
    selections: SetupSelections,
    requested: str | None,
) -> SetupSelections:
    """Apply an explicit `--model` to non-interactive setup selections."""

    if requested is None:
        return selections
    model = requested_harness_model(selections.harness, requested)
    return replace(selections, model=model)


def model_for_index(
    harness: HarnessKind,
    index: int,
    current: str,
    listing: HarnessModelListing | None = None,
) -> str:
    return wizard_models(harness, current, listing)[index].id


def model_index(
    harness: HarnessKind,
    current: str,
    listing: HarnessModelListing | None = None,
) -> int:
    ids = tuple(model.id for model in wizard_models(harness, current, listing))
    return ids.index(current)


def parse_setup_targets(value: str) -> tuple[SetupTarget, ...]:
    if value == "all":
        return (SetupTarget.CODEX, SetupTarget.CLAUDE)
    return (SetupTarget(value),)


RUNNER_LABELS = {
    HarnessKind.CODEX: "Codex",
    HarnessKind.CLAUDE: "Claude",
}
