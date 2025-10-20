Here's the updated README with the complete solution:

```markdown
# Zenodo DOI Harvest Script

Automated script to import and update datasets from Zenodo DOIs into CKAN.

## Location

```
src/ckanext-zenodo/ckanext/zenodo/scripts/harvest_zenodo.py
```

## Prerequisites

1. **API Token**: Generate a CKAN API token for the `ckan_admin` user:
   ```bash
   docker exec -it obis-ckan-211-ckan-dev-1 bash
   ckan -c /srv/app/ckan.ini user token list ckan_admin
   ```
   Copy the **token ID** (not the JWT) - it looks like: `Tnq0p8Lyx-oFgUxtRM8J3C__KtTxwWOfp8SPBtYx96s`

2. **DOI Registry**: Ensure your DOI list exists at:
   ```
   src/ckanext-zenodo/ckanext/zenodo/config/zenodo_dois.txt
   ```
   
   Format: One DOI per line, supports both formats:
   ```
   https://doi.org/10.5281/zenodo.12345
   https://zenodo.org/record/12345
   ```

3. **Scheming Configuration**: Add to `.env` file:
   ```bash
   CKAN__SCHEMING__DATASET_SCHEMAS=ckanext.zenodo:zenodo_schema.yaml
   ```
   
   Then restart CKAN:
   ```bash
   docker-compose -f docker-compose.dev.yml restart ckan-dev
   ```

## Usage

### From Host Machine

```bash
docker exec -it obis-ckan-211-ckan-dev-1 bash -c \
  "cd /srv/app/src_extensions/ckanext-zenodo/ckanext/zenodo/scripts && \
   CKAN_API_TOKEN='your-token-id-here' python3 harvest_zenodo.py"
```

### From Inside Container

```bash
# Enter container
docker exec -it obis-ckan-211-ckan-dev-1 bash

# Set token (use the token ID, not JWT)
export CKAN_API_TOKEN='Tnq0p8Lyx-oFgUxtRM8J3C__KtTxwWOfp8SPBtYx96s'

# Navigate to script
cd /srv/app/src_extensions/ckanext-zenodo/ckanext/zenodo/scripts

# Run harvest
python3 harvest_zenodo.py
```

## Modes

### Normal Mode (Default)
Only updates datasets if Zenodo's modification date is newer than CKAN's:
```bash
python3 harvest_zenodo.py
```

### Force Update Mode
Updates all existing datasets regardless of modification date:
```bash
python3 harvest_zenodo.py --force
```

## What It Does

1. **Checks each DOI** in the registry file
2. **Searches CKAN** for existing datasets with that DOI
3. **For existing datasets**: 
   - Compares modification dates
   - Updates if Zenodo is newer (or if `--force` flag used)
4. **For new datasets**: 
   - Fetches metadata from Zenodo
   - Maps to CKAN schema (including product_type)
   - Creates new dataset in CKAN
   - Assigns to "OBIS Community" organization

## Metadata Mapping

The script maps Zenodo metadata to CKAN fields:
- **Resource Type** → **Product Type** (dataset, publication, software, presentation, poster, image, video, lesson, physical_object, other)
- **Creators** → **Authors** (as JSON)
- **Title, Description, License, Keywords** → Standard CKAN fields
- **Files** → Resources (as links to Zenodo)

## Output

```
=== Zenodo DOI Harvest ===

Found 43 DOIs to process

[1/43] Processing: https://doi.org/10.5281/zenodo.12345
  ✓ Found in CKAN: Dataset Title
    → Force updating...
    ✓ Updated: Dataset Title

[2/43] Processing: https://doi.org/10.5281/zenodo.67890
  → Not in CKAN, importing...
    ✓ Imported: New Dataset Title

==================================================
Summary:
  Total DOIs processed: 43
  Already in CKAN: 30
  Newly imported: 10
  Updated: 30
  Failed: 3
==================================================
```

## Troubleshooting

**"API token required" error**: Make sure you're using the token ID (from `user token list`), not a JWT token

**"Invalid API token"**: 
- Verify token exists: `ckan -c /srv/app/ckan.ini user token list ckan_admin`
- Use the value in `[brackets]`, e.g., `[Tnq0p8Lyx...]`

**"DOI registry not found"**: Check the file exists at `src/ckanext-zenodo/ckanext/zenodo/config/zenodo_dois.txt`

**Product Type not displaying**: 
1. Verify scheming config: `docker exec -it obis-ckan-211-ckan-dev-1 python3 -c "from ckan.plugins import toolkit; print(toolkit.config.get('scheming.dataset_schemas'))"`
2. Should show: `ckanext.zenodo:zenodo_schema.yaml`
3. If `None`, add to `.env` and restart (see Prerequisites #3)

**Import failures**: Check CKAN logs for detailed errors:
```bash
docker logs obis-ckan-211-ckan-dev-1 | tail -50
```

## Configuration Files

- **Schema**: `src/ckanext-zenodo/ckanext/zenodo/zenodo_schema.yaml`
- **Plugin**: `src/ckanext-zenodo/ckanext/zenodo/plugin.py`
- **DOI List**: `src/ckanext-zenodo/ckanext/zenodo/config/zenodo_dois.txt`
- **Harvest Script**: `src/ckanext-zenodo/ckanext/zenodo/scripts/harvest_zenodo.py`
```