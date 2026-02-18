# Data Model

!!! note "Stub"
    This page is a skeleton. Content will be filled in during documentation sprints.

## Current State

42 active datasets.

## Product Types

Controlled vocabulary defined in `zenodo_schema.yaml`:

dataset, publication, software, presentation, poster, image, video, lesson, physical_object, other

## Thematic Areas

Controlled vocabulary defined in `zenodo_schema.yaml`:

Biodiversity, Climate Change, Ocean Acidification, Marine Protected Areas, eDNA, Invasives, Fisheries, Pollution, Coastal Management, Deep Sea, Coral Reefs, Species Distribution

## Organizations

OBIS nodes synced from the OBIS API. Prefixed with `node-` to avoid namespace collisions with groups.

## Groups

Research institutions synced from the OBIS API and enriched with Ocean Expert data.

## Key Schema Fields

| Field | Purpose |
|---|---|
| `canonical_id` | DOI or persistent identifier (used as `@id` in ODIS export) |
| `resource_type` | Schema.org type (e.g., `Dataset`, `PresentationDigitalDocument`) |
| `authors` | JSON array of author objects |
| `contributors` | JSON array of contributor objects |
| `funding` | JSON array of funding objects |
| `product_type` | Multi-value from controlled vocabulary |
| `thematic_tags` | Multi-value from controlled vocabulary |
| `spatial_coverage_type` | Point or box |
| `spatial_point_latitude`, `spatial_point_longitude` | Point coordinates |
| `spatial_box` | Bounding box string |

## Data Pipeline

```
Source API (Zenodo, future: GBIF, Dryad, etc.)
    ↓ mapper (Python function: API response → standard dict)
    ↓
CKAN (storage, curation UI, search, user management)
    ↓ odis_export extension (CKAN dataset → Schema.org JSON-LD)
    ↓
ODIS (discovery, federated search)
```

Adding a new source requires writing one mapper file in `ckanext-doi-import/ckanext/doi_import/mappers/`.
