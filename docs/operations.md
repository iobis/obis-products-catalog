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

## Dev Auto-Deploy

Pushes to the `dev` branch automatically deploy to `https://dev.products.obis.org:8443`. No SSH, no manual rebuild — push and wait.

### How It Works

1. You push a commit to `origin/dev`
2. GitHub sends a webhook to `https://dev.products.obis.org:8443/webhook/deploy-dev`
3. nginx proxies the request to a small daemon (`webhook`) running on the droplet
4. The daemon verifies the request really came from GitHub (HMAC signature check), and that the push was to `refs/heads/dev`
5. If both checks pass, it runs `/home/deploy/bin/deploy-dev.sh`, which pulls the new commit, rebuilds the ckan image, restarts the stack, and waits for it to be healthy
6. The script reports back to GitHub as a commit status — green check on success, red X on failure

Total time: ~30 seconds for a cached build, 2-3 minutes for a real one.

### Monitoring

Each commit on the dev branch gets a status next to it on GitHub. Click the status icon to see what happened.

| Where | What |
|---|---|
| `https://github.com/iobis/obis-products-catalog/commits/dev` | Status badges on every commit |
| GitHub webhook page → Recent Deliveries | Per-delivery request/response logs |
| `/var/log/deploy-dev.log` on the droplet | Full deploy output |
| `sudo journalctl -u webhook` | Webhook daemon logs |

A failed status check on your own push generates a GitHub email by default. That's the failure ping.

### Security

The webhook URL is publicly reachable, but every request must carry a valid HMAC-SHA256 signature computed with a shared secret. Without the secret, requests are rejected with HTTP 500. The daemon itself binds to the docker bridge IP (`172.17.0.1:9000`), not the public internet — only nginx (which lives on the same bridge) can reach it. The deploy script runs as a non-root `deploy` user with Docker group access, not as root. The systemd unit hardens this further with `ProtectSystem=strict`, restricting filesystem writes to a small allowlist.

The deploy script does `git reset --hard origin/dev` — anything edited directly in `/opt/dev-obis-products-catalog` will be wiped on the next deploy. Edit locally, push through GitHub.

### Disabling Temporarily

```bash
sudo systemctl stop webhook
```

GitHub will retry deliveries a few times, then mark them failed. Re-enable with `sudo systemctl start webhook`.

### Running a Deploy Manually

If you need to bypass GitHub (e.g. the webhook isn't firing and you want to test):

```bash
sudo -u deploy /home/deploy/bin/deploy-dev.sh
```

### Moving Parts

| What | Where | Notes |
|---|---|---|
| Deploy script | `/home/deploy/bin/deploy-dev.sh` | Runs as `deploy` user |
| Systemd unit | `/etc/systemd/system/webhook.service` | `sudo systemctl status webhook` |
| Webhook daemon config | `/etc/webhook/hooks.json` | Contains the HMAC secret |
| GitHub PAT | `/etc/webhook/github-token` | For posting commit statuses; owned by `deploy`, mode 600 |
| nginx route | `/opt/dev-obis-products-catalog/nginx/setup/default.dev.conf` | `location /webhook/` block |
| Deploy log | `/var/log/deploy-dev.log` | Owned by `deploy`, no rotation configured |

### Rotating the GitHub PAT

The PAT expires (currently set to 1 year). When it does, commit statuses stop posting — deploys continue working, you just stop seeing green/red checks on GitHub.

To rotate:

1. Generate a new fine-grained PAT at https://github.com/settings/personal-access-tokens
   - Resource owner: **iobis**
   - Repository access: **Only select repositories** → `obis-products-catalog`
   - Repository permissions: **Commit statuses: Read and write**
2. Replace the file on the droplet:
   ```bash
   sudo install -m 600 -o deploy -g deploy /dev/stdin /etc/webhook/github-token
   ```
   Paste the new token, then Ctrl-D. No restart needed — the script re-reads the file on each deploy.
3. Delete the old PAT on GitHub.

### Rotating the Webhook Secret

If the secret leaks (committed to git, posted in a screenshot, etc.):

1. Generate a new secret: `openssl rand -hex 32`
2. Replace it in `/etc/webhook/hooks.json` (the `"secret":` value)
3. Restart the daemon: `sudo systemctl restart webhook`
4. Update the secret in the GitHub webhook settings to match

---

That's it. Want me to also add a one-line mention in the "Dev Instance" intro section pointing readers at this new section? Something like "Deploys happen automatically on push to dev — see [Dev Auto-Deploy](#dev-auto-deploy) below."

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
| URL | `https://products.obis.org` | `https://dev.products.obis.org` |
| HTTPS port | 443 (via host nginx) | 443 (via host nginx, shared with prod) |
| HTTP port (Docker, internal only) | 127.0.0.1:8080 | 127.0.0.1:8081 |
| Databases | `ckandb`, `datastore` | `ckandb_dev`, `datastore_dev` |
| Compose project name | `obis-products-catalog` (directory default) | `ckan-dev` (set via `COMPOSE_PROJECT_NAME`) |
| SSL cert | `/etc/letsencrypt/live/products.obis.org/` | `/etc/letsencrypt/live/dev.products.obis.org/` |

!!! note "SSL architecture changed (commit 012e3f8)"
    TLS termination moved from each stack's own Docker nginx container to a single host-level nginx in front of both prod and dev. Docker nginx in each stack now binds only to a localhost port and serves plain HTTP. Dev's URL no longer needs an explicit `:8443` port. The "stop prod nginx to grab dev's cert" workaround described in "Setting Up a Fresh Dev Instance" below is now **obsolete** — cert renewal is fully automated at the host level via `certbot.timer`, independently for both domains, confirmed via a successful `certbot renew --dry-run` for both. That section should be revised or removed; a fresh dev cert can now be obtained the same way, via the host-level `certbot --nginx -d dev.products.obis.org` (no need to stop prod nginx to free port 80).

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
   - `CKAN_SITE_URL=https://dev.products.obis.org` (no port needed — see note below)
   - `CKANEXT__OAUTH2_LOGIN__REDIRECT_URI=https://dev.products.obis.org/oauth2/callback`
   - `POSTGRES_DB=postgres_dev`, `CKAN_DB=ckandb_dev`, `DATASTORE_DB=datastore_dev`
   - Update all three DB connection URL strings to use the `_dev` database names
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
   sed -i 's/dockerfile: Dockerfile/dockerfile: Dockerfile.dev/' docker-compose.dev.yml
```

   !!! note "Docker nginx is HTTP-only, host nginx handles SSL"
       Since the host-level nginx refactor (commit 012e3f8), Docker's nginx container no longer terminates TLS or binds to a public port. In `docker-compose.dev.yml`, the `ckan-nginx` (or equivalent) service should bind only to a localhost port, e.g.:
```yaml
       ports:
         - "127.0.0.1:8081:80"
```
       matching prod's pattern of `127.0.0.1:8080:80`. Do not carry over the old `0.0.0.0:80:80` / `${NGINX_SSLPORT_HOST}` port mappings or the Let's Encrypt volume mounts — those belong to the pre-refactor, per-stack-SSL setup and are no longer used.

4. Add a `server_name dev.products.obis.org` block to the **host-level** nginx config (not the Docker one) so it routes to dev's Docker stack on its localhost port:
```bash
   sudo nano /etc/nginx/sites-available/dev.products.obis.org
```
   Reference the existing `products.obis.org` host-nginx config as a template, adjusting `server_name` and the `proxy_pass`/`upstream` target to point at dev's localhost port (e.g. `127.0.0.1:8081`). Enable it and reload:
```bash
   sudo ln -s /etc/nginx/sites-available/dev.products.obis.org /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
```

5. Obtain the SSL cert for the new dev domain using certbot's nginx plugin, directly at the host level — no need to stop prod, since host nginx serves both domains independently on the same port 443:
```bash
   sudo certbot --nginx -d dev.products.obis.org
```
   This both obtains the certificate and configures the host nginx config's SSL block automatically. Renewal is then handled automatically by `certbot.timer` (already running twice daily for all certs on the host) — no further action needed.

6. Register the dev redirect URI with ORCID: add `https://dev.products.obis.org/oauth2/callback` to the allowed redirect URIs in the ORCID developer app settings. This app is registered under Stephen Formel's (sformel) personal ORCID account.

7. Build and start:
```bash
   docker compose -f docker-compose.dev.yml up -d --build
   docker compose -f docker-compose.dev.yml exec ckan ckan -c /srv/app/ckan.ini obis sync-nodes
   docker compose -f docker-compose.dev.yml exec ckan ckan -c /srv/app/ckan.ini obis sync-institutions
   docker compose -f docker-compose.dev.yml exec ckan ckan -c /srv/app/ckan.ini obis sync-whitelist
```

## User Management

### ORCID Developer App Ownership

The ORCID OAuth application used for catalog login is registered under **Stephen Formel's (sformel) personal ORCID account** — not a shared or organizational account. Any change to registered redirect URIs (e.g., updating dev's URI after a URL/port change) requires his access to make.

Registered redirect URIs:
- `https://products.obis.org/oauth2/callback`
- `https://dev.products.obis.org/oauth2/callback` (updated from `:8443` following the host-nginx SSL refactor, commit 012e3f8 — confirm this has been applied in the ORCID app settings, not just documented here)

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
### Droplet Access

The following individuals have full sudo (root-equivalent) access to the droplet via named accounts:

| User | Linux account |
|---|---|
| Stephen Formel | sformel |
| Silas Principe | sprincipe |

Each account uses a dedicated, personal SSH key. Direct `root` SSH login is disabled (`PermitRootLogin no`); all admin access goes through named accounts plus `sudo`.

**Gotcha — shared repo, multiple identities**: `/opt/obis-products-catalog` and `/opt/dev-obis-products-catalog` are single shared clones used by all sudo users plus the root-run cron job. Git identity (`user.name`/`user.email`) must never be set via `git config --local` in these repos — a local value applies to *whoever* runs git there, regardless of Linux account, and will silently misattribute commits (this happened during onboarding — a stray local override attributed a real commit to "OBIS Catalog Bot"). Each person sets identity in their own `~/.gitconfig` (global scope). The automated whitelist-export script instead scopes the bot identity per-command with `git -c user.name="OBIS Catalog Bot" -c user.email="helpdesk@obis.org" commit ...`, so it never touches shared repo config.

**Gotcha — new user, repo permissions**: A freshly created sudo user will likely hit two errors in these shared repos on first use:
1. `fatal: detected dubious ownership` — fix with `git config --global --add safe.directory <path>` (per-user, run once for each repo).
2. `error: insufficient permission for adding an object to repository database .git/objects` — ownership/group-write issue. Fix with:
```bash
   sudo find <repo-path> -type d -exec chmod g+rwx {} \;
   sudo find <repo-path> -type f -exec chmod g+rw {} \;
   sudo chown -R <owner>:<owner> <repo-path>
   sudo chgrp -R sudo <repo-path>
```
   Directory-level group permissions alone aren't sufficient — individual files (e.g. existing `.git/objects` blobs) may lack the group-write bit if created under a different user's default umask, and must be fixed explicitly with `find`.

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
