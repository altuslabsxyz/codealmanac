# Model Catalog Refresh And Explicit Model Override Plan

## Goal

Make the current Codex and Claude generations selectable, let an explicitly
entered model id run even when the catalog does not list it, and give
maintainers a tested way to see when the catalog drifts from what providers
actually serve.

## Why Now

- Codex retired every model in the shipped catalog for ChatGPT sign-in:
  GPT-5.4 and GPT-5.4-mini on 2026-08-31, GPT-5.3-Codex-Spark on 2026-09-14,
  and GPT-5.5 on 2026-10-14. The shipped default `gpt-5.5` now fails on a
  current Codex. A local probe of codex-cli 0.152.1 through Yoke app-server
  `model/list` returned only `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`.
- Claude Code's current generation is Opus 5.5, Sonnet 5.5, Haiku 5.5, and
  Fable 5.1 (Claude Code model configuration docs). The catalog still lists
  Sonnet 5, Opus 4.7, and Haiku 4.5.
- A closed allowlist turns every provider release into a blocking CodeAlmanac
  release. The decision page already named that cost; it is now paid.

## Decision

The catalog changes role from allowlist to recommended list.

- Catalog ids are still validated against their harness: a Claude catalog id
  under `harness.default = "codex"` is rejected, and vice versa.
- Any other single-token model id is accepted and passed to the harness as
  entered. Both providers validate on first request (Claude Code documents
  that `--model` is not validated up front; Codex app-server rejects unknown
  models when the thread starts), so a typo surfaces as a failed run in
  `jobs`, not as silent fallback.
- `config set`, setup output, and `--json` say whether a model is `catalog`
  or `custom`, so the typo safety net moves from a hard error to a visible
  notice.
- Lifecycle telemetry exports the literal `custom` for non-catalog ids instead
  of dropping the event. User-entered text still never leaves the machine.

## Scope

1. `services/config/model_catalog.py`: one table per harness (`id`, `label`,
   `detail`), derived defaults, `validate_harness_model`, and `model_source`.
   Labels and details move here from the setup wizard so a refresh edits one
   tuple per harness.
2. `HarnessConfig`, `parse_harness_model`, and `RunSetupRequest` share the one
   validator.
3. `--model <id>` on `init`, `ingest`, `garden`, and `sync` for one run, and on
   `setup` to write config. Resolution order: flag, then config when the
   harness matches `harness.default`, then that harness's catalog default. In
   the wizard the flag is validated against the runner chosen on the first
   screen, so `setup --model claude-opus-5-5` works when the user picks Claude
   there and fails with the catalog message when they stay on Codex.
4. Setup wizard: a current custom model appears as a preselected extra option
   instead of being silently reset to the first catalog entry.
5. Telemetry: `telemetry_model_value` maps non-catalog ids to `custom`.
6. `scripts/check_model_catalog.py`: Codex ids come from Yoke discovery
   (account-scoped app-server `model/list`, no paid turn); Claude ids come
   from the Anthropic Models API when `ANTHROPIC_API_KEY` is set, because
   Claude Code has no listing surface. The script reports stale catalog ids
   and served candidates and exits non-zero on stale ids. Ids a provider
   serves but hides from its picker count as served and are flagged
   separately. Drift logic lives in the script, not the wheel, and is tested
   through `tests/test_check_model_catalog.py`. The script never rewrites
   source: labels, order, and defaults are product judgment.
7. Docs: README configuration section, CHANGELOG, live agreement.
8. Account-aware setup. The harness port gains `models()`, which returns a
   typed `HarnessModelListing` (served ids, hidden ids, or why the surface
   could not list). The Yoke adapter answers through app-server `model/list`
   for Codex and reports "not implemented" for Claude. Setup uses the listing
   to annotate, never to define, the catalog: the wizard disables catalog
   models the signed-in account does not serve and preselects the first one it
   does, and `setup --yes` prints a warning step with the served ids and the
   `config set` command when the chosen model is not in the account's list.
   The listing never changes which ids the catalog contains or which ids a
   user may type. The harness contract facade `services/harnesses/models.py`
   re-exports the new type, so its size guard in `tests/test_architecture.py`
   moves from 50 to 60 lines; the facade still holds no classes, functions, or
   validators.

## Out Of Scope

- A `doctor` warning when `harness.model` is not served by the account. Setup
  covers the moment the choice is made; a doctor check is a natural second
  consumer of `HarnessModelListing`.
- A provider-default model value that lets Codex or Claude pick.
- Wiki pages `decisions/controlled-model-catalog` and `reference/config-keys`
  describe the retired allowlist. They belong to a Garden pass.

## Catalog (2026-10-16)

| Harness | Models (first is default) |
| --- | --- |
| `codex` | `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-luna`, `gpt-5.6-sol` |
| `claude` | `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-haiku-5-5`, `claude-fable-5-1` |

