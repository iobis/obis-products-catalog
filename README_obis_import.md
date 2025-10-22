# OBIS CKAN Synchronization Commands

## Overview
The `obis_theme` extension provides CLI commands to synchronize OBIS data into CKAN:
- **sync-nodes**: Imports OBIS nodes as CKAN organizations
- **sync-institutions**: Imports OBIS institutions as CKAN groups (enriched with Ocean Expert data)

## Prerequisites
- CKAN 2.11 running in Docker
- `obis_theme` extension installed and enabled
- Sysadmin access (ckan_admin user)

## Installation
The commands are built into the `obis_theme` plugin via the `IClick` interface in `plugin.py`.

## Usage

### 1. Access the CKAN container
```bash
docker-compose -f docker-compose.dev.yml exec ckan-dev bash
```

### 2. Sync OBIS Nodes (Organizations)
```bash
ckan -c /srv/app/ckan.ini obis sync-nodes
```
This will:
- Fetch all OBIS nodes from `https://api.obis.org/v3/node`
- Create new CKAN organizations for each node
- Update existing organizations if they already exist
- Store metadata: node ID, type, URL, coordinates, contacts, feeds

### 3. Sync OBIS Institutions (Groups)
```bash
# Sync all institutions
ckan -c /srv/app/ckan.ini obis sync-institutions

# Or test with a limited number first
ckan -c /srv/app/ckan.ini obis sync-institutions --limit 10
```
This will:
- Fetch OBIS institutions with Ocean Expert IDs from `https://api.obis.org/v3/institute`
- Enrich with Ocean Expert data from `https://oceanexpert.org/api/v1/institute/{id}.json`
- Create/update CKAN groups with full metadata
- Store: addresses, URLs, logos, institution types, etc.
- Rate limits API calls to avoid overwhelming Ocean Expert API

## Key Features

### Authentication
- Commands run with `ignore_auth=True` context (no token needed)
- Uses CKAN's internal action API (not HTTP endpoints)
- Runs as `ckan_admin` user automatically

### Conflict Resolution
- Both commands check if organizations/groups already exist
- Automatically updates existing records instead of failing
- Uses slugified names for URL-friendly identifiers

### Data Quality
- Validates and normalizes institution names
- Handles missing/null data gracefully
- Logs progress and errors clearly

## Troubleshooting

### Command not found
```bash
# Make sure obis_theme is in ckan.plugins
grep "ckan.plugins" /srv/app/ckan.ini

# Should include: obis_theme
```

### Import errors
```bash
# Restart CKAN after code changes
docker-compose -f docker-compose.dev.yml restart ckan-dev
```

### Database/Session errors
The commands use CKAN's CLI context which properly initializes database sessions. If you get session errors, the command isn't running within CKAN's context - make sure you're using `ckan -c /srv/app/ckan.ini obis <command>`.

## Architecture Notes

### Why CLI Commands vs Standalone Scripts?
- **Standalone HTTP scripts** faced authentication issues with CKAN 2.11's API token system
- **CLI commands** run within CKAN's app context with full database access
- No HTTP authentication needed - uses internal action functions
- Follows CKAN best practices for extensions

### Helper Function Naming
The extension uses `obis_` prefix for helper functions to avoid conflicts:
- `obis_get_product_type_stats()` 
- `obis_get_thematic_stats()`
- `obis_get_recent_datasets()`

This was necessary because the `zenodo` extension registered helpers with the same names.

## Output Examples

### Successful sync-nodes
```
Fetching OBIS nodes...
Processing 38 OBIS nodes...
✓ Created: OBIS Australia
✓ Created: OBIS Canada
↻ Updated: OBIS USA
...
==================================================
Created: 35, Updated: 3, Failed: 0
Total: 38
```

### Successful sync-institutions
```
Found 450 institutions with Ocean Expert IDs
[1/450] Processing: Woods Hole Oceanographic Institution
  ✓ Created: Woods Hole Oceanographic Institution
[2/450] Processing: Scripps Institution of Oceanography
  ↻ Updated: Scripps Institution of Oceanography
...
==================================================
Created: 320, Updated: 125, Failed: 5
Ocean Expert enriched: 445
Total: 450
```