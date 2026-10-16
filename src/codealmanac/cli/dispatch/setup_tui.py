import argparse

from codealmanac.cli.dispatch.config import resolve_harness_model
from codealmanac.cli.dispatch.setup_wizard.choices import choose_setup_option
from codealmanac.cli.dispatch.setup_wizard.models import (
    SetupCancelled,
    SetupSelections,
)
from codealmanac.cli.dispatch.setup_wizard.options import (
    change_options,
    listing_for,
    maintenance_options,
    model_for_index,
    model_index,
    model_options,
    parse_setup_targets,
    requested_model_selections,
    runner_for_index,
    runner_index,
    runner_options,
    target_default_index,
    target_options,
    targets_for_index,
    telemetry_options,
    update_options,
    wizard_current_model,
)
from codealmanac.cli.dispatch.setup_wizard.terminal import (
    supports_interactive_setup,
    wizard_terminal,
)
from codealmanac.cli.render.setup import (
    SetupChoiceScreen,
    background_item_selection_notices,
)
from codealmanac.services.config.models import UserConfig
from codealmanac.services.harnesses.models import (
    HarnessKind,
    HarnessModelListing,
    HarnessReadiness,
)


def resolve_setup_selections(
    args: argparse.Namespace,
    user_config: UserConfig,
    runner_status: tuple[HarnessReadiness, ...] = (),
    model_listings: tuple[HarnessModelListing, ...] = (),
) -> SetupSelections:
    defaults = default_setup_selections(args, user_config)
    if args.yes or args.json or not supports_interactive_setup():
        return requested_model_selections(defaults, args.model)
    return interactive_setup_selections(
        defaults,
        runner_status,
        include_telemetry=not args.no_telemetry,
        requested_model=args.model,
        model_listings=model_listings,
    )


def default_setup_selections(
    args: argparse.Namespace,
    user_config: UserConfig,
) -> SetupSelections:
    """Selections from config and every flag except `--model`, which is applied
    against the runner that ends up selected."""

    harness = (
        user_config.harness.default if args.runner is None else HarnessKind(args.runner)
    )
    model = resolve_harness_model(harness, user_config)
    return SetupSelections(
        targets=parse_setup_targets(args.target),
        harness=harness,
        model=model,
        auto_update=user_config.automation.update.enabled and not args.no_auto_update,
        auto_commit=user_config.auto_commit and not args.no_auto_commit,
        telemetry_enabled=user_config.telemetry.enabled and not args.no_telemetry,
        sync_off=args.sync_off or not user_config.automation.sync.enabled,
        garden_off=args.garden_off or not user_config.automation.garden.enabled,
    )


def interactive_setup_selections(
    defaults: SetupSelections,
    runner_status: tuple[HarnessReadiness, ...],
    *,
    include_telemetry: bool,
    requested_model: str | None = None,
    model_listings: tuple[HarnessModelListing, ...] = (),
) -> SetupSelections:
    try:
        with wizard_terminal():
            return wizard_selections(
                defaults,
                runner_status,
                include_telemetry=include_telemetry,
                requested_model=requested_model,
                model_listings=model_listings,
            )
    except KeyboardInterrupt as error:
        raise SetupCancelled() from error


def wizard_selections(
    defaults: SetupSelections,
    runner_status: tuple[HarnessReadiness, ...],
    *,
    include_telemetry: bool,
    requested_model: str | None = None,
    model_listings: tuple[HarnessModelListing, ...] = (),
) -> SetupSelections:
    total_steps = 7 if include_telemetry else 6
    runner_index_value = choose_setup_option(
        SetupChoiceScreen(
            step=1,
            title="AI runner",
            question="Which agent should run CodeAlmanac jobs?",
            options=runner_options(runner_status),
            total_steps=total_steps,
        ),
        initial_index=runner_index(defaults.harness),
    )
    harness = runner_for_index(runner_index_value)
    listing = listing_for(harness, model_listings)
    current_model = wizard_current_model(harness, defaults, requested_model, listing)
    model_index_value = choose_setup_option(
        SetupChoiceScreen(
            step=2,
            title="Runner model",
            question=f"Which {harness.value} model should maintain your wiki?",
            options=model_options(harness, current_model, listing),
            visual="list",
            total_steps=total_steps,
        ),
        initial_index=model_index(harness, current_model, listing),
    )
    target_index = choose_setup_option(
        SetupChoiceScreen(
            step=3,
            title="Agent instructions",
            question="Add CodeAlmanac instructions to your AGENTS.md / CLAUDE.md:",
            options=target_options(),
            total_steps=total_steps,
        ),
        initial_index=target_default_index(defaults.targets),
    )
    maintenance_index = choose_setup_option(
        SetupChoiceScreen(
            step=4,
            title="Wiki maintenance",
            question="How should your wikis be updated?",
            options=maintenance_options(),
            total_steps=total_steps,
        ),
        initial_index=1 if defaults.sync_off and defaults.garden_off else 0,
    )
    update_index = choose_setup_option(
        SetupChoiceScreen(
            step=5,
            title="Product updates",
            question="Keep CodeAlmanac up to date automatically?",
            options=update_options(),
            total_steps=total_steps,
            selection_notices=background_item_selection_notices(
                automatic_maintenance=maintenance_index == 0
            ),
        ),
        initial_index=0 if defaults.auto_update else 1,
    )
    change_index = choose_setup_option(
        SetupChoiceScreen(
            step=6,
            title="Agent change handling",
            question="Should agents commit wiki changes or leave them in the worktree?",
            options=change_options(),
            visual="change-handling",
            total_steps=total_steps,
        ),
        initial_index=0 if defaults.auto_commit else 1,
    )
    telemetry_enabled = defaults.telemetry_enabled
    if include_telemetry:
        telemetry_index = choose_setup_option(
            SetupChoiceScreen(
                step=7,
                title="Help improve CodeAlmanac",
                question=(
                    "Share anonymous usage so we can focus on what matters and fix "
                    "broken experiences faster."
                ),
                options=telemetry_options(),
                total_steps=total_steps,
            ),
            initial_index=0 if defaults.telemetry_enabled else 1,
        )
        telemetry_enabled = telemetry_index == 0
    return SetupSelections(
        targets=targets_for_index(target_index),
        harness=harness,
        model=model_for_index(harness, model_index_value, current_model, listing),
        auto_update=update_index == 0,
        auto_commit=change_index == 0,
        telemetry_enabled=telemetry_enabled,
        sync_off=maintenance_index == 1,
        garden_off=maintenance_index == 1,
    )
