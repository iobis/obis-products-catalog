# OBIS Data Sync Scripts

These scripts synchronize data from OBIS and Ocean Expert APIs into CKAN.

## Prerequisites

- CKAN running and accessible
- CKAN API token with admin privileges

## Scripts

### 1. OBIS Nodes Sync (`obis_sync.py`)

Syncs OBIS nodes as CKAN organizations.

**Usage:**
```bash

# From your host machine
CKAN_TOKEN=your-token python3 src/ckanext-obis_theme/scripts/obis_sync.py

# Or from inside Docker
docker compose -f docker-compose.dev.yml exec ckan-dev bash
export CKAN_TOKEN=your-token
cd /srv/app/src_extensions/ckanext-obis_theme/scripts
python3 obis_sync.py
```

#### What it does:

Fetches all OBIS nodes from https://api.obis.org/v3/node
Creates or updates CKAN organizations for each node
Stores node metadata (URL, coordinates, contacts, etc.) as extras

#### Run frequency: Monthly or quarterly
2. OBIS Institutions Sync (obis_institute_sync.py)
Syncs OBIS institutions enriched with Ocean Expert data as CKAN groups.
Usage:
bash# From your host machine
CKAN_TOKEN=your-token python3 src/ckanext-obis_theme/scripts/obis_institute_sync.py

### Or from inside Docker

```bash
docker compose -f docker-compose.dev.yml exec ckan-dev bash
export CKAN_TOKEN=your-token
cd /srv/app/src_extensions/ckanext-obis_theme/scripts
python3 obis_institute_sync.py
```

#### What it does:

Fetches OBIS institutions that have Ocean Expert IDs
Enriches each with detailed data from Ocean Expert API
Creates or updates CKAN groups with full metadata
Includes logos, contact info, addresses, activities, etc.

#### Features:

Resumable on interruption (saves progress every 10 institutions)
Rate limiting to respect API quotas
Creates debug file (obis_institutions_debug.json)

Run frequency: Monthly or quarterly
Getting Your CKAN Token

Log into CKAN as admin
Go to your user profile
Click on "API Tokens" in the left sidebar
Create a new token or copy an existing one

### Notes

Both scripts can be safely re-run - they update existing records
Progress is saved for the institutions sync (can resume if interrupted)
Scripts run from localhost:5000 by default, adjust CKAN_BASE_URL in scripts if needed