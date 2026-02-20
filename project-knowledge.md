# OBIS Products Catalog â€” Project Knowledge

## What This Is

The OBIS Products Catalog is a CKAN-based metadata catalog for ocean biodiversity research products. It aggregates metadata about datasets, publications, software, maps, dashboards, and other research outputs from repositories like Zenodo, and makes them discoverable and exportable as ODIS-compliant Schema.org JSON-LD.

It is not a data repository â€” it stores metadata and links to products that live in other systems.

## Who Maintains It

The catalog is maintained by a small team under the OBIS Products Coordination Group (PCG). The codebase needs to be understandable and rebuildable by collaborators without deep CKAN expertise. Decisions should favor simplicity and documentation over clever solutions.

## Repository

- **GitHub**: https://github.com/iobis/obis-products-catalog
- **Branch**: `main`
- **Documentation**: https://iobis.github.io/obis-products-catalog/ (MkDocs Material)
- **Dev instance**: Running on a Digital Ocean droplet at https://obis-catalog.dev.thedatapatch.com (134.199.199.216)
- **Production instance**: Live at https://products.obis.org (143.198.98.101)

## Architecture

### Infrastructure

The entire stack runs in Docker Compose. Six services:

| Service | Image | Purpose | Memory (idle) |
|---|---|---|---|
| **ckan** | Custom (ckan/ckan-base:2.11) | Main application, serves on port 5000 via uwsgi | ~186MB |
| **nginx** | Custom (nginx:stable-alpine) | Reverse proxy, HTTPâ†’HTTPS redirect, Let's Encrypt certs | ~4MB |
| **db** | Custom (PostgreSQL) | Database for CKAN and datastore | ~30MB |
| **solr** | ckan/ckan-solr:2.10-solr9 | Search index | ~700MB |
| **redis** | redis:6 | Caching and job queue | ~3MB |
| **datapusher** | ckan/ckan-base-datapusher:0.0.21 | Processes uploaded data files | ~56MB |

Total idle memory: ~1GB. Under load with 20-40 users: ~2GB. Minimum droplet: 4GB RAM, 2 vCPU, 50GB disk.

### How Traffic Flows

```
Browser â†’ nginx (port 80, redirects to 443) â†’ nginx (port 443, SSL) â†’ ckan (port 5000) â†’ db/solr/redis
```

### HTTPS / SSL

- **Let's Encrypt** certificates, obtained via `certbot --standalone`
- Certs are mounted into nginx container as volumes (not baked into image)
- nginx config redirects all HTTP to HTTPS
- `NGINX_SSLPORT_HOST=443` in `.env`
- Let's Encrypt certs stored at `/etc/letsencrypt/live/<domain>/`
- Volume mounts also include `/etc/letsencrypt/archive/<domain>/` because `live/` files are symlinks

### How Extensions Are Installed

**Production** (`docker-compose.yml`): Extensions in `src/` are COPYed into the Docker image and pip-installed at build time. Changes to extension code require `docker compose build ckan && docker compose up -d`.

**Development**: The `docker-compose.dev.yml` has been removed. Dev work uses the same `docker-compose.yml` as production, running on the dev droplet. Changes require `docker compose build ckan && docker compose up -d`.

**Local dev on Mac (OrbStack/Docker Desktop) is not currently viable.** Attempted and hit multiple issues: `.env` sensitivity to copy-paste errors, permission errors on `prerun.py` and `01_setup_datapusher.sh` causing crash loops. **Decision: use a dedicated dev droplet instead of local dev.**

### Configuration

All configuration is in `.env` (not committed to git). The `.env.example` file in the repo has placeholder values. Key points:

- CKAN uses the `envvars` plugin to read environment variables and override `ckan.ini` at runtime
- The triple-underscore convention maps env vars to config: `CKAN___BEAKER__SESSION__SECRET` â†’ `beaker.session.secret`
- Database passwords appear in multiple env vars (the password itself AND the connection URL strings) â€” they must match
- `CKAN__PLUGINS` controls which plugins are loaded, in order
- `CKAN___CKAN__GROUP_AND_ORGANIZATION_LIST_MAX=1000` and `CKAN___CKAN__GROUP_AND_ORGANIZATION_LIST_ALL_FIELDS_MAX=1000` must be set to support 663+ groups

### Docker Build Context

The production `docker-compose.yml` sets the CKAN build context to the repo root (`.`), not `ckan/`. This is so the Dockerfile can COPY from `src/`. The nginx build context remains `nginx/`.

