Here's a concise README for the harvest script:

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
   ckan -c /srv/app/ckan.ini user token add ckan_admin harvest_script
   ```
   Copy the token that's displayed.

2. **DOI Registry**: Ensure your DOI list exists at:
   ```
   src/ckanext-zenodo/ckanext/zenodo/config/zenodo_dois.txt
   ```
   
   Format: One DOI per line, supports both formats:
   ```
   https://doi.org/10.5281/zenodo.12345
   https://zenodo.org/record/12345
   ```

## Usage

### From Host Machine

```bash
docker exec -it obis-ckan-211-ckan-dev-1 bash -c \
  "cd /srv/app/src_extensions/ckanext-zenodo/ckanext/zenodo/scripts && \
   CKAN_API_TOKEN='your-token-here' python3 harvest_zenodo.py"
```

### From Inside Container

```bash
# Enter container
docker exec -it obis-ckan-211-ckan-dev-1 bash

# Set token
export CKAN_API_TOKEN='your-token-here'

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
   - Creates new dataset in CKAN
   - Assigns to "OBIS Community" organization

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

**"API token required" error**: Ensure you're using `Bearer` format (script handles this automatically)

**"DOI registry not found"**: Check the file path matches the location above

**"Invalid API token"**: Regenerate token using the command in Prerequisites

**Import failures**: Check CKAN logs for detailed errors:
```bash
docker logs obis-ckan-211-ckan-dev-1 | tail -50
```
```