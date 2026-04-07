*Documentation last built: {{BUILD_DATE}}*

## What is the OBIS Products Catalog?

The OBIS Products Catalog is a metadata catalog that helps users discover and access data products created from OBIS-mediated data. As the OBIS network has grown, it became challenging to track the diverse products, like maps, models, tools, infographics, etc. that researchers have created. This catalog provides a searchable focal point for the products, and also ensures the metadata are exposed to catalogs like ODIS for increased findability.

## Key Features

> **Centralized Discovery** - Find data products from across the OBIS network
>
> **Lightweight** - Focuses metadata focused across multiple repositories without manipulation
>
> **Semantic Web Ready** - JSON-LD export for machine-readable metadata and sharing with ODIS
>
> **Linked Data** - Connections to OBIS nodes, institutions, and Ocean Expert
>
> **Multiple Product Types** - Datasets, publications, software, presentations, visualizations, and more

## Infrastructure at a Glance

| Component | Description |
|:----------|:------------|
| **Core Stack** | CKAN 2.11, PostgreSQL, Solr, Redis, NGINX |
| **Data Sources** | OBIS API, Ocean Expert API, Zenodo |
| **Organizations** | OBIS regional/thematic nodes |
| **Institutions** | Ocean Expert Institutions |
| **API** | Full CKAN API v3 + custom JSON-LD endpoints |
| **Docs** | MkDocs Material, served via NGINX |

## Community

The OBIS Products Catalog is developed and maintained by the [OBIS Products Coordination Group (PCG)](https://manual.obis.org/nodes.html#obis-products-coordination-group).

- **Meetings:** Every other month, open to the OBIS community
- **Contact:** [helpdesk@obis.org](mailto:helpdesk@obis.org)
- **Issues:** [GitHub Issues](https://github.com/iobis/obis-products-catalog/issues)

---