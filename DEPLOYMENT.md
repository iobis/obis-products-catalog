# Deploying OBIS Products Catalog on a Digital Ocean Droplet

This guide assumes you have a Digital Ocean droplet (Ubuntu, minimum 4GB RAM) with SSH access and root privileges.

## 1. Install Docker and Docker Compose

```bash
# Update packages
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Verify
docker --version
docker compose version
```

## 2. Clone the repo

```bash
cd ~
git clone git@github.com:iobis/obis-products-catalog.git
cd obis-products-catalog
```

If you haven't set up SSH keys for GitHub on this droplet:

```bash
ssh-keygen -t ed25519 -C "your@email.com"
cat ~/.ssh/id_ed25519.pub
# Add this key at: GitHub → Settings → SSH and GPG keys → New SSH key
ssh -T git@github.com  # confirm it works
```

## 3. Configure environment

```bash
cp .env.example .env
```

Now edit `.env` and replace all placeholder values with real secrets:

```bash
nano .env
```

**You must change these values** (do not use the defaults):

| Variable | What to do |
|---|---|
| `POSTGRES_PASSWORD` | Generate: `python3 -c "import secrets; print(secrets.token_urlsafe(16))"` |
| `CKAN_DB_PASSWORD` | Generate a new password, then also update it in `CKAN_SQLALCHEMY_URL`, `CKAN_DATASTORE_WRITE_URL` |
| `DATASTORE_READONLY_PASSWORD` | Generate a new password, then also update it in `CKAN_DATASTORE_READ_URL` |
| `CKAN___SECRET_KEY` | Generate: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `CKAN___BEAKER__SESSION__SECRET` | Generate (same command as above) |
| `CKAN___API_TOKEN__JWT__ENCODE__SECRET` | Generate: `python3 -c "import secrets; print('string:' + secrets.token_urlsafe(32))"` |
| `CKAN___API_TOKEN__JWT__DECODE__SECRET` | Generate (same command as above) |
| `CKAN_SYSADMIN_PASSWORD` | Choose a strong password for the CKAN admin account |
| `CKAN_SYSADMIN_EMAIL` | Set to a real email address |
| `CKAN_SITE_URL` | Set to `http://<YOUR_DROPLET_IP>` |

**Important**: The DB password appears in multiple places. If you set `CKAN_DB_PASSWORD=mypassword`, you must also update:
- `CKAN_SQLALCHEMY_URL=postgresql://ckandbuser:mypassword@db/ckandb`
- `CKAN_DATASTORE_WRITE_URL=postgresql://ckandbuser:mypassword@db/datastore`

Same for `DATASTORE_READONLY_PASSWORD` in `CKAN_DATASTORE_READ_URL`.

## 4. Open firewall ports

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## 5. Build and start

```bash
docker compose build
docker compose up -d
```

This will take a few minutes on first run. Watch the startup:

```bash
docker compose logs -f ckan
```

Wait until you see `WSGI app 0 (mountpoint='') ready` and the healthcheck passing (200 responses to `/api/action/status_show`). Ctrl+C to exit the logs.

## 6. Verify everything is running

```bash
docker compose ps
```

All services should show `healthy` or `Up`:
- **ckan** — the main application
- **db** — PostgreSQL database
- **solr** — search index
- **redis** — caching/queue
- **nginx** — reverse proxy (serves on port 80)
- **datapusher** — processes uploaded data files

Test from the command line:

```bash
curl http://localhost/api/action/status_show
```

You should see a JSON response with `"success": true`. Then visit `http://<YOUR_DROPLET_IP>` in your browser.

## 7. Rebuild the search index (if restoring data)

If you've restored a database dump or the site shows no datasets:

```bash
docker compose exec ckan ckan -c /srv/app/ckan.ini search-index rebuild
```

## Routine operations

**Restart everything:**
```bash
docker compose down
docker compose up -d
```

**View logs:**
```bash
docker compose logs -f ckan        # CKAN application
docker compose logs -f nginx       # web server
docker compose logs --tail=50 db   # database
```

**Rebuild after code changes to extensions in `src/`:**
```bash
docker compose build ckan
docker compose up -d
```

Note: because extensions are baked into the Docker image at build time (not mounted as volumes), you must rebuild the `ckan` image whenever you change extension code.

**Database backup:**
```bash
docker compose exec db pg_dump -U ckandbuser ckandb -Fc > backup_$(date +%Y%m%d).dump
```

**Database restore:**
```bash
docker compose exec -T db pg_restore -U ckandbuser -d ckandb --clean < backup_file.dump
docker compose exec ckan ckan -c /srv/app/ckan.ini search-index rebuild
```

## Git workflow

This repo uses `.env` for all secrets. The `.env` file is in `.gitignore` and is **never committed**. Each deployment maintains its own `.env`.

To work on changes:

```bash
git checkout -b my-feature
# make changes
git add .
git commit -m "Description of change"
git push origin my-feature
```

After changing extension code, rebuild:

```bash
docker compose build ckan
docker compose up -d
```

## Troubleshooting

**CKAN won't start / exit code 1:**
```bash
docker compose logs --tail=50 ckan
```
Usually a database connection issue. Verify `CKAN_SQLALCHEMY_URL` in `.env` matches the actual DB credentials.

**"no python application found":**
CKAN failed to load. Check the full logs — there's usually a Python traceback above this message indicating the actual error.

**Nginx "host not found in upstream":**
The `ckan` service isn't running. Start it first: `docker compose up -d ckan`, wait for it to become healthy, then `docker compose up -d nginx`.

**Datasets missing but DB has data:**
Rebuild the Solr search index:
```bash
docker compose exec ckan ckan -c /srv/app/ckan.ini search-index rebuild
```

**Permission errors during startup:**
If CKAN logs show `PermissionError` on `test.ini` files, these are non-fatal warnings from the extension installer and can be ignored.
