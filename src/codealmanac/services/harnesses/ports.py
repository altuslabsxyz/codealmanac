from collections.abc import Callable
from typing import Protocol

from codealmanac.services.harnesses.models import (
    HarnessEvent,
    HarnessKind,
    HarnessModelListing,
    HarnessReadiness,
    HarnessRunResult,
)
from codealmanac.services.harnesses.requests import RunHarnessRequest

HarnessEventSink = Callable[[HarnessEvent], None]


class HarnessAdapter(Protocol):
    kind: HarnessKind

    def check(self) -> HarnessReadiness:
        """Return local readiness without starting an agent run."""

    def models(self) -> HarnessModelListing:
        """List model ids the signed-in account serves, without starting a run."""

    def run(
        self,
        request: RunHarnessRequest,
        on_event: HarnessEventSink | None = None,
    ) -> HarnessRunResult:
        """Run one normalized agent task."""
