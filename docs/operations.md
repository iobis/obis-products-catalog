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

# Pre-create accounts and apply roles from whitelist
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-whitelist

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
   docker compose -f docker-compose.dev.yml exec ckan ckan -c /srv/app/ckan.ini obis sync-whitelist
   ```

## User Management

### ORCID Whitelist

Access to the catalog is controlled by an ORCID whitelist. Only researchers whose ORCID iDs appear in the whitelist can log in via ORCID. Unapproved users see a message directing them to contact helpdesk@obis.org.

**Whitelist file location:** `src/ckanext-oauth2-login/orcid_whitelist.txt`

**Whitelist format:**

```
# Format: <orcid> [role1|role2|...] # comment
#
# Roles are optional and pipe-delimited:
#   sysadmin        full system access
#   <org-name>      org admin for that org (e.g. node-obis-uk)
#
# No role = regular editor, added to obis-community on first login.
# Roles are re-applied on every login, including demotions.

0000-0001-7418-1244 sysadmin # Stephen Formel
0000-0002-5806-0837 node-obis-uk # Dan Lear
0000-0001-6775-530X # Dimitra Mavraki (editor, no special role)
```

A user can hold multiple org admin roles by pipe-separating them:
```
0000-0003-2807-5867 node-otn-obis|node-eurobis # Someone who admins two nodes
```

**Adding a new user:**

1. Edit the whitelist file and add their ORCID iD with optional role
2. Rebuild and restart:
   ```bash
   docker compose build ckan && docker compose up -d
   ```
3. Run sync-whitelist to pre-create their account immediately (optional — account is also created on first login):
   ```bash
   docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-whitelist
   ```

**Syncing the whitelist:**

The `sync-whitelist` command pre-creates accounts for all whitelisted users and applies roles. It is safe to re-run at any time — it skips existing accounts and only applies role changes.

```bash
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-whitelist
```

It fetches real names from the ORCID public API, so newly created accounts have correct names rather than placeholder values.

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

### Managing Organization Members

Organization member management is available to org admins and sysadmins at `/organization/manage_members/<org-name>`.

!!! note "CKAN 2.11 route change"
    In CKAN 2.11, the members management page moved from `/organization/members/<name>` to `/organization/manage_members/<name>`. The old URL is now a public read-only view.

The Add Member search box finds users by name or username. Users must have an existing account (created via `sync-whitelist` or first ORCID login) to appear in search results.

### Managing Institution Members

Institution (group) member management is open to any logged-in user at `/group/manage_members/<group-name>`. This allows researchers to associate themselves with their institutions without needing admin access.

### Adding a user to an organization via API

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

The preferred way is to add `sysadmin` as a role in the whitelist and run `sync-whitelist`. For emergency or one-off use, the shell approach still works:

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

## Featured Products

The homepage "Featured Products" section shows a curated selection of products. Sysadmins can manage this via the admin dashboard at `/ckan-admin/featured-products`.

Up to 8 products can be added to the pool. The homepage randomly displays 4 of them on each page load, providing variety without manual rotation. If no products are configured, the most recently updated products are shown as a fallback.

To add products, paste their URL slugs (one per line) into the admin form. Slugs are the last part of a product's URL, e.g. `10-5281-zenodo-11464531` from `/dataset/10-5281-zenodo-11464531`.

!!! note
    Featured products are stored in the database, not in the codebase. After deploying to a new environment (e.g. prod after testing on dev), you will need to configure the featured pool again at `/ckan-admin/featured-products`.

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