Sources: OpenAI models documentation (GPT-6.1 Sol recommended on paid plans,
GPT-6 Luna on Free and Go, GPT-6 Astra for the hardest work, GPT-5.6 served
during the rollout) and the Claude Code model configuration page (5.5
generation ids, Fable 5.1 availability by plan).

## Files

- Add: `src/codealmanac/services/config/model_catalog.py`
- Modify: `src/codealmanac/services/config/models.py`
- Modify: `src/codealmanac/services/config/service.py`
- Modify: `src/codealmanac/services/setup/requests.py`
- Modify: `src/codealmanac/services/setup/models.py`
- Modify: `src/codealmanac/services/setup/planning.py`
- Modify: `src/codealmanac/services/telemetry/models.py`
- Modify: `src/codealmanac/services/telemetry/service.py`
- Modify: `src/codealmanac/cli/parser/run_commands.py`
- Modify: `src/codealmanac/cli/parser/setup.py`
- Modify: `src/codealmanac/cli/dispatch/config.py`
- Modify: `src/codealmanac/cli/dispatch/build.py`
- Modify: `src/codealmanac/cli/dispatch/operations.py`
- Modify: `src/codealmanac/cli/dispatch/sync.py`
- Modify: `src/codealmanac/cli/dispatch/setup_tui.py`
- Modify: `src/codealmanac/cli/dispatch/setup_wizard/options.py`
- Modify: `src/codealmanac/cli/render/config.py`
- Modify: `src/codealmanac/cli/render/setup/result.py`
- Modify: `src/codealmanac/cli/syntax/catalog.py`
- Add: `src/codealmanac/cli/dispatch/setup_wizard/choices.py` (keyboard
  choice loop moved out of `setup_tui.py` to keep dispatch files small)
- Modify: `src/codealmanac/services/harnesses/results.py`, `ports.py`,
  `service.py`, `models.py`
- Modify: `src/codealmanac/integrations/harnesses/yoke/adapter.py`
- Modify: `src/codealmanac/services/setup/ports.py`, `runners.py`,
  `service.py`
- Modify: `src/codealmanac/cli/dispatch/setup.py`
- Add: `scripts/check_model_catalog.py`
- Add: `tests/test_check_model_catalog.py`
- Rename: `tests/test_controlled_model_config.py` to
  `tests/test_harness_model_config.py`
- Modify: `tests/test_cli.py`, `tests/test_config_service.py`,
  `tests/test_run_telemetry.py`, `tests/test_telemetry_service.py`, and other
  tests that spell the old default model.
- Modify: `README.md`, `CHANGELOG.md`, `docs/python-port-live-agreement.md`

## Test Coverage

- Catalog table: defaults are first entries, ids are unique across harnesses,
  every entry has a label and detail.
- Config: catalog id of the other harness rejected (model and service paths);
  custom id accepted and reported as `custom`; blank or spaced ids rejected;
  `harness.default` switch resets the model to that harness's default.
- CLI: `--model` lands in the queued run spec; `--using claude --model
  <codex catalog id>` fails before queueing; `config set harness.model
  <custom>` prints the custom notice; `setup --yes --model` writes the custom
  id; interactive setup keeps a custom configured model preselected, drops it
  when the runner is switched, follows `--model` to the chosen runner, and
  rejects a `--model` that conflicts with the chosen runner.
- Telemetry: non-catalog ids export `custom` with no private text; the event
  boundary rejects raw custom text and catalog ids of another harness and
  accepts the `custom` marker.
- Drift: the script's `catalog_drift` reports stale, hidden, and candidate ids
  and the report exits non-zero only on stale ids.
- Account listing: the Yoke adapter projects served and hidden ids and turns
  unsupported listing into `listed = false`; the harness service explains a
  missing adapter; the wizard disables unserved catalog models and preselects
  the first served one; `setup --yes` warns with the served ids and stays
  quiet when the chosen model is served.

## Verified On This Machine (2026-10-16)

- Claude Code 2.1.299 answered a one-turn prompt on every Claude catalog id:
  `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-haiku-5-5`,
  `claude-fable-5-1`.
- codex-cli 0.152.1 listed only `gpt-5.6-sol`, `gpt-5.6-terra`, and
  `gpt-5.6-luna` through Yoke app-server `model/list`, so the GPT-6 entries
  showed as stale and the drift script exited 1. After `codex update` to
  0.163.0 the same account lists `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-luna`,
  `gpt-6-sol`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, and `gpt-5.5`;
  every Codex catalog id is served and the script exits 0. The account-aware
  setup exists for exactly the older-client case: it disables unserved catalog
  entries and preselects a served one instead of failing at the first run.

## Verification

```bash
uv run pytest
uv run ruff check .
uv run python scripts/check_model_catalog.py
```
