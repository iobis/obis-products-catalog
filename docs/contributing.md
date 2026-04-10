# Contributing

## Development Setup

Development is done on a dedicated Digital Ocean droplet. Local Docker setup on Mac is not currently viable due to known permission issues with the container entrypoint scripts.

## Git Workflow

1. Create a branch off `main`
2. Make changes and test on the dev droplet
3. Commit and push
4. Open a pull request or merge directly to `main` when stable

## Rebuilding After Code Changes

```bash
docker compose build ckan && docker compose up -d
```

For nginx/docs changes only:

```bash
docker compose build nginx && docker compose up -d nginx
```

## Adding a New Data Source

Each data source (Zenodo, GBIF, Dryad, etc.) has its own mapper package under `src/ckanext-doi-import/ckanext/doi_import/mappers/`. The mapper is responsible for fetching metadata from the source API and mapping it to the CKAN schema. It is plain Python and testable without running CKAN.

### Mapper structure

Each source gets its own subdirectory:

```
mappers/
  base.py              ← DOI detection and shared utilities
  zenodo/
    __init__.py        ← fetch_metadata(), get_last_modified(), internal helpers
  gbif/                ← example future source
    __init__.py
```

### Required interface

Every mapper package must implement two functions in its `__init__.py`:

**`fetch_metadata(doi)`** — fetches metadata from the source API and returns a dict matching the CKAN schema. This is called by both the web import form and the harvest CLI.

```python
def fetch_metadata(doi):
    """Fetch and map metadata from the source for a given DOI.

    Args:
        doi: A DOI string (e.g. '10.XXXX/source.12345').

    Returns:
        A dict matching the CKAN schema, ready for package_create/update.

    Raises:
        toolkit.ValidationError on API or format errors.
    """
    ...
```

The returned dict should include at minimum: `title`, `notes`, `source_url`, `canonical_id`, `license_id`, `product_type`, `authors`, `resources`.

**`get_last_modified(doi)`** — returns the last modified timestamp from the source API as an ISO 8601 string, or `None` if unavailable. Used by the harvest CLI to skip records that haven't changed.

```python
def get_last_modified(doi):
    """Get the last modified timestamp from the source for a given DOI.

    Returns:
        ISO 8601 timestamp string, or None if unavailable.
    """
    ...
```

### Step-by-step

1. Create the mapper directory and file:
   ```bash
   mkdir src/ckanext-doi-import/ckanext/doi_import/mappers/mysource
   touch src/ckanext-doi-import/ckanext/doi_import/mappers/mysource/__init__.py
   ```

2. Implement `fetch_metadata(doi)` and `get_last_modified(doi)` in `__init__.py`. Use `mappers/zenodo/__init__.py` as a reference.

3. Register the source in `mappers/base.py` by adding detection logic to `detect_source()`:
   ```python
   def detect_source(doi):
       if "zenodo" in doi.lower() or doi.startswith("10.5281/zenodo"):
           return "zenodo"
       if "mysource" in doi.lower() or doi.startswith("10.XXXX"):
           return "mysource"
       return "unknown"
   ```

4. Wire the mapper into `doi_import/plugin.py` in the `doi_fetch_metadata` action function:
   ```python
   from ckanext.doi_import.mappers import mysource as mysource_mapper

   if source == "mysource":
       return mysource_mapper.fetch_metadata(doi)
   ```

5. Add any new license strings from the source to the `LICENSE_FAMILY_MAP` in `ckanext-obis_schema` (see issue #13).

### Testing the mapper

Because the mapper is plain Python, you can test it directly without running CKAN:

```python
from ckanext.doi_import.mappers.mysource import fetch_metadata
result = fetch_metadata("10.XXXX/mysource.12345")
print(result)
```