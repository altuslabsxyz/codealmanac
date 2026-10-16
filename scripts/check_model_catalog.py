"""Report drift between the recommended model catalog and what providers serve.

Codex ids come from the same Yoke harness adapter that ``codealmanac setup``
uses: it asks the signed-in Codex app-server for ``model/list`` without
starting a paid turn, so the answer is exactly the picker the local account
sees. Claude ids come from the Anthropic Models API when ``ANTHROPIC_API_KEY``
is set; Claude Code has no listing surface, so the API organization's list is
the closest stable source. That call is plain HTTP because CodeAlmanac never
talks to the Anthropic API itself and should not grow an SDK dependency for one
maintainer script.

Usage::

    uv run python scripts/check_model_catalog.py [--runtime-root DIR] [--json]

Exit status is 1 when a provider answered and a catalog model is missing from
its list. Models the provider serves but hides from its picker count as served
and are flagged separately. The script never edits source: catalog order,
labels, and defaults stay a maintainer decision in
``src/codealmanac/services/config/model_catalog.py``.
"""

import argparse
import os
import sys
from collections.abc import Iterable
from pathlib import Path

import httpx
from pydantic import BaseModel

from codealmanac.integrations.harnesses.yoke.adapter import YokeHarnessAdapter
from codealmanac.services.config.model_catalog import catalog_model_ids
from codealmanac.services.harnesses.kinds import HarnessKind
from codealmanac.settings import AppConfig, LocalStatePaths

ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"
ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_PAGE_SIZE = 100


class CatalogDrift(BaseModel):
    harness: HarnessKind
    stale: tuple[str, ...]
    hidden: tuple[str, ...]
    candidates: tuple[str, ...]


def catalog_drift(
    harness: HarnessKind,
    served: Iterable[str],
    hidden: Iterable[str] = (),
) -> CatalogDrift:
    """Compare the catalog with the ids a provider serves and hides."""

    served_ids = tuple(dict.fromkeys(served))
    hidden_ids = tuple(dict.fromkeys(hidden))
    catalog = catalog_model_ids(harness)
    return CatalogDrift(
        harness=harness,
        stale=tuple(
            model
            for model in catalog
            if model not in served_ids and model not in hidden_ids
        ),
        hidden=tuple(model for model in catalog if model in hidden_ids),
        candidates=tuple(model for model in served_ids if model not in catalog),
    )


class ProviderListing(BaseModel):
    harness: HarnessKind
    served: tuple[str, ...] = ()
    hidden: tuple[str, ...] = ()
    skipped: str | None = None

    def drift(self) -> CatalogDrift | None:
        if self.skipped is not None:
            return None
        return catalog_drift(self.harness, self.served, self.hidden)


class CatalogReport(BaseModel):
    listings: tuple[ProviderListing, ...]

    def stale(self) -> bool:
        return any(
            drift is not None and len(drift.stale) > 0
            for drift in (listing.drift() for listing in self.listings)
        )


class AnthropicModel(BaseModel):
    id: str


class AnthropicModelsPage(BaseModel):
    data: list[AnthropicModel] = []
    has_more: bool = False
    last_id: str | None = None


def codex_listing(runtime_root: Path) -> ProviderListing:
    listing = YokeHarnessAdapter(HarnessKind.CODEX, runtime_root).models()
    if not listing.listed:
        return ProviderListing(
            harness=HarnessKind.CODEX,
            skipped=(
                f"Codex did not list models: {listing.message}; sign in with `codex`"
            ),
        )
    return ProviderListing(
        harness=HarnessKind.CODEX,
        served=listing.served,
        hidden=listing.hidden,
    )


def claude_listing() -> ProviderListing:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ProviderListing(
            harness=HarnessKind.CLAUDE,
            skipped=(
                "ANTHROPIC_API_KEY is not set; Claude Code has no model listing "
                "surface, so the Anthropic Models API is the only source"
            ),
        )
    headers = {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION}
    params: dict[str, str | int] = {"limit": ANTHROPIC_PAGE_SIZE}
    served: list[str] = []
    try:
        with httpx.Client(timeout=30.0) as client:
            while True:
                response = client.get(
                    ANTHROPIC_MODELS_URL,
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                page = AnthropicModelsPage.model_validate(response.json())
                served.extend(model.id for model in page.data)
                if not page.has_more or page.last_id is None:
                    break
                params = {"limit": ANTHROPIC_PAGE_SIZE, "after_id": page.last_id}
    except httpx.HTTPError as error:
        return ProviderListing(
            harness=HarnessKind.CLAUDE,
            skipped=f"Anthropic Models API request failed: {type(error).__name__}",
        )
    return ProviderListing(harness=HarnessKind.CLAUDE, served=tuple(served))


def report_lines(report: CatalogReport) -> list[str]:
    lines: list[str] = []
    for listing in report.listings:
        drift = listing.drift()
        if drift is None:
            lines.append(f"{listing.harness.value}: skipped")
            lines.append(f"  {listing.skipped}")
            continue
        lines.append(
            f"{listing.harness.value}: {len(listing.served)} served, "
            f"{len(listing.hidden)} hidden"
        )
        for model in catalog_model_ids(listing.harness):
            if model in drift.stale:
                status = "stale"
            elif model in drift.hidden:
                status = "hidden"
            else:
                status = "served"
            lines.append(f"  catalog  {model:<24} {status}")
        for model in drift.candidates:
            lines.append(f"  served   {model:<24} candidate")
        for model in listing.hidden:
            if model not in drift.hidden:
                lines.append(f"  hidden   {model:<24} not in the picker")
    if report.stale():
        lines.append(
            "stale catalog ids: refresh "
            "src/codealmanac/services/config/model_catalog.py"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=LocalStatePaths.from_config(AppConfig()).harness_runtime_dir,
        help="Yoke runtime root for the Codex probe (default: CodeAlmanac state)",
    )
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)
    report = CatalogReport(
        listings=(codex_listing(args.runtime_root), claude_listing())
    )
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print("\n".join(report_lines(report)))
    return 1 if report.stale() else 0


if __name__ == "__main__":
    sys.exit(main())
