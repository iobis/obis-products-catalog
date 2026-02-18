# Extensions

!!! note "Stub"
    This page is a skeleton. Content will be filled in during documentation sprints.

The catalog uses five custom CKAN extensions:

## ckanext-obis_theme

Visual theming for the OBIS look and feel. Overrides CKAN templates for the homepage, header, footer, and dataset pages. Provides template helpers for product type and thematic area stats.

**Plugin name**: `obis_theme`

## ckanext-obis_sync

OBIS data synchronization CLI commands. Syncs OBIS nodes as organizations and institutions as groups (with Ocean Expert enrichment).

**Plugin name**: `obis_sync`

**Commands**:

- `ckan obis sync-nodes` — Sync OBIS nodes as CKAN organizations
- `ckan obis sync-institutions` — Sync institutions as CKAN groups

## ckanext-odis_export

ODIS Schema.org JSON-LD export. Adds a `/dataset/<id>/odis.jsonld` endpoint to every dataset, transforming CKAN metadata to ODIS-compliant Schema.org JSON-LD.

**Plugin name**: `odis_export`

This is the primary output of the catalog — making curated metadata discoverable by ODIS.

## ckanext-zenodo

Schema definition and Zenodo-specific facets/indexing. Defines the dataset schema via `zenodo_schema.yaml`, provides custom validators and Solr indexing, and adds Product Type and Thematic Area facets.

**Plugin name**: `zenodo`

## ckanext-doi-import

Import datasets from DOIs (currently Zenodo). Provides a web UI for DOI import and an API endpoint for automated harvesting. Uses a mapper pattern — adding new sources requires writing one mapper file.

**Plugin name**: `doi_import`
