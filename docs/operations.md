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

## Dev Instance

The dev instance runs on the same droplet as production at `https://dev.products.obis.org:8443`. It shares the host but uses separate Docker containers, databases, and SSL certificates.

### Directory Layout

| Path | Purpose |
|---|---|
| `/opt/obis-products-catalog` | Production stack |
| `/opt/dev-obis-products-catalog` | Dev stack |

The `dev-` prefix on the folder name is intentional — it prevents accidentally running commands against the wrong stack.

### Dev-Specific Files

These files exist only in the dev directory and are excluded from git via `.gitignore`:

| File | Purpose |
|---|---|
| `.env` | Dev environment config (different ports, DB names, URLs) |
| `docker-compose.dev.yml` | Dev compose file (different ports, cert paths) |
| `nginx/Dockerfile.dev` | Nginx Dockerfile pointing to dev nginx config |
| `nginx/setup/default.dev.conf` | Nginx config for `dev.products.obis.org` |

### Key Differences from Prod

| Setting | Production | Dev |
|---|---|---|
| URL | `https://products.obis.org` | `https://dev.products.obis.org:8443` |
| HTTPS port | 443 | 8443 |
| HTTP port | 80 | 8080 |
| Databases | `ckandb`, `datastore` | `ckandb_dev`, `datastore_dev` |
| Compose project name | `obis-products-catalog` (directory default) | `ckan-dev` (set via `COMPOSE_PROJECT_NAME`) |
| SSL cert | `/etc/letsencrypt/live/products.obis.org/` | `/etc/letsencrypt/live/dev.products.obis.org/` |

### Running Dev Commands

Always pass `-f docker-compose.dev.yml` when working with the dev stack:

```bash
cd /opt/dev-obis-products-catalog

# Start dev
docker compose -f docker-compose.dev.yml up -d

# Rebuild and restart dev
docker compose -f docker-compose.dev.yml up -d --build

# View dev logs
docker compose -f docker-compose.dev.yml logs -f ckan

# Run a CKAN command on dev
docker compose -f docker-compose.dev.yml exec ckan ckan -c /srv/app/ckan.ini obis sync-nodes
```

### Setting Up a Fresh Dev Instance

If you need to rebuild dev from scratch:

1. Clone the repo:
   ```bash
   git clone https://github.com/iobis/obis-products-catalog.git /opt/dev-obis-products-catalog
   ```

2. Copy and edit the env file:
   ```bash
   cp /opt/obis-products-catalog/.env /opt/dev-obis-products-catalog/.env
   ```
   Update these values in `.env`:
   - `CKAN_SITE_URL=https://dev.products.obis.org:8443`
   - `CKANEXT__OAUTH2_LOGIN__REDIRECT_URI=https://dev.products.obis.org:8443/oauth2/callback`
   - `POSTGRES_DB=postgres_dev`, `CKAN_DB=ckandb_dev`, `DATASTORE_DB=datastore_dev`
   - Update all three DB connection URL strings to use the `_dev` database names
   - `NGINX_PORT_HOST=8080`, `NGINX_SSLPORT_HOST=8443`
   - `COMPOSE_PROJECT_NAME=ckan-dev`
   - Regenerate all secrets (session secret, API token secrets) — do not reuse prod values

3. Recreate the dev-specific files (not in git — see above table). Use the versions in the existing dev directory as reference, or recreate them:
   ```bash
   # nginx config
   cp nginx/setup/default.conf nginx/setup/default.dev.conf
   sed -i 's/products\.obis\.org/dev.products.obis.org/g' nginx/setup/default.dev.conf

   # nginx Dockerfile
   cp nginx/Dockerfile nginx/Dockerfile.dev
   sed -i 's/default\.conf/default.dev.conf/g' nginx/Dockerfile.dev

   # compose file
   cp docker-compose.yml docker-compose.dev.yml
   sed -i 's/0\.0\.0\.0:80:80/0.0.0.0:8080:80/' docker-compose.dev.yml
   sed -i 's/0\.0\.0\.0:${NGINX_SSLPORT_HOST}:${NGINX_SSLPORT}/0.0.0.0:8443:443/' docker-compose.dev.yml
   sed -i 's/dockerfile: Dockerfile/dockerfile: Dockerfile.dev/' docker-compose.dev.yml
   sed -i 's|/etc/letsencrypt/live/products.obis.org|/etc/letsencrypt/live/dev.products.obis.org|g' docker-compose.dev.yml
   sed -i 's|/etc/letsencrypt/archive/products.obis.org|/etc/letsencrypt/archive/dev.products.obis.org|g' docker-compose.dev.yml
   ```

4. Obtain the SSL cert (briefly stop prod nginx to free port 80):
   ```bash
   docker compose -f /opt/obis-products-catalog/docker-compose.yml stop nginx
   certbot certonly --standalone -d dev.products.obis.org
   docker compose -f /opt/obis-products-catalog/docker-compose.yml start nginx
   ```

5. Register the dev redirect URI with ORCID: add `https://dev.products.obis.org:8443/oauth2/callback` to the allowed redirect URIs in your ORCID developer app settings.

6. Build and start:
   ```bash
   docker compose -f docker-compose.dev.yml up -d --build
   docker compose -f docker-compose.dev.yml exec ckan ckan -c /srv/app/ckan.ini obis sync-nodes
   docker compose -f docker-compose.dev.yml exec ckan ckan -c /srv/app/ckan.ini obis sync-institutions
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

### Dev-specific files are not in git

The dev stack depends on four files that are gitignored and must be recreated if the dev directory is cloned fresh. See the "Setting Up a Fresh Dev Instance" section above for the commands to regenerate them.

## Git Workflow

All work happens on branches off `main`. Changes are committed on the droplet and pushed to GitHub. When stable, branches merge to `main`.

`.env` is never committed. Each deployment maintains its own `.env` from `.env.example`.