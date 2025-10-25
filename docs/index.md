---
layout: default
title: OBIS Products Catalog
---

# OBIS Products Catalog

A comprehensive metadata catalog for ocean biodiversity data products built on CKAN 2.11.

## Quick Links

- [User Guide](user-guide.md)
- [API Documentation](api-docs.md)
- [Developer Guide](developer-guide.md)
- [GitHub Repository](https://github.com/iobis/obis-products-catalog)

## What is the OBIS Products Catalog?

The OBIS Products Catalog is a centralized metadata repository that helps users discover and access data products created from OBIS-mediated marine biodiversity data. As the OBIS network has grown, it became challenging to track the diverse products—from maps and models to publications and software—that researchers have created. This catalog provides a searchable, well-organized metadata registry with semantic web capabilities.

## Key Features

- **Centralized Discovery** - Find data products from across the OBIS network
- **Rich Metadata** - Enhanced schemas with author tracking, funding info, and spatial/temporal coverage
- **Semantic Web Ready** - JSON-LD export for machine-readable metadata
- **Linked Data** - Connections to OBIS nodes, institutions, and Ocean Expert
- **Multiple Product Types** - Datasets, publications, software, presentations, visualizations, and more

## Infrastructure at a Glance

**Core Stack:** CKAN 2.11, PostgreSQL, Solr, Redis, NGINX  
**Data Sources:** OBIS API, Ocean Expert API, Zenodo  
**Organizations:** 38 OBIS regional/thematic nodes  
**Institutions:** 668 OBIS institutions with enhanced metadata  
**API:** Full CKAN API v3 + custom JSON-LD endpoints

## Getting Started

New users should start with the [User Guide](user-guide.md) to understand how to search, browse, and use the catalog.

Developers interested in contributing or deploying their own instance should see the [Developer Guide](developer-guide.md).

For API access and integration, see the [API Documentation](api-docs.md).

## Community

The OBIS Products Catalog is developed and maintained by the [OBIS Products Coordination Group (PCG)](https://manual.obis.org/nodes.html#obis-products-coordination-group).

- **Meetings:** Every other month, open to the OBIS community
- **Contact:** [helpdesk@obis.org](mailto:helpdesk@obis.org)
- **Issues:** [GitHub Issues](https://github.com/iobis/obis-products-catalog/issues)

## License

This project is licensed under the GNU Affero General Public License (AGPL) v3.0.

---

*Last updated: October 2025*