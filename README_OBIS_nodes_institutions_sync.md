# OBIS Data Synchronization Guide

This guide explains how to synchronize OBIS nodes and institutions into your CKAN instance.

## Overview

The OBIS CKAN extension provides two sync commands:

1. **`sync-nodes`** - Syncs OBIS nodes as CKAN **organizations**
2. **`sync-institutions`** - Syncs OBIS institutions as CKAN **groups** (enriched with Ocean Expert data)

## Prerequisites

- CKAN instance running in Docker
- `ckanext-obis_theme` plugin installed and enabled
- Network access to:
  - `https://api.obis.org/v3/node`
  - `https://api.obis.org/v3/institute`
  - `https://oceanexpert.org/api/v1/institute/`

## Important Concepts

### Organizations vs Groups

- **Organizations** (`type='organization'`) - OBIS nodes that own/publish datasets
  - Named with `node-` prefix (e.g., `node-obis-usa`, `node-ocean-tracking-network`)
  - Display titles without prefix (e.g., "OBIS USA", "Ocean Tracking Network")
  
- **Groups** (`type='group'`) - OBIS institutions for categorization/tagging
  - No prefix in names (e.g., `ocean-tracking-network`, `vlaamse-instituut`)
  - Enriched with Ocean Expert metadata when available

### Data Quality Levels

When syncing institutions, each group is tagged with a data quality indicator:

- `ocean_expert_full` - Complete Ocean Expert data retrieved
- `ocean_expert_partial` - Partial Ocean Expert data available
- `obis_only` - Only OBIS data available (Ocean Expert unavailable or timeout)

## Command Reference

### Sync OBIS Nodes

```bash
docker exec <container-name> ckan -c /srv/app/ckan.ini obis sync-nodes
```

**What it does:**
- Fetches all OBIS nodes from `https://api.obis.org/v3/node`
- Creates or updates organizations in CKAN
- Adds `node-` prefix to organization names to avoid conflicts with groups
- Commits all changes in a single transaction

**Example output:**
```
Fetching OBIS nodes...
Processing 38 OBIS nodes...
✓ Will create: OBIS USA (as node-obis-usa)
✓ Will create: OBIS UK (as node-obis-uk)
↻ Will update: Ocean Tracking Network
...
Committing all changes...
Commit complete

==================================================
Created: 35, Updated: 3
Total: 38

✓ 40 organizations in database after commit
```

### Sync OBIS Institutions

```bash
# Sync all institutions
docker exec <container-name> ckan -c /srv/app/ckan.ini obis sync-institutions

# Test with a limited number (recommended for first run)
docker exec <container-name> ckan -c /srv/app/ckan.ini obis sync-institutions --limit 10
```

**What it does:**
- Fetches all OBIS institutions with Ocean Expert IDs from `https://api.obis.org/v3/institute`
- For each institution:
  1. Fetches detailed data from Ocean Expert API
  2. Creates or updates group in CKAN
  3. Stores comprehensive metadata as group extras
- Rate-limited to 1 Ocean Expert request per second
- Commits all changes in a single transaction

**Options:**
- `--limit N` - Only process first N institutions (useful for testing)

**Example output:**
```
Starting OBIS institutions synchronization with Ocean Expert...
============================================================
Fetching OBIS institutions...
Found 668 institutions with Ocean Expert IDs
Limited to 10 institutions

Processing 10 institutions...
[1/10] Processing: CSIRO National Collections (OE ID: 20942)
  ✓ Retrieved Ocean Expert data
  ✓ Will create: CSIRO National Collections
  Data quality: ocean_expert_full
...

Committing all changes...
Commit complete

============================================================
Synchronization complete!
Created: 10
Updated: 0
Failed: 0
Ocean Expert enriched: 9
Total processed: 10
Success rate: 100.0%

✓ 10 groups in database after commit
```

## Metadata Stored

### OBIS Nodes (Organizations)

- Name (with `node-` prefix)
- Title (OBIS node name)
- Description

### OBIS Institutions (Groups)

**Core fields:**
- Name (slugified institution name)
- Title (full institution name)
- Description (institution address from Ocean Expert)
- Image URL (institution logo from Ocean Expert)

**Extras (when Ocean Expert data available):**
- `ocean_expert_id` - Ocean Expert institution ID
- `obis_institution_code` - OBIS institution code
- `data_source` - Always "obis_oceanexpert"
- `data_quality` - Quality level (ocean_expert_full/partial/obis_only)
- `sync_date` - Date of last sync
- `website` - Institution website URL
- `email` - Contact email
- `phone` - Contact phone
- `fax` - Contact fax
- `country` - Country name
- `country_code` - ISO country code
- `region` - Geographic region
- `acronym` - Institution acronym
- `institution_type` - Type of institution
- `ocean_expert_edmo_code` - EDMO code
- `activities` - Institution activities description
- `ocean_expert_updated` - Last update date from Ocean Expert

## Usage Workflow

### Initial Setup

1. **Test with limited data:**
   ```bash
   # Test with 10 nodes
   docker exec obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini obis sync-nodes
   
   # Test with 10 institutions
   docker exec obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini obis sync-institutions --limit 10
   ```

2. **Verify in UI:**
   - Navigate to `/organization` to see OBIS nodes
   - Navigate to `/group` to see institutions

3. **Run full sync:**
   ```bash
   # Sync all nodes
   docker exec obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini obis sync-nodes
   
   # Sync all institutions (takes ~11 minutes for 668 institutions with rate limiting)
   docker exec obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini obis sync-institutions
   ```

### Regular Updates

Run periodically to keep data synchronized:

