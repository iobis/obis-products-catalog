# Deploying OBIS Products Catalog on a Digital Ocean Droplet

This guide assumes you have a Digital Ocean droplet (Ubuntu, minimum 4GB RAM, 2 vCPU, 50GB disk) with SSH access and root privileges.

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
cd /opt
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
| `CKAN_SYSADMIN_PASSWORD` | Choose a strong password (temporary — will be purged after ORCID setup) |
| `CKAN_SYSADMIN_EMAIL` | Set to a real email address |
| `CKAN_SITE_URL` | Set to `https://your-domain.org` |
| `CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID` | From ORCID developer portal |
| `CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_SECRET` | From ORCID developer portal |
| `CKANEXT__OAUTH2_LOGIN__REDIRECT_URI` | `https://your-domain.org/oauth2/callback` |

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

## 5. Build and start (HTTP first)

Set `NGINX_SSLPORT_HOST=4443` temporarily in `.env` (to disable HTTPS until certs are ready), then:
```bash
docker compose build
docker compose up -d
```

Watch the startup:
```bash
docker compose logs -f ckan
```

Wait until you see `WSGI app 0 (mountpoint='') ready` and the healthcheck passing. Ctrl+C to exit.

## 6. Set up SSL with Let's Encrypt

Stop nginx so certbot can bind to port 80:
```bash
docker compose stop nginx
```

Install certbot and obtain certificate:
```bash
apt install -y certbot
certbot certonly --standalone -d your-domain.org
```

Update `docker-compose.yml` to mount the cert paths:
```yaml
volumes:
  - /etc/letsencrypt/live/your-domain.org:/etc/letsencrypt/live/your-domain.org:ro
  - /etc/letsencrypt/archive/your-domain.org:/etc/letsencrypt/archive/your-domain.org:ro
```

**Important**: Mount both `live/` and `archive/` directories because `live/` contains symlinks to files in `archive/`.

Update `nginx/setup/default.conf` with your domain and cert paths. Then set `NGINX_SSLPORT_HOST=443` in `.env` and restart:
```bash
docker compose up -d
```

Verify HTTPS works:
```bash
curl -s -o /dev/null -w "%{http_code}" https://your-domain.org
```

## 7. Verify everything is running
```bash
docker compose ps
```

All services should show `healthy` or `Up`:
- **ckan** — main application
- **db** — PostgreSQL database
- **solr** — search index
- **redis** — caching/queue
- **nginx** — reverse proxy (ports 80 → 443 → ckan:5000)
- **datapusher** — processes uploaded data files

Visit `https://your-domain.org` in your browser.

## 8. Sync OBIS data
```bash
# Sync OBIS nodes as organizations (39 orgs)
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-nodes

# Sync institutions as groups with Ocean Expert enrichment (659 groups)
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-institutions
```

## 9. Import products

Run the bulk harvest to import products from the DOI registry:
```bash
docker compose exec ckan ckan -c /srv/app/ckan.ini zenodo harvest
```

Or import individual DOIs through the web UI at `/dataset/import-doi`.

## 10. Set up ORCID sysadmin

Log in with your ORCID to create your account, then promote it to sysadmin:
```bash
docker compose exec -it ckan ckan -c /srv/app/ckan.ini shell
```
```python
from ckan import model
user = model.User.by_name('orcid-XXXX-XXXX-XXXX-XXXX')
user.sysadmin = True
model.Session.commit()
```

Then purge the temporary `ckan_admin` account:
```bash
docker compose exec -it ckan ckan -c /srv/app/ckan.ini shell
```
```python
from ckan import model
user = model.User.by_name('ckan_admin')
user.purge()
model.Session.commit()
```

## 11. Set up nightly whitelist export

Create a deploy key for automated git push (no passphrase):
```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N "" -C "obis-catalog-deploy"
cat ~/.ssh/github_deploy.pub
# Add as deploy key at: GitHub repo → Settings → Deploy keys → Allow write access
git config core.sshCommand "ssh -i ~/.ssh/github_deploy"
git remote set-url origin git@github.com:iobis/obis-products-catalog.git
```

Set up git identity for automated commits:
```bash
git config user.email "helpdesk@obis.org"
git config user.name "OBIS Catalog Bot"
```

Create the export script:
```bash
mkdir -p /root/bin
cat > /root/bin/export-whitelist.sh << 'EOF'
#!/bin/bash
cd /opt/obis-products-catalog
docker compose exec -T ckan ckan -c /srv/app/ckan.ini zenodo export-whitelist 2>/dev/null > catalog_whitelist.csv
git add catalog_whitelist.csv
git diff --cached --quiet catalog_whitelist.csv || (git commit -m "Auto-update catalog whitelist $(date +%Y-%m-%d)" && git push)
EOF
chmod +x /root/bin/export-whitelist.sh
```

Test it:
```bash
/root/bin/export-whitelist.sh
```

Add to cron (runs at 2am UTC daily):
```bash
crontab -e
```

Add:
```
0 2 * * * /root/bin/export-whitelist.sh >> /var/log/whitelist-export.log 2>&1
```

## Routine Operations

**Restart everything:**
```bash
docker compose down && docker compose up -d
```

**View logs:**
```bash
docker compose logs -f ckan
```

**Rebuild after code changes to extensions in `src/`:**
```bash
docker compose build ckan && docker compose up -d
```

**Database backup:**
```bash
docker compose exec db pg_dump -U ckandbuser ckandb -Fc > backup_$(date +%Y%m%d).dump
```

**Database restore:**
```bash
docker compose exec -T db pg_restore -U ckandbuser -d ckandb --clean < backup_file.dump
docker compose exec ckan ckan -c /srv/app/ckan.ini search-index rebuild
```

**Export catalog whitelist manually:**
```bash
docker compose exec ckan ckan -c /srv/app/ckan.ini zenodo export-whitelist
```

## Troubleshooting

| Symptom | Likely Cause |
|---|---|
| CKAN won't start, "no python application found" | Check `docker compose logs ckan` for Python traceback above this message |
| Nginx "host not found in upstream" | CKAN service isn't running. Start ckan first, wait for healthy, then restart nginx |
| Datasets missing but DB has data | Rebuild Solr index: `search-index rebuild` |
| Extensions not found after code change | Forgot to rebuild: `docker compose build ckan` |
| Exit code 137 | Out of memory — check `docker stats`. Solr is usually the culprit |
| ORCID login: flash message but not logged in | User may be in `deleted` state. Reactivate or purge and re-login |
| DOI import says "excluded from catalog" | DOI is on the blacklist (`catalog_blacklist.csv`) |
| DOI import says "already in catalog" | Product exists — it will be updated with curated fields preserved |
| Permission errors on `test.ini` during startup | Non-fatal warnings from extension installer. Ignore |

## Git Workflow

This repo uses `.env` for all secrets. The `.env` file is in `.gitignore` and is **never committed**. Each deployment maintains its own `.env`.

Work happens on branches off `main`. Changes are committed on the droplet and pushed to GitHub.

```bash
git checkout -b my-feature

# make changes
docker compose build ckan && docker compose up -d  # test
git add . && git commit -m "Description of change"
git push origin my-feature

# merge to main when stable
```
