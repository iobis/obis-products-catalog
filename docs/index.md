# OBIS Products Catalog

The OBIS Products Catalog is a metadata catalog that helps users discover and access data products created from OBIS-mediated marine biodiversity data, or designed to support the OBIS network. As the OBIS network has grown to encompass 38 regional and thematic nodes, it became challenging to track the diverse products — maps, models, training materials, visualizations, software, and presentations — that researchers have created. This catalog provides a searchable focal point for those products, and ensures their metadata are exposed to catalogs like ODIS for increased findability.

It is not a data repository — it stores metadata and links to products that live in other systems.

## Key Features

- **Centralized Discovery** — Find data products from across the OBIS network
- **Lightweight** — Metadata focused; links to products in their authoritative repositories
- **Semantic Web Ready** — JSON-LD export for machine-readable metadata and sharing with ODIS
- **Linked Data** — Connections to OBIS nodes, institutions, and Ocean Expert
- **Multiple Product Types** — Datasets, publications, software, presentations, visualizations, and more

## Infrastructure at a Glance

| Component | Description |
|:----------|:------------|
| **Core Stack** | CKAN 2.11, PostgreSQL, Solr, Redis, Nginx |
| **Data Sources** | OBIS API, Ocean Expert API, Zenodo |
| **Organizations** | 38 OBIS regional/thematic nodes |
| **Institutions** | 668+ Ocean Expert institutions |
| **API** | Full CKAN API v3 + custom JSON-LD endpoints |

## Documentation

- **[User Guide](user-guide.md)** — How to search, browse, and contribute products
- **[Theming & Aesthetics](theming.md)** — How to change colors, fonts, logos, and icons
- **[Architecture](architecture.md)** — How the system is built and how the pieces fit together
- **[Extensions](extensions.md)** — What each custom CKAN extension does
- **[Operations](operations.md)** — How to deploy, maintain, and troubleshoot
- **[Data Model](data-model.md)** — Dataset fields, vocabularies, and the data pipeline
- **[Contributing Code](contributing.md)** — Git workflow and development setup

## Community

The catalog is developed and maintained by the [OBIS Products Coordination Group (PCG)](https://manual.obis.org/nodes.html#obis-products-coordination-group), which coordinates data and information products that synthesize and generate new information from OBIS-hosted data.

- **Meetings:** Every other month, open to the OBIS community
- **Contact:** [helpdesk@obis.org](mailto:helpdesk@obis.org)
- **Issues:** [GitHub Issues](https://github.com/iobis/obis-products-catalog/issues)

## Repository

- **GitHub**: [iobis/obis-products-catalog](https://github.com/iobis/obis-products-catalog)
- **Active branch**: `prod-setup`
