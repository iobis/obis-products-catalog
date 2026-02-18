# Operations

!!! note "Stub"
    This page is a skeleton. Content will be filled in during documentation sprints.

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

## Troubleshooting

| Symptom | Likely Cause |
|---|---|
| CKAN won't start | Check `docker compose logs ckan` for Python traceback |
| Datasets missing in browser | Solr index needs rebuild |
| Facet counts wrong | Check `before_dataset_index` field names, rebuild index |
| Nginx "host not found" | CKAN service isn't running |
| Extensions not found | Forgot to rebuild after code change |
| Exit code 137 | Out of memory — check `docker stats` |
| Org dropdown still editable for non-admins | `public_edit` must load before `scheming_datasets` in plugins |
| `group_list` returns TypeError on `limit` | Set `CKAN___CKAN__GROUP_AND_ORGANIZATION_LIST_MAX=1000` in `.env` |

## Gotchas

### Plugin load order matters

The `CKAN__PLUGINS` order in `.env` affects template priority. Plugins loaded **earlier** in the list have **higher** template priority. Current required ordering:

- `public_edit` must come **before** `scheming_datasets` (so its organization field override takes effect)
- `public_edit` must come **before** `scheming_datasets` was also true for `obis_theme` template overrides

Example:
```
CKAN__PLUGINS="envvars image_view text_view public_edit scheming_datasets scheming_groups obis_theme obis_sync odis_export zenodo doi_import"
```

### `.env` is never committed

Each deployment maintains its own `.env` from `.env.example`. Database passwords appear in multiple env vars (standalone vars AND connection URL strings) — they must match.

## Git Workflow

All work happens on branches off `prod-setup`. Changes are committed on the droplet and pushed to GitHub. When stable, branches merge to `main`.

`.env` is never committed. Each deployment maintains its own `.env` from `.env.example`.
