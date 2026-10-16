from codealmanac.core.errors import ExecutionFailed
from codealmanac.services.harnesses.models import (
    HarnessModelListing,
    HarnessReadiness,
)
from codealmanac.services.setup.ports import RunnerReadinessProbe
from codealmanac.services.setup.requests import RunSetupRequest


def runner_readiness(
    probe: RunnerReadinessProbe | None,
    request: RunSetupRequest,
) -> HarnessReadiness | None:
    if probe is None:
        return None
    return probe.readiness(request.harness)


def require_runner(
    probe: RunnerReadinessProbe | None,
    request: RunSetupRequest,
) -> HarnessReadiness | None:
    readiness = runner_readiness(probe, request)
    if readiness is None or readiness.available:
        return readiness
    message = f"{request.harness.value} is not configured: {readiness.message}"
    if readiness.repair is not None:
        message = f"{message}. {readiness.repair}"
    raise ExecutionFailed(message)


def runner_models(
    probe: RunnerReadinessProbe | None,
    request: RunSetupRequest,
) -> HarnessModelListing | None:
    if probe is None:
        return None
    return probe.models(request.harness)
