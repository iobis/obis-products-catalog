---
layout: default
title: Developer Guide
nav_order: 4
---

# Developer Guide
{: .no_toc }

Information for developers contributing to or deploying the OBIS Products Catalog.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Git
- 4GB+ RAM recommended

### Quick Start

```bash
# Clone the repository
git clone https://github.com/iobis/obis-products-catalog.git
cd obis-products-catalog

# Copy environment template
cp .env.obis.example .env

# Edit .env with your configuration
nano .env

# Build and start
docker compose -f docker-compose.dev.yml up -d --build

# Initialize database
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini db init

# Create admin user
docker exec obis-products-catalog-ckan-dev-1 ckan -c /srv/app/ckan.ini sysadmin add admin email=admin@localhost
```

Access at: `http://localhost:5000`

---

## Repository Structure

```
obis-products-catalog/
├── ckan/                      # CKAN Docker configuration
│   ├── Dockerfile            # Production image
│   └── Dockerfile.dev        # Development image
├── nginx/                     # Reverse proxy config
├── postgresql/                # Database initialization
├── src/                       # CKAN extensions
│   ├── ckanext-obis_theme/   # Custom UI
│   ├── ckanext-odis/         # JSON-LD export
│   ├── ckanext-zenodo/       # Zenodo integration
│   └── ckanext-doi_import/   # DOI import
├── docker-compose.dev.yml     # Development setup
└── .env.obis.example          # Environment template
```

---

## Development Workflow

### Making Changes to Extensions

Extensions are mounted from `src/` and auto-reload in dev mode:

```bash
# Edit files in src/ckanext-obis_theme/
nano src/ckanext-obis_theme/ckanext/obis_theme/templates/home/index.html

# Changes apply immediately (refresh browser)
```

For Python code changes, restart CKAN:

```bash
docker compose -f docker-compose.dev.yml restart ckan-dev
```

### Modifying the Theme

**Homepage:**
- Templates: `src/ckanext-obis_theme/ckanext/obis_theme/templates/home/`
- Helpers: `src/ckanext-obis_theme/ckanext/obis_theme/helpers.py`

**Styles:**
- CSS: `src/ckanext-obis_theme/ckanext/obis_theme/assets/style.css`
- Public files: `src/ckanext-obis_theme/ckanext/obis_theme/public/`

**After changes:**
```bash
docker compose -f docker-compose.dev.yml restart ckan-dev
```

### Modifying the Schema

Edit the metadata schema:

```bash
nano src/ckanext-zenodo/ckanext/zenodo/zenodo_schema.yaml
docker compose -f docker-compose.dev.yml restart ckan-dev
```

Changes apply immediately - no rebuild needed.

---

## Syncing Data

### Sync OBIS Nodes

```bash
docker exec obis-products-catalog-ckan-dev-1 \
  ckan -c /srv/app/ckan.ini obis sync-nodes
```

### Sync OBIS Institutions

```bash
# Test with 10 institutions
docker exec obis-products-catalog-ckan-dev-1 \
  ckan -c /srv/app/ckan.ini obis sync-institutions --limit 10

# Full sync (~11 minutes for 668 institutions)
docker exec obis-products-catalog-ckan-dev-1 \
  ckan -c /srv/app/ckan.ini obis sync-institutions
```

### Import from Zenodo

1. Get API token:
   ```bash
   docker exec obis-products-catalog-ckan-dev-1 \
     ckan -c /srv/app/ckan.ini user token list ckan_admin
   ```

2. Run harvest:
   ```bash
   docker exec obis-products-catalog-ckan-dev-1 bash -c \
     "cd /srv/app/src_extensions/ckanext-zenodo/ckanext/zenodo/scripts && \
      CKAN_API_TOKEN='YOUR_TOKEN' python3 harvest_zenodo.py"
   ```

---

## Testing

### Run CKAN Tests

```bash
docker exec obis-products-catalog-ckan-dev-1 \
  pytest --ckan-ini=/srv/app/ckan.ini /srv/app/src_extensions/
```

### Test JSON-LD Export

```bash
curl http://localhost:5000/dataset/test-dataset/odis.jsonld | python3 -m json.tool
```

### Validate Schema.org

Use [Google's Rich Results Test](https://search.google.com/test/rich-results) to validate JSON-LD output.

---

## Deployment

### Production Setup

See the [Test Deployment Guide](https://github.com/iobis/obis-products-catalog/blob/main/Test_Deployment_README.md) for full deployment instructions.

**Key differences from development:**

1. Use production Dockerfile (not Dockerfile.dev)
2. Set strong secrets in `.env`
3. Configure SSL certificates
4. Set up backups
5. Configure monitoring

### Environment Variables

Critical settings in `.env`:

```bash
# Site configuration
CKAN_SITE_URL=https://products.obis.org

# Security (change these!)
CKAN___SECRET_KEY=<generate-strong-secret>
CKAN___BEAKER__SESSION__SECRET=<generate-strong-secret>

# Database passwords
POSTGRES_PASSWORD=<strong-password>
CKAN_DB_PASSWORD=<strong-password>

# Schema
CKAN___SCHEMING__DATASET_SCHEMAS=ckanext.zenodo:zenodo_schema.yaml
```

Generate secrets:
```bash
openssl rand -base64 32
```

---

## Architecture

### Core Stack

| Service | Purpose | Port |
|:--------|:--------|:-----|
| CKAN | Catalog application | 5000 |
| PostgreSQL | Database | 5432 |
| Solr | Search index | 8983 |
| Redis | Cache/sessions | 6379 |
| NGINX | Reverse proxy | 80/443 |
| DataPusher | Data loading | 8800 |

### Extensions

**ckanext-obis_theme** - UI/UX customization
- Homepage with statistics
- Enhanced dataset pages
- OBIS branding

**ckanext-odis** - JSON-LD export
- Schema.org compliance
- ODIS vocabulary extensions
- Endpoint: `/dataset/{id}/odis.jsonld`

**ckanext-zenodo** - Enhanced metadata
- Custom schema definition
- Product types and themes
- Zenodo integration

**ckanext-doi_import** - Automated import
- DOI-based harvesting
- Metadata mapping

---

## Contributing

### Code Style

- **Python:** Follow PEP 8
- **JavaScript:** Use ES6+
- **CSS:** Use BEM naming convention

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages
6. Push and create a PR

### Reporting Issues

Use [GitHub Issues](https://github.com/iobis/obis-products-catalog/issues) to report:
- Bugs
- Feature requests
- Documentation improvements

---

## Troubleshooting

### Container won't start

Check logs:
```bash
docker compose -f docker-compose.dev.yml logs ckan-dev
```

### Database connection errors

Ensure PostgreSQL is ready:
```bash
docker compose -f docker-compose.dev.yml ps
docker exec obis-products-catalog-db-1 pg_isready
```

### Extensions not loading

Check plugin configuration in `.env`:
```bash
CKAN__PLUGINS="envvars image_view text_view scheming_datasets obis_theme odis zenodo doi_import"
```

### Permission errors in src/

Fix permissions:
```bash
chmod -R 777 src/
docker compose -f docker-compose.dev.yml restart ckan-dev
```

---

## Resources

- [CKAN Documentation](https://docs.ckan.org/)
- [CKAN Extensions Tutorial](https://docs.ckan.org/en/latest/extensions/tutorial.html)
- [Schema.org Documentation](https://schema.org/)
- [ODIS Book](https://book.oceaninfohub.org/)

---

*For questions, contact [helpdesk@obis.org](mailto:helpdesk@obis.org)*