# Contributing

!!! note "Stub"
    This page is a skeleton. Content will be filled in during documentation sprints.

## Development Setup

Development is done on a dedicated Digital Ocean droplet (not locally — local Docker setup on Mac has known issues with permissions).

## Git Workflow

1. Create a branch off `prod-setup`
2. Make changes, test on the dev droplet
3. Commit and push
4. Merge to `prod-setup` when stable
5. `prod-setup` merges to `main` after thorough testing

## Rebuilding After Code Changes

```bash
docker compose build ckan && docker compose up -d
```

## Adding a New Data Source

To add a new source (e.g., GBIF, Dryad):

1. Create a new mapper file in `src/ckanext-doi-import/ckanext/doi_import/mappers/` (e.g., `gbif.py`)
2. Implement a `fetch_metadata(doi)` function that returns a dict matching the CKAN schema
3. Add detection logic in `mappers/base.py` → `detect_source()`
4. The mapper is plain Python — testable without running CKAN