## Custom Extensions

### ckanext-obis_theme
**Purpose**: Visual theming + i18n overrides
**Plugin**: `obis_theme`
**What it does**:
- Overrides CKAN templates for the OBIS look and feel (homepage, header, footer, dataset pages)
- Provides template helpers for displaying product type and thematic stats
- Template helpers: `obis_get_product_type_stats()`, `obis_get_thematic_stats()`, `obis_get_recent_datasets()`, `dataset_type_class()`
- **Homepage stats show all vocabulary items** even with 0 count, sorted by count descending then alphabetically
- **i18n override**: Translates "Dataset/Datasets" â†’ "Product/Products" throughout the UI via `ITranslation` interface and custom `.po/.mo` files in `i18n/en/LC_MESSAGES/`
- **Snippet override**: `snippets/add_dataset.html` links to `new-choice` page with `owner_org` parameter from org pages
- Uses `DefaultTranslation` from `ckan.lib.plugins` (not `toolkit.DefaultTranslation` which doesn't exist in CKAN 2.11)

### ckanext-obis_sync
**Purpose**: OBIS data sync CLI commands (split from obis_theme)
**Plugin**: `obis_sync`
**What it does**:
- CLI command: `ckan obis sync-nodes` (syncs OBIS nodes as CKAN organizations, prefixed with `node-`)
- CLI command: `ckan obis sync-institutions` (syncs institutions as CKAN groups with Ocean Expert enrichment)
- Both use direct SQLAlchemy model access (not HTTP API)
- `sync-institutions` accepts `--limit N` for testing

### ckanext-odis_export
**Purpose**: ODIS Schema.org JSON-LD export (renamed from ckanext-odis)
**Plugin**: `odis_export`
**What it does**:
- Adds a `/dataset/<id>/odis.jsonld` endpoint to every dataset
- Transforms CKAN dataset metadata to ODIS-compliant Schema.org JSON-LD
- Handles complex nested structures: authors, contributors, funding, spatial coverage, DOI identifiers
- Author mapping supports both schema format (`author_name`) and legacy format (`name`)

**This is the primary output of the catalog** â€” making curated metadata available to ODIS.

### ckanext-zenodo
**Purpose**: Schema definition + Zenodo-specific facets and indexing
**Plugin**: `zenodo`
**What it does**:
- Defines the dataset schema via `zenodo_schema.yaml` (loaded through ckanext-scheming)
- Custom validators for spatial fields and JSON arrays
- Solr indexing customization in `before_dataset_index` for multi-valued tag fields
- Custom facets: Product Types and Thematic Areas
- CLI: `ckan zenodo harvest` â€” bulk import/update from DOI registry file, checks blacklist, uses smart update
- CLI: `ckan zenodo export-whitelist` â€” export all catalog products as CSV for nightly cron
- CLI: `ckan zenodo init-vocabularies` â€” initialize controlled vocabularies

**Key file**: `zenodo_schema.yaml` defines all dataset fields, product types, and thematic areas.

### ckanext-doi-import
**Purpose**: Import datasets from DOIs with mapper pattern for multi-source support
**Plugin**: `doi_import`
**What it does**:
- Web UI: "New Product" choice page (`/dataset/new-choice`) and DOI import form
- Choice page and import form accept `?owner_org=` parameter to pre-select organization
- API endpoint: `/api/harvest-doi` for automated imports
- Mapper pattern: `mappers/base.py` (DOI detection), `mappers/zenodo.py` (Zenodo-specific)
- Contributing organizations saved as CKAN groups (appear in facets and dataset pages)
- Handles resources (links to Zenodo files, not copies)
- **Duplicate detection**: Checks for existing datasets by matching `source_url` before importing. Routes to update if found.
- **Smart update**: On re-import, preserves curated fields (`thematic_tags`, `product_type`, `groups`, `owner_org`, `tag_string`). Only overwrites fields where the source provides a non-empty value.
- **DOI-based URL slugs**: New imports use the DOI as the URL slug (e.g., `/dataset/10-5281-zenodo-17537386`) for stability and uniqueness. Fallback to title-based slug for manual products without DOIs.
- **Blacklist check**: Checks `catalog_blacklist.csv` before importing. Blacklisted DOIs are rejected with an explanation in both web form and API.
- **Flash messages**: Uses CKAN's `flash()` with `alert-warning` category for yellow warning boxes (CKAN 2.11 uses the category directly as a CSS class, not prefixed with `alert-`).

**Adding a new source**: Create `mappers/newsource.py` with `fetch_metadata(doi)`, update `detect_source()` in `base.py`.

### ckanext-public-edit
**Purpose**: Authorization policy for cross-node curation
**Plugin**: `public_edit`
**What it does**:
- Any logged-in user can edit any public dataset
- Any logged-in user can create new datasets
- Only org admins can delete datasets (more restrictive than default CKAN)
- Non-admins cannot change a dataset's `owner_org` (enforced both in template and server-side via `before_dataset_update`)
- Template override: `scheming/form_snippets/organization.html` shows org as read-only text for non-admins editing existing datasets
- Template helper: `h.public_edit_user_can_change_org(owner_org)` checks for admin role specifically (not just editor)

### ckanext-oauth2-login
**Purpose**: ORCID OAuth2 authentication
**Plugin**: `oauth2_login`
**What it does**:
- "Sign in with ORCID" button on login page
- Full OAuth2 authorization code flow with ORCID
- **Whitelist-based access control**: Only ORCID iDs listed in `orcid_whitelist.txt` can log in
- Creates CKAN account on first login (username: `orcid-XXXX-XXXX-XXXX-XXXX`)
- Auto-assigns new users to `obis-community` org as editor
- Reactivates deleted users if still on whitelist
- Session handling mirrors CKAN native login (session regeneration + CSRF token rotation â€” both required for login to persist)
- Stores ORCID iD in `plugin_extras` for future use
- Unapproved users see: "Your ORCID iD is not yet approved. Contact helpdesk@obis.org."

**Whitelist file**: `src/ckanext-oauth2-login/orcid_whitelist.txt` â€” one ORCID per line, comments after `#`. Rebuild required after changes.

**Required `.env` variables**:
```
CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID=APP-XXXXXXXXXXXXXXXX
CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CKANEXT__OAUTH2_LOGIN__REDIRECT_URI=https://your-domain/oauth2/callback
```

## Authentication and Authorization

### Authentication
- **ORCID login**: Primary method for researchers. Whitelist-controlled.
- **No shared admin account**: `ckan_admin` has been purged. All admin access is via ORCID sysadmin accounts.
- **Emergency admin recovery**: SSH to droplet â†’ `docker compose exec -it ckan ckan -c /srv/app/ckan.ini shell` â†’ set any ORCID user as sysadmin via `user.sysadmin = True`.

### Current Sysadmins
- Stephen Formel (orcid-0000-0001-7418-1244) â€” currently the only one with an active account
- Pieter Provoost, Ward Appeltans, Silas Principe, Jonathan Pye â€” will become sysadmins on first ORCID login

### Authorization Model
| Action | Who can do it |
|---|---|
| View public products | Anyone |
| Edit public products | Any logged-in user |
| Create new products | Any logged-in user |
| Delete products | Organization admins and sysadmins only |
| Change a product's organization | Organization admins and sysadmins only |

## Data Model

### Current State
38 active products on production (products.obis.org), ~42 on dev. No shared admin user. ORCID-based sysadmins.

### Product Types (controlled vocabulary, in schema YAML)
dataset, publication, software, presentation, poster, image, video, lesson, physical_object, other

### Thematic Areas (controlled vocabulary, in schema YAML)
Biodiversity, Climate Change, Ocean Acidification, Marine Protected Areas, eDNA, Invasives, Fisheries, Pollution, Coastal Management, Deep Sea, Coral Reefs, Species Distribution, Near-Realtime

### Organizations (CKAN organizations)
38 OBIS nodes + OBIS Secretariat + OBIS Community, synced from the OBIS API. Prefixed with `node-` to avoid namespace collisions. `obis-community` is the default org for new ORCID users.

### Groups (CKAN groups)
663 research institutions, synced from OBIS API and enriched with Ocean Expert data.

### Key Schema Fields
- `canonical_id`: DOI URL as persistent identifier (used as `@id` in ODIS export). Populated automatically by the Zenodo mapper.
- `source_url`: URL of the original record at the source repository (e.g., `https://zenodo.org/record/11464531`). Used for duplicate detection on import.
- `resource_type`: Schema.org type (e.g., `Dataset`, `PresentationDigitalDocument`)
- `authors`, `contributors`, `funding`: JSON arrays (stored as strings, parsed on read). Authors schema expects `author_name`, `author_affiliation_name` etc. but legacy data uses `name`, `affiliation`.
- `product_type`: Multi-value from controlled vocabulary
- `thematic_tags`: Multi-value from controlled vocabulary
- `spatial_coverage_type`, `spatial_point_*`, `spatial_box`: Spatial metadata for ODIS

## Data Pipeline

The catalog serves as a curation layer between source repositories and ODIS:

```
Source API (Zenodo, future: GBIF, Dryad, etc.)
    â†“ mapper (Python function: API response â†’ standard dict)
    â†“
CKAN (storage, curation UI, search, user management)
    â†“ odis_export extension (CKAN dataset â†’ Schema.org JSON-LD)
    â†“
ODIS (discovery, federated search)
```

Adding a new source requires writing one mapper file in `ckanext-doi-import/ckanext/doi_import/mappers/`.

## Catalog Manifest

Two CSV files at the repo root serve as the archivable, citable record of the catalog:

**`catalog_whitelist.csv`** â€” Every product in the catalog, exported nightly from the database. Columns: `doi`, `title`, `source_url`, `catalog_url`. Version-controlled in git, auto-committed by cron at 2am UTC if changes detected.

**`catalog_blacklist.csv`** â€” DOIs reviewed and determined out of scope. Manually curated. Columns: `doi`, `title`, `source_url`, `reason`, `reviewed_date`. Checked by web form, API, and bulk harvest CLI before importing.

The nightly export runs via `/root/bin/export-whitelist.sh` on the prod droplet, using a deploy key for passwordless git push. The deploy key is repo-scoped (not user-scoped) and can be managed by any repo admin.

The `doi_registry.txt` seed file has been removed â€” the database is the source of truth, and the whitelist CSV is the ongoing record.

## Documentation

MkDocs Material site deployed to GitHub Pages via GitHub Actions.

- **Source**: `docs/` directory in repo root + `mkdocs.yml`
- **URL**: https://iobis.github.io/obis-products-catalog/
- **Deployment**: Push to `main` triggers `.github/workflows/docs.yml` â†’ builds with `mkdocs build` â†’ deploys via `actions/deploy-pages`
- **Pages source**: Set to "GitHub Actions" in repo Settings â†’ Pages

### Doc pages:
- **Home**: Project overview, key features, infrastructure summary
- **User Guide**: Signing in (ORCID whitelist), data model, product types, searching, contributing products, permissions, DOI import workflow, catalog manifest
- **Theming & Aesthetics**: Colors, fonts, logos, icons â€” for comms team
- **Architecture**: Infrastructure, services, auth model, plugin load order
- **Extensions**: All seven custom extensions documented
- **Operations**: Routine commands, catalog manifest, user management (whitelist), troubleshooting, gotchas
- **Data Model, Contributing**: Skeleton pages to flesh out

## Operations

### Plugin Load Order (CRITICAL)

```
CKAN__PLUGINS="envvars image_view text_view public_edit oauth2_login scheming_datasets scheming_groups obis_theme obis_sync odis_export zenodo doi_import"
```

**`public_edit` must come BEFORE `scheming_datasets`** â€” so its template override for the organization field takes effect. Plugins loaded earlier in the list have higher template priority for overriding scheming templates.

### Routine Commands

```bash
# Restart everything
docker compose down && docker compose up -d

# Rebuild after code changes
docker compose build ckan && docker compose up -d

# View logs
docker compose logs -f ckan

# Rebuild search index (after DB restore or missing datasets)
docker compose exec ckan ckan -c /srv/app/ckan.ini search-index rebuild

# Database backup
docker compose exec db pg_dump -U ckandbuser ckandb -Fc > backup_$(date +%Y%m%d).dump

# Sync OBIS nodes
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-nodes

# Sync institutions
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-institutions

# Export catalog whitelist
docker compose exec ckan ckan -c /srv/app/ckan.ini zenodo export-whitelist

# Bulk harvest from DOI registry
docker compose exec ckan ckan -c /srv/app/ckan.ini zenodo harvest
```

### User Management

**Add to whitelist**: Edit `src/ckanext-oauth2-login/orcid_whitelist.txt`, add ORCID iD, rebuild and restart.

**Promote to sysadmin**: `docker compose exec -it ckan ckan -c /srv/app/ckan.ini shell` then:
```python
from ckan import model
user = model.User.by_name('orcid-XXXX-XXXX-XXXX-XXXX')
user.sysadmin = True
model.Session.commit()
```

**Purge a user**: Same shell, then `user.purge()` and `model.Session.commit()`.

**Warning**: If you only set a user to `deleted` state without removing from whitelist, they will be reactivated on next ORCID login.

### Git Workflow

Work happens on branches off `main`. Changes are committed on the droplet and pushed to GitHub.

`.env` is never committed. Each deployment maintains its own `.env` from `.env.example`.

### What Breaks and Why

| Symptom | Likely Cause |
|---|---|
| CKAN won't start, "no python application found" | Check logs for Python traceback above this message. Usually a DB connection issue or missing extension. |
| `PluginNotFoundException` after rename | Check `pyproject.toml` entry points match the plugin name in `.env`. This file takes precedence over `setup.cfg`. |
| Datasets missing in browser but exist in DB | Solr index needs rebuild: `search-index rebuild` |
| Facet counts show on homepage but clicking returns zero results | Solr indexing field mismatch â€” check `before_dataset_index` field names match schema. Rebuild index after fix. |
| Nginx "host not found in upstream" | CKAN service isn't running. Start it first, wait for healthy, then restart nginx. |
| Extensions not found after code change | Forgot to rebuild: `docker compose build ckan` |
| Permission errors on `test.ini` during startup | Non-fatal warnings from extension installer. Can be ignored. |
| Exit code 137 | Out of memory. Check `docker stats`. Solr is usually the culprit. |
| `group_list` returns TypeError on `limit` | Set `CKAN___CKAN__GROUP_AND_ORGANIZATION_LIST_MAX` and `CKAN___CKAN__GROUP_AND_ORGANIZATION_LIST_ALL_FIELDS_MAX` in `.env` |
| Dev compose crash loop with permission denied on `prerun.py` | Known issue with `docker-compose.dev.yml` on Mac. Use a dev droplet instead. |
| Org dropdown still editable for non-admins | `public_edit` must load before `scheming_datasets` in plugins |
| ORCID login: flash message appears but user not logged in | User may be in `deleted` state. Check with `user_show` include_deleted. Reactivate or purge and re-login. |
| ORCID login: `login_user` returns False | User is inactive. Check `userobj.is_active` and `userobj.state`. |
| `AttributeError: DefaultTranslation` | Import from `ckan.lib.plugins` not `toolkit` |
| DOI import says "excluded from catalog" | DOI is on the blacklist (`catalog_blacklist.csv`) â€” remove it if this was a mistake |
| DOI import says "already in catalog" | Product exists â€” it will be updated with curated fields preserved |
| Flash messages not styled (no color) | CKAN 2.11 uses the flash category directly as CSS class. Use `alert-warning`, `alert-info`, etc., not `warning` or `info` |

### Resolved Issues (Session Log)

- **Split obis_theme**: Extracted sync commands into `ckanext-obis_sync`. Theme-only code stays in `ckanext-obis_theme`.
- **Refactored doi_import**: Mapper pattern with `mappers/base.py` and `mappers/zenodo.py`. Removed dead code and debug print statements.
- **Renamed odis â†’ odis_export**: Full rename of directory, Python package, entry points in `pyproject.toml`, `setup.cfg`, Dockerfile, `.env`. Key lesson: `pyproject.toml` entry points take precedence over `setup.cfg`.
- **Fixed authors in ODIS JSON-LD**: Export now handles both `author_name` (schema) and `name` (legacy) formats. Zenodo mapper updated to output schema-correct field names.
- **Fixed contributing orgs in DOI import**: Groups now saved via CKAN `groups` key (not custom field). Set `group_and_organization_list_max=1000` in `.env` to show all 663 institutions.
- **Spatial and funding in JSON-LD**: Confirmed working after testing with manually-added data.
- **Removed test users and ckan_admin**: All admin access now via ORCID sysadmins.
- **Repo cleanup**: Replaced old README with concise version. Removed obsolete docs.
- **MkDocs docs**: Set up with Material theme, deployed to GitHub Pages. Updated with auth/extension/operations content.
- **Built ckanext-public-edit**: Cross-node editing with org field protection. Override scheming's `organization.html` form snippet (not CKAN's `package_basic_fields.html`).
- **Built ckanext-oauth2-login**: ORCID OAuth2 with whitelist, auto-assign to obis-community, session regeneration.
- **HTTPS via Let's Encrypt**: Set up on dev domain `obis-catalog.dev.thedatapatch.com`. Nginx config with HTTPâ†’HTTPS redirect.
- **Datasetâ†’Product i18n**: English translation override in obis_theme replaces all "Dataset/Datasets" with "Product/Products".
- **Org pre-selection**: "Add Product" from org pages passes `owner_org` through to create and import forms.
- **Removed JS redirect script**: Was in `base.html`, overwriting org URLs. Replaced by proper snippet override.
- **Added Near-Realtime thematic area**: In `zenodo_schema.yaml`.
- **Production deployment**: Stood up prod at products.obis.org. SSL, ORCID login, nodes/institutions synced, 38 products imported via bulk harvest.
- **Homepage shows all vocabulary items**: Product types and thematic areas display even with 0 count, helping users understand the full taxonomy. Sort: count descending, then alphabetical.
- **DOI import duplicate detection**: Web form checks for existing datasets by `zenodo_url` field. Routes to smart update if found, preserving curated fields.
- **DOI-based URL slugs**: Replaced title-based slugs (collision-prone) with DOI-based slugs for stability and uniqueness.
- **Catalog manifest system**: Nightly whitelist export to CSV via cron, blacklist enforcement on import. Removed `doi_registry.txt` and in-container file writing.
- **Flash message styling**: CKAN 2.11 uses flash category as CSS class directly (not prefixed). Use `alert-warning` for yellow, `alert-info` for blue, `success` for green.
- **Deploy key for prod**: Repo-scoped SSH deploy key (no passphrase) for automated git push from cron.
- **Removed docker-compose.dev.yml and load test scripts**: Dev uses same compose as prod on dev droplet.
- **Updated DEPLOYMENT.md**: Full walkthrough including SSL, ORCID sysadmin setup, node/institution sync, whitelist export cron.
- **Renamed zenodo_url → source_url (Issue #27)**: Schema field renamed, mapper updated to output `source_url` and populate `canonical_id`, duplicate detection updated, whitelist export updated, templates updated.
- **ODIS sitemap and robots.txt (Issues #34, #35)**: Dynamic sitemap at `/sitemap.xml` listing all JSON-LD endpoints. robots.txt served via nginx with crawler directives.
- **ORCID whitelist update (Issue #33)**: Added Emilie Boulanger, Saara Suominen, Laurent Chmiel, Lisa Benedetti.
- **Dataset page JSON rendering**: Authors, contributors, and funding parsed from JSON and displayed as formatted HTML instead of raw JSON strings.
- **OBIS Community org**: sync-nodes now automatically creates the obis-community organization.

## Gotchas

1. **Plugin load order matters**: `public_edit` must come BEFORE `scheming_datasets` in `CKAN__PLUGINS`. Earlier = higher template priority for scheming template overrides.
2. **Scheming uses its own templates**: To override org field behavior, override `scheming/form_snippets/organization.html`, NOT `package/snippets/package_basic_fields.html`.
3. **CKAN 2.11 login requires session regeneration**: After `login_user()`, must also call session `regenerate()` and `rotate_token()` or the session won't persist.
4. **Deleted users get reactivated**: ORCID users in `deleted` state are reactivated on login if still on whitelist. Remove from whitelist AND purge to fully block.
5. **`DefaultTranslation` import**: Use `from ckan.lib.plugins import DefaultTranslation`, not `toolkit.DefaultTranslation`.
6. **Let's Encrypt cert volumes**: Must mount both `live/` and `archive/` directories because `live/` contains symlinks.
7. **Heredocs with Jinja syntax**: Shell heredocs (`<< 'EOF'`) break on `{%`, `{{` etc. Use Python file writes or `cat > /tmp/file` from a temp file instead.
8. **CKAN 2.11 flash message styling**: `flash("message", "warning")` adds CSS class `warning`, not `alert-warning`. Use `alert-warning` as the category to get Bootstrap styling.
9. **Heredocs in Claude sessions**: Shell heredocs also break when file content contains backticks, curly braces, or other shell-interpreted characters. For writing large files, use a Python script or edit directly in VS Code via SSH.
10. **Deploy keys are repo-scoped**: A GitHub deploy key grants access to one repo, not the whole org. Add via repo Settings â†’ Deploy Keys. Any repo admin can manage it.

## Open Questions / Future Work

- **Organizationâ†’Node renaming**: i18n override to replace "Organization/Organizations" with "Node/Nodes" throughout UI. Deferred to future sprint.
- **Search help box (Issue #14)**: Add persistent "Need help?" sidebar on search page + enhanced "no results" message directing users to helpdesk@obis.org.
- **Move thematic areas to dynamic vocabulary** if update frequency increases.
- **Automated DB backups**: Cron job similar to whitelist export.
- **SMTP configuration**: For future email notifications (user approval, etc.).
- **Purge temporary sysadmin on prod**: Once ORCID sysadmin is confirmed working.