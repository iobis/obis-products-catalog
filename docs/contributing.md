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

To add a new source (e.g., GBIF, Dryad):

1. Create a new mapper file in `src/ckanext-doi-import/ckanext/doi_import/mappers/` (e.g., `gbif.py`)
2. Implement a `fetch_metadata(doi)` function that returns a dict matching the CKAN schema
3. Add detection logic in `mappers/base.py` → `detect_source()`
4. The mapper is plain Python — testable without running CKAN