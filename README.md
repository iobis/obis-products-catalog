# OBIS Products Catalog

A CKAN-based metadata catalog for discovering and accessing data products created from OBIS-mediated marine biodiversity data. The catalog aggregates metadata from sources like Zenodo, links to OBIS nodes and Ocean Expert institutions, and exports ODIS-compliant Schema.org JSON-LD for semantic web integration.

**[Documentation](https://iobis.github.io/obis-products-catalog/)** · **[Issues](https://github.com/iobis/obis-products-catalog/issues)** · **[OBIS Products Coordination Group](https://manual.obis.org/nodes.html#obis-products-coordination-group)**

## Stack

| Service | Purpose |
|---|---|
| CKAN 2.11 | Core application |
| PostgreSQL | Database |
| Solr 9 | Search index |
| Redis 6 | Caching and job queue |
| Nginx | Reverse proxy |
| DataPusher | Data file processing |

Everything runs in Docker Compose. Total idle memory ~1GB.

## Extensions

| Extension | Plugin name | Purpose |
|---|---|---|
| `ckanext-obis_theme` | `obis_theme` | OBIS visual theme, homepage, dataset pages |
| `ckanext-obis_sync` | `obis_sync` | CLI commands to sync OBIS nodes and institutions |
| `ckanext-odis_export` | `odis_export` | JSON-LD export at `/dataset/<id>/odis.jsonld` |
| `ckanext-zenodo` | `zenodo` | Dataset schema, facets, Solr indexing |
| `ckanext-doi-import` | `doi_import` | Import datasets from DOIs (Zenodo, extensible) |

## Quick Start

```bash
git clone https://github.com/iobis/obis-products-catalog.git
cd obis-products-catalog
cp .env.example .env
# Edit .env with your configuration (see .env.example for required values)

docker compose build
docker compose up -d
```

Create an admin user:

```bash
docker compose exec ckan ckan -c /srv/app/ckan.ini sysadmin add admin email=admin@localhost
```

Sync OBIS data:

```bash
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-nodes
docker compose exec ckan ckan -c /srv/app/ckan.ini obis sync-institutions
```

## Common Operations

```bash
# Rebuild after code changes
docker compose build ckan && docker compose up -d

# View logs
docker compose logs -f ckan

# Rebuild search index
docker compose exec ckan ckan -c /srv/app/ckan.ini search-index rebuild

# Database backup
docker compose exec db pg_dump -U ckandbuser ckandb -Fc > backup_$(date +%Y%m%d).dump
```

## Configuration

All configuration lives in `.env` (never committed). Copy `.env.example` and fill in values. Key settings:

- `CKAN_SITE_URL` — Public URL of your instance
- `CKAN__PLUGINS` — Enabled plugins in load order
- `CKAN___SECRET_KEY`, `CKAN___BEAKER__SESSION__SECRET` — Security secrets (generate with `openssl rand -base64 32`)
- Database passwords must match between standalone vars and connection URL strings

CKAN reads environment variables via the `envvars` plugin using triple-underscore convention: `CKAN___BEAKER__SESSION__SECRET` maps to `beaker.session.secret` in `ckan.ini`.

## Project Structure

```
├── ckan/                         # Dockerfile and startup scripts
├── nginx/                        # Reverse proxy config and SSL certs
├── postgresql/                   # Database init scripts
├── src/                          # Custom CKAN extensions
│   ├── ckanext-obis_theme/       # Visual theme
│   ├── ckanext-obis_sync/        # OBIS data sync commands
│   ├── ckanext-odis_export/      # ODIS JSON-LD export
│   ├── ckanext-zenodo/           # Schema and facets
│   └── ckanext-doi-import/       # DOI import with mapper pattern
├── docs/                         # MkDocs documentation source
├── docker-compose.yml            # Production compose
├── docker-compose.dev.yml        # Development compose
├── mkdocs.yml                    # Docs site config
└── .env.example                  # Configuration template
```

## Contributing

See the [full documentation](https://iobis.github.io/obis-products-catalog/) for architecture details, theming guide, and development setup.

Contact: [helpdesk@obis.org](mailto:helpdesk@obis.org)

## License

AGPL v3.0

devtest
