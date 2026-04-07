# Architecture

## Infrastructure

The entire stack runs in Docker Compose with six services: CKAN, Nginx, PostgreSQL, Solr, Redis, and DataPusher.

```
Browser → nginx (port 80) → ckan (port 5000) → db/solr/redis
```

## Services

| Service | Image | Purpose |
|---|---|---|
| **ckan** | Custom (ckan/ckan-base:2.11) | Main application |
| **nginx** | Custom (nginx:stable-alpine) | Reverse proxy, serves static docs at `/docs` |
| **db** | Custom (PostgreSQL) | Database |
| **solr** | ckan/ckan-solr:2.10-solr9 | Search index |
| **redis** | redis:6 | Caching and job queue |
| **datapusher** | ckan/ckan-base-datapusher:0.0.21 | Data file processing |

## How Extensions Are Installed

Extensions in `src/` are COPYed into the Docker image and pip-installed at build time. Changes to extension code require a rebuild:

```bash
docker compose build ckan && docker compose up -d
```

Development is done on a dedicated Digital Ocean droplet using the same `docker-compose.yml` as production. Local Docker setup on Mac is not currently viable due to known permission issues.

## Configuration

All configuration is in `.env` (not committed to git). CKAN reads environment variables via the `envvars` plugin with triple-underscore convention: `CKAN___BEAKER__SESSION__SECRET` → `beaker.session.secret`.

## Authentication and Authorization

### Authentication

The catalog supports two login methods:

- **ORCID login** — Primary method for researchers. OAuth2-based login, restricted to ORCID iDs on an approved whitelist.
- **CKAN accounts** — Used for automated processes and emergency admin access only. No shared admin account exists — all admin access is via ORCID sysadmin accounts.

New ORCID users are automatically assigned to the **OBIS Community** organization as editors on first login.

### Authorization Model

The catalog uses a custom authorization model via `ckanext-public-edit` that differs from default CKAN:

| Action | Who can do it |
|---|---|
| **View public datasets** | Anyone |
| **Edit public datasets** | Any logged-in user |
| **Create new datasets** | Any logged-in user |
| **Delete datasets** | Organization admins and sysadmins only |
| **Change a dataset's organization** | Organization admins and sysadmins only |
| **Manage org members** | Organization admins and sysadmins |

This model enables cross-node curation: a researcher from any OBIS node can annotate, tag, and improve metadata on any public dataset in the catalog, without needing membership in the owning organization.

### Organization Assignment

- All new users are assigned to the **OBIS Community** (`obis-community`) organization as editors
- Users can request addition to specific node organizations from an admin
- Datasets retain their original owning organization regardless of who edits them

### Plugin Load Order

Plugin load order in `CKAN__PLUGINS` matters. Current required order:

```
envvars image_view text_view public_edit oauth2_login scheming_datasets scheming_groups obis_theme obis_sync odis_export zenodo doi_import
```

`public_edit` must come **before** `scheming_datasets` so its template overrides take effect.