```bash
# Update nodes (quick - ~38 nodes)
docker exec obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini obis sync-nodes

# Update institutions (slower - ~668 institutions, ~11 minutes)
docker exec obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini obis sync-institutions
```

## Troubleshooting

### Only Some Organizations/Groups Visible

**Problem:** Database shows 40 organizations but UI/API shows only 10.

**Cause:** The `is_organization` flag was not set correctly during creation.

**Solution:** 
```bash
# Fix organizations
docker exec obis-ckan-211-db-1 psql -U ckandbuser -d ckandb -c "
UPDATE public.group 
SET is_organization = true 
WHERE type = 'organization' AND is_organization = false;"

# Groups should have is_organization = false (this is correct)
```

### Ocean Expert Timeout Errors

**Problem:** Some institutions fail to fetch Ocean Expert data due to timeouts.

**Cause:** Ocean Expert API may be slow or temporarily unavailable.

**Behavior:** Script continues and creates the group with `obis_only` data quality. This is expected and graceful.

**Note:** These institutions can be updated later by re-running the sync.

### Duplicate Key Errors

**Problem:** Error like `duplicate key value violates unique constraint "group_name_key"`

**Cause:** An organization and group with the same name cannot coexist.

**Solution:** The `node-` prefix on organizations prevents this. If you see this error, ensure:
1. Your plugin has the latest code with `node-` prefix
2. You've restarted CKAN after updating the plugin

### Transaction Rollback Issues

**Problem:** Script says "Created: X" but database shows fewer records.

**Cause:** Using CKAN action functions (`group_create`) instead of direct SQLAlchemy.

**Solution:** The current plugin uses direct SQLAlchemy model operations which commit properly. If you see this, ensure you're using the latest plugin version.

## Performance Notes

- **sync-nodes**: Fast (~5-10 seconds for 38 nodes)
- **sync-institutions**: 
  - ~668 institutions with Ocean Expert IDs
  - ~1 second per institution (rate limiting for Ocean Expert API)
  - Total time: ~11 minutes for full sync
  - Use `--limit` for faster testing

## API Verification

Check sync results via API:

```bash
# Count organizations
docker exec obis-ckan-211-ckan-dev-1 wget -qO- "http://localhost:5000/api/3/action/organization_list" | python3 -c "import json, sys; data=json.load(sys.stdin); print(f'{len(data[\"result\"])} organizations')"

# Count groups
docker exec obis-ckan-211-ckan-dev-1 wget -qO- "http://localhost:5000/api/3/action/group_list" | python3 -c "import json, sys; data=json.load(sys.stdin); print(f'{len(data[\"result\"])} groups')"

# View organization details
docker exec obis-ckan-211-ckan-dev-1 wget -qO- "http://localhost:5000/api/3/action/organization_show?id=node-obis-usa" | python3 -m json.tool

# View group details with extras
docker exec obis-ckan-211-ckan-dev-1 wget -qO- "http://localhost:5000/api/3/action/group_show?id=ocean-tracking-network&include_extras=true" | python3 -m json.tool
```

## Database Verification

Check directly in PostgreSQL:

```bash
# Count organizations
docker exec obis-ckan-211-db-1 psql -U ckandbuser -d ckandb -c "
SELECT COUNT(*) FROM public.group WHERE type = 'organization' AND state = 'active';"

# Count groups
docker exec obis-ckan-211-db-1 psql -U ckandbuser -d ckandb -c "
SELECT COUNT(*) FROM public.group WHERE type = 'group' AND state = 'active';"

# View organizations
docker exec obis-ckan-211-db-1 psql -U ckandbuser -d ckandb -c "
SELECT name, title, is_organization FROM public.group 
WHERE type = 'organization' ORDER BY name LIMIT 10;"

# View groups with data quality
docker exec obis-ckan-211-db-1 psql -U ckandbuser -d ckandb -c "
SELECT g.name, g.title, ge.value as data_quality 
FROM public.group g
LEFT JOIN group_extra ge ON g.id = ge.group_id AND ge.key = 'data_quality'
WHERE g.type = 'group' 
ORDER BY g.name LIMIT 10;"
```

## Maintenance

### Cleaning Up Before Re-sync

If you need to start fresh:

```bash
# Delete all organizations except test/obis-community
docker exec obis-ckan-211-db-1 psql -U ckandbuser -d ckandb -c "
DELETE FROM group_extra WHERE group_id IN (
    SELECT id FROM public.group WHERE type = 'organization' 
    AND name NOT IN ('obis-community', 'test')
);
DELETE FROM member WHERE group_id IN (
    SELECT id FROM public.group WHERE type = 'organization' 
    AND name NOT IN ('obis-community', 'test')
);
DELETE FROM public.group WHERE type = 'organization' 
    AND name NOT IN ('obis-community', 'test');"

# Delete all groups
docker exec obis-ckan-211-db-1 psql -U ckandbuser -d ckandb -c "
DELETE FROM group_extra WHERE group_id IN (SELECT id FROM public.group WHERE type = 'group');
DELETE FROM member WHERE group_id IN (SELECT id FROM public.group WHERE type = 'group');
DELETE FROM public.group WHERE type = 'group';"
```

## Support

For issues or questions:
1. Check this README's Troubleshooting section
2. Verify your plugin code matches the latest version
3. Check CKAN logs: `docker logs obis-ckan-211-ckan-dev-1`
4. Verify external APIs are accessible: 
   - https://api.obis.org/v3/node
   - https://api.obis.org/v3/institute
   - https://oceanexpert.org/api/v1/institute/

---

**Last Updated:** October 22, 2025
**Plugin Version:** ckanext-obis_theme with direct SQLAlchemy sync commands