"""Shared utilities for DOI import mappers."""

import re


def extract_doi_from_url(url):
    """Extract DOI from various URL formats.

    Handles:
        - Raw DOIs: 10.5281/zenodo.12345
        - doi.org URLs: https://doi.org/10.5281/zenodo.12345
        - Zenodo record URLs: https://zenodo.org/record/12345
        - Zenodo DOI URLs: https://zenodo.org/doi/10.5281/zenodo.12345

    Returns the DOI string or None if not recognized.
    """
    url = url.strip()

    if url.startswith("10."):
        return url

    patterns = [
        r"doi\.org/(.+)$",
        r"zenodo\.org/record/(\d+)",
        r"zenodo\.org/doi/(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            if "record" in pattern:
                return f"10.5281/zenodo.{match.group(1)}"
            return match.group(1)

    return None


def detect_source(doi):
    """Determine which source a DOI belongs to.

    Returns a string identifier: 'zenodo' or 'unknown'.
    Future sources (GBIF, Dryad, etc.) would be added here.
    """
    if "zenodo" in doi.lower() or doi.startswith("10.5281/zenodo"):
        return "zenodo"
    return "unknown"
