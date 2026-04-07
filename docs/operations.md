# Operations

## Routine Commands

```bash
# Restart everything
docker compose down && docker compose up -d

# Rebuild after code changes
docker compose build ckan && docker compose up -d

# View logs
docker compose logs -f ckan

# Rebuild search index
docker compose exec ckan ckan -c /srv/app/ckan.ini search-index rebuild

# Database backup
docker compose exec db pg_dump -U ckandbuser ckandb -Fc > backup_$(date +%Y%m%d).dump

# Sync OBIS nodes
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-nodes

# Sync institutions
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-institutions

# Export catalog whitelist
docker compose exec ckan ckan -c /srv/app/ckan.ini zenodo export-whitelist

# Export whitelist to file
docker compose exec ckan ckan -c /srv/app/ckan.ini zenodo export-whitelist --output /srv/app/catalog_whitelist.csv

# Bulk harvest from DOI list
docker compose exec ckan ckan -c /srv/app/ckan.ini zenodo harvest
```

## User Management

### ORCID Whitelist

Access to the catalog is controlled by an ORCID whitelist. Only researchers whose ORCID iDs appear in the whitelist can log in via ORCID. Unapproved users see a message directing them to contact helpdesk@obis.org.

**Whitelist file location:** `src/ckanext-oauth2-login/orcid_whitelist.txt`

**Adding a new user:**

1. Edit the whitelist file and add their ORCID iD (one per line, comments after `#`):
   ```
   0000-0002-1234-5678  # Researcher Name
   ```
2. Rebuild and restart:
   ```bash
   docker compose build ckan && docker compose up -d
   ```

The next time the researcher clicks "Sign in with ORCID", their account will be created automatically and they'll be added to the OBIS Community organization as an editor.

**Removing a user:**

Remove their ORCID iD from the whitelist file, rebuild, and restart. They won't be able to log in again via ORCID. Their existing CKAN account will remain in the system but will be inactive.

To fully delete the account:

```bash
docker compose exec -it ckan ckan -c /srv/app/ckan.ini shell
```

Then in the shell:

```python
from ckan import model
user = model.User.by_name('orcid-XXXX-XXXX-XXXX-XXXX')
user.purge()
model.Session.commit()
```

!!! warning
    If you only set a user to `deleted` state (via the CKAN UI or `user remove` CLI) without removing them from the whitelist, they will be **automatically reactivated** the next time they log in via ORCID.

### Adding a user to an organization

Use the web UI at `/organization/<org-name>/members` or the API:

```bash
curl -X POST https://YOUR_HOST/api/3/action/organization_member_create \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"id": "obis-community", "username": "the_username", "role": "editor"}'
```

Roles: `member` (read-only), `editor` (create/edit), `admin` (full control including delete and member management).

### Creating a user manually

For non-ORCID accounts (e.g. service accounts):

```bash
docker compose exec ckan ckan -c /srv/app/ckan.ini user add USERNAME email=EMAIL password=PASSWORD
```

### Promoting a user to sysadmin

```bash
docker compose exec -it ckan ckan -c /srv/app/ckan.ini shell
```

Then in the shell:

```python
from ckan import model
user = model.User.by_name('orcid-XXXX-XXXX-XXXX-XXXX')
user.sysadmin = True
model.Session.commit()
```

## Catalog Manifest

The catalog maintains two CSV files at the repo root:

**`catalog_whitelist.csv`** — Every product in the catalog, exported nightly from the database. Columns: `doi`, `title`, `source_url`, `catalog_url`. This file is version-controlled in git, providing an audit trail of catalog changes over time.

**`catalog_blacklist.csv`** — DOIs that have been reviewed and determined to be out of scope. Manually curated. Columns: `doi`, `title`, `source_url`, `reason`, `reviewed_date`. The import system checks this file and blocks blacklisted DOIs from being imported.

### Nightly Export

A cron job runs at 2am UTC daily, exports the whitelist from the database, and commits to git if there are changes:
```bash
# Manual run
/root/bin/export-whitelist.sh

# Cron log
cat /var/log/whitelist-export.log
```

### Adding to the Blacklist

Edit `catalog_blacklist.csv` at the repo root and add a row:
```
https://doi.org/10.5281/zenodo.99999,Some Product Title,https://zenodo.org/record/99999,Not OBIS-derived,2026-02-19
```

The blacklist is checked by the web form, API endpoint, and bulk harvest CLI. No rebuild is required — the file is volume-mounted into the container.

## Gotchas

### Plugin load order matters

The `CKAN__PLUGINS` order in `.env` affects template priority. Plugins loaded **earlier** in the list have **higher** template priority. Current required ordering:

```
CKAN__PLUGINS="envvars image_view text_view public_edit oauth2_login scheming_datasets scheming_groups obis_theme obis_sync odis_export zenodo doi_import"
```

`public_edit` must come **before** `scheming_datasets` so its organization field override takes effect.

### `.env` is never committed

Each deployment maintains its own `.env` from `.env.example`. Database passwords appear in multiple env vars (standalone vars AND connection URL strings) — they must match.

## Git Workflow

All work happens on branches off `main`. Changes are committed on the droplet and pushed to GitHub. When stable, branches merge to `main`.

`.env` is never committed. Each deployment maintains its own `.env` from `.env.example`.