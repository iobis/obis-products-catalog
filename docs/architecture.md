# Architecture

!!! note "Stub"
    This page is a skeleton. Content will be filled in during documentation sprints.

## Infrastructure

The entire stack runs in Docker Compose with six services: CKAN, Nginx, PostgreSQL, Solr, Redis, and DataPusher.

```
Browser → nginx (port 80) → ckan (port 5000) → db/solr/redis
```

## Services

| Service | Image | Purpose |
|---|---|---|
| **ckan** | Custom (ckan/ckan-base:2.11) | Main application |
| **nginx** | Custom (nginx:stable-alpine) | Reverse proxy |
| **db** | Custom (PostgreSQL) | Database |
| **solr** | ckan/ckan-solr:2.10-solr9 | Search index |
| **redis** | redis:6 | Caching and job queue |
| **datapusher** | ckan/ckan-base-datapusher:0.0.21 | Data file processing |

## How Extensions Are Installed

**Production** (`docker-compose.yml`): Extensions in `src/` are COPYed into the Docker image and pip-installed at build time.

**Development** (`docker-compose.dev.yml`): Extensions in `src/` are mounted as a volume and auto-installed on startup.

## Configuration

All configuration is in `.env` (not committed to git). CKAN reads environment variables via the `envvars` plugin with triple-underscore convention: `CKAN___BEAKER__SESSION__SECRET` → `beaker.session.secret`.
