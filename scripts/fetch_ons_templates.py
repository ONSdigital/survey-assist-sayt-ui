#!/usr/bin/env python3
"""Fetch ONS Design System templates into the Flask package templates folder."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
import zipfile

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / ".design-system-version"
TARGET_DIR = ROOT / "src" / "ons_flask_auth_template" / "templates"
GITHUB_API_BASE = "https://api.github.com/repos/ONSdigital/design-system/releases"


def main() -> int:
    """Download and install ONS Design System templates.

    Returns:
        int: Zero when templates are installed successfully, otherwise one.
    """
    version = (
        VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "latest"
    )
    release_url = (
        f"{GITHUB_API_BASE}/latest" if version == "latest" else f"{GITHUB_API_BASE}/tags/{version}"
    )
    logger.info("Resolving ONS Design System release: %s", version)

    with urllib.request.urlopen(release_url, timeout=30) as response:
        release = json.loads(response.read().decode("utf-8"))

    asset_url = _find_templates_asset_url(release)
    if not asset_url:
        logger.error("No templates zip asset found on release %s", release.get("tag_name", version))
        return 1

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / "ons-design-system-templates.zip"
        logger.info("Downloading %s", asset_url)
        urllib.request.urlretrieve(asset_url, zip_path)  # noqa: S310 - controlled GitHub rel URL

        extract_dir = Path(tmp_dir) / "extract"
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)

        _copy_template_dir(extract_dir, "components")
        _copy_template_dir(extract_dir, "layout")

    logger.info("ONS Design System templates installed in %s", TARGET_DIR)
    return 0


def _find_templates_asset_url(release: dict[str, object]) -> str | None:
    """Find the zip asset URL for templates in a release payload.

    Args:
        release: Parsed GitHub release metadata.

    Returns:
        str | None: The download URL for a matching template archive, if found.
    """
    assets = release.get("assets", [])
    if not isinstance(assets, list):
        return None
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name", "")).lower()
        if "template" in name and name.endswith(".zip"):
            return str(asset.get("browser_download_url"))
    return None


def _copy_template_dir(extract_dir: Path, directory_name: str) -> None:
    """Copy a template directory from extracted archive contents.

    Args:
        extract_dir: Path containing extracted archive files.
        directory_name: Name of the directory to locate and copy.

    Raises:
        FileNotFoundError: If the named directory cannot be found in the archive.
    """
    matches = [path for path in extract_dir.rglob(directory_name) if path.is_dir()]
    if not matches:
        raise FileNotFoundError(f"Could not find {directory_name!r} in downloaded templates zip")

    source = matches[0]
    destination = TARGET_DIR / directory_name
    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(source, destination)
    logger.info("Copied %s", directory_name)


if __name__ == "__main__":
    sys.exit(main())
