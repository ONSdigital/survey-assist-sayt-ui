"""Report failed user-visible assets from browser tests."""

import warnings

from playwright.sync_api import Page, Request, Response

ASSET_TYPES = frozenset({"stylesheet", "script", "image"})


class AssetLoadWarning(UserWarning):
    """Report an asset load failure."""


class AssetMonitor:
    """Collect failed CSS, JavaScript, and image requests for one page."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.failures: list[str] = []
        self.failed_assets: set[tuple[str, str]] = set()

    def on_response(self, response: Response) -> None:
        """Capture HTTP errors for monitored assets."""
        request = response.request
        if request.resource_type in ASSET_TYPES and response.status >= 400:
            self._record_failure(
                request,
                f"returned HTTP {response.status}",
            )

    def on_request_failed(self, request: Request) -> None:
        """Capture network errors for monitored assets with no response."""
        if request.resource_type in ASSET_TYPES:
            self._record_failure(request, f"failed: {request.failure}")

    def warn_if_failed(self) -> None:
        """Emit failures after the test to preserve its result."""
        if self.failures:
            warnings.warn(
                "Asset load failures:\n" + "\n".join(self.failures),
                AssetLoadWarning,
                stacklevel=2,
            )

    def _record_failure(self, request: Request, reason: str) -> None:
        """Record each failed asset once."""
        asset = (request.resource_type, request.url)
        if asset in self.failed_assets:
            return
        self.failed_assets.add(asset)
        self.failures.append(f"{self.page.url}: {asset[0]} {asset[1]} {reason}")
