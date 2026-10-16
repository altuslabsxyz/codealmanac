# Changelog

## 0.5.0 - 2026-10-16

### Changed

- The runner model catalog lists the current generations: `gpt-6.1-sol`
  (default), `gpt-6-astra`, `gpt-6-luna`, and `gpt-5.6-sol` for Codex, and
  `claude-sonnet-5-5` (default), `claude-opus-5-5`, `claude-haiku-5-5`, and
  `claude-fable-5-1` for Claude. Codex retired every previously listed model
  for ChatGPT sign-in between 2026-08-31 and 2026-10-14.
- `harness.model` accepts any single-token model id. Catalog ids must match
  the selected runner; any other id is passed to the runner as entered and
  reported as a custom model by `config set` and `setup`.
- Lifecycle telemetry exports non-catalog models as the literal `custom`
  instead of dropping the event.
- Existing configs that still name a retired id such as `gpt-5.5` keep loading
  as a custom model; the run fails at the provider until `harness.model` is
  updated. `scripts/check_model_catalog.py` shows which ids an account serves.

### Added

- `--model <id>` on `init`, `ingest`, `garden`, `sync`, and `setup`.
- Setup checks which models the signed-in runner account serves (Codex
  app-server `model/list`; Claude has no listing surface). The wizard greys
  out catalog models the account does not serve and preselects one it does;
  `setup --yes` prints a warning with the served ids when the chosen model is
  not in the list.
- `scripts/check_model_catalog.py` reports drift between the catalog and the
  models the signed-in Codex account and the Anthropic Models API serve.
- The Altus fork installs from Git with
  `uv tool install git+https://github.com/altuslabsxyz/codealmanac`; README
  and RELEASE.md describe the install and release flow.

## 0.4.0 - 2026-07-10

### Changed

- Configuration now lives only at `~/.codealmanac/config.toml`.
  Repository-level `almanac/config.toml` is no longer read.
- Sync, Garden, and Update enabled states and intervals are user config keys.
  `codealmanac config set` applies automation changes immediately, while
  `codealmanac config apply` applies direct TOML edits.
- `codealmanac automation install` and `automation uninstall` were removed.
  Use `config set automation.<task>.*`; `automation status` remains available.
