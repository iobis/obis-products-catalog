"""Zenodo mapper: fetches metadata from Zenodo API and maps to CKAN schema."""

import re
import json
import requests
import ckan.plugins.toolkit as toolkit


# Zenodo resource type → product_type mapping
RESOURCE_TYPE_MAP = {
    "dataset": "dataset",
    "software": "software",
    "presentation": "presentation",
    "poster": "poster",
    "video": "video",
    "lesson": "lesson",
    "physicalobject": "physical_object",
    "other": "other",
}


def fetch_metadata(doi):
    """Fetch and map metadata from Zenodo for a given DOI.

    Args:
        doi: A DOI string (e.g. '10.5281/zenodo.12345').

    Returns:
        A dict matching the CKAN schema, ready for package_create/update.

    Raises:
        toolkit.ValidationError on API or format errors.
    """
    record_id = _extract_record_id(doi)
    api_url = f"https://zenodo.org/api/records/{record_id}"

    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise toolkit.ValidationError(
            {"doi": f"Failed to fetch Zenodo metadata: {e}"}
        )

    data["record_id"] = record_id
    return _map_to_schema(data, doi)


def search_by_doi(doi):
    """Search Zenodo for a record matching a DOI.

    Used for non-Zenodo DOIs that might also be deposited on Zenodo.

    Returns:
        Mapped metadata dict if found, None otherwise.
    """
    try:
        url = f"https://zenodo.org/api/records?q=doi:{doi}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("hits", {}).get("total", 0) > 0:
            record = data["hits"]["hits"][0]
            record_id = record.get("id")
            return fetch_metadata(f"10.5281/zenodo.{record_id}")
    except Exception:
        pass

    return None


def get_last_modified(doi):
    """Get the last modified timestamp from Zenodo for a given DOI.

    Returns:
        ISO 8601 timestamp string, or None if unavailable.
    """
    try:
        record_id = _extract_record_id(doi)
        url = f"https://zenodo.org/api/records/{record_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('updated')
    except Exception:
        return None


def _extract_record_id(doi):
    """Extract the numeric Zenodo record ID from a DOI."""
    match = re.search(r"zenodo\.(\d+)", doi)
    if not match:
        raise toolkit.ValidationError({"doi": "Invalid Zenodo DOI format"})
    return match.group(1)


def _map_resource_type(zenodo_type):
    """Map Zenodo resource type string to product_type list.

    Zenodo types look like 'dataset', 'publication-article',
    'image-figure', 'software', etc.
    """
    if zenodo_type.startswith("publication"):
        return ["publication"]
    if zenodo_type.startswith("image"):
        return ["image"]

    normalized = zenodo_type.lower().replace("-", "").replace("_", "")
    for key, value in RESOURCE_TYPE_MAP.items():
        if normalized == key:
            return [value]

    return ["dataset"]


def _map_authors(creators):
    """Map Zenodo creators list to authors JSON string."""
    authors = []
    for creator in creators:
        affiliation = creator.get("affiliation", "")
        if isinstance(affiliation, list):
            affiliation = ", ".join(affiliation)

        authors.append({
            "author_name": creator.get("name", ""),
            "author_affiliation_name": str(affiliation) if affiliation else "",
        })
    return authors


def _map_resources(files, record_id):
    """Map Zenodo files to CKAN resource list."""
    resources = [
        {
            "name": "Zenodo Record",
            "url": f"https://zenodo.org/record/{record_id}",
            "format": "HTML",
            "description": "View this dataset on Zenodo",
        }
    ]

    for file_info in files:
        filename = file_info.get("key", file_info.get("filename", "Download"))
        resources.append({
            "name": filename,
            "url": f"https://zenodo.org/record/{record_id}/files/{file_info.get('key', '')}",
            "format": file_info.get("type", "").upper(),
            "description": f"Download from Zenodo. File size: {file_info.get('size', 0)} bytes",
        })

    return resources


def _map_to_schema(zenodo_data, doi):
    """Map full Zenodo API response to CKAN schema dict."""
    record_id = zenodo_data.get("record_id", "")
    metadata = zenodo_data.get("metadata", {})
    files = zenodo_data.get("files", [])

    # Determine resource/product type
    resource_type_data = metadata.get("resource_type", {})
    if isinstance(resource_type_data, dict):
        resource_type = resource_type_data.get("type", "dataset")
    elif isinstance(resource_type_data, str):
        resource_type = resource_type_data
    else:
        resource_type = "dataset"

    # DOI value (strip URL prefix if present)
    doi_value = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

    mapped = {
        "title": metadata.get("title", "Untitled Dataset"),
        "notes": metadata.get("description", ""),
        "url": f"https://zenodo.org/record/{record_id}",
        "source_url": f"https://zenodo.org/record/{record_id}",
        "canonical_id": f"https://doi.org/{doi_value}",
        "identifier": {
            "propertyID": "DOI",
            "value": doi_value,
            "url": f"https://doi.org/{doi_value}",
        },
        "version": metadata.get("version", "1.0"),
        "license_id": metadata.get("license", {}).get("id", "notspecified"),
        "tag_string": ",".join(metadata.get("keywords", [])),
        "product_type": _map_resource_type(resource_type),
        "update_frequency": "never",
        "resources": _map_resources(files, record_id),
        "extras": [
            {"key": "source", "value": "zenodo"},
        ],
    }

    # Authors
    creators = metadata.get("creators", [])
    if creators:
        mapped["authors"] = json.dumps(_map_authors(creators), ensure_ascii=False)

    # Publication date
    pub_date = metadata.get("publication_date", "")
    if pub_date:
        mapped["extras"].append({"key": "publication_date", "value": pub_date})

    return mapped