# User Guide

This guide covers how to use the OBIS Products Catalog to discover, search, and contribute ocean biodiversity research products.

## Why This Catalog Exists

As the OBIS network has grown to encompass 38 regional and thematic nodes, with data published by thousands of institutions worldwide, researchers have created an incredible variety of data products from OBIS-mediated marine biodiversity data — scientific publications, interactive maps, statistical models, derived datasets, software tools, and educational materials.

These products were scattered across repositories and platforms, making them difficult to discover. The OBIS Products Coordination Group flagged this as an important challenge to address.

The catalog solves this by providing a centralized metadata registry that aggregates metadata from existing sources (like Zenodo), links to authoritative sources (OBIS nodes, Ocean Expert institutions), and exposes machine-readable metadata via JSON-LD for semantic web integration. This minimizes the maintenance burden on product creators while maximizing discoverability.

## Understanding the Data Model

The catalog organizes metadata using three main entities that reflect the OBIS organizational structure.

### OBIS Nodes (Organizations)

The 38 regional and thematic nodes that form the OBIS network — for example, EurOBIS, Antarctic OBIS, Caribbean OBIS, or the Ocean Tracking Network. Each node is represented as an **Organization** in the catalog, and products are associated with the node(s) that stewarded the underlying data. Node metadata is synchronized from the [OBIS API](https://api.obis.org/v3/node).

### Institutions (Groups)

The 668+ research institutions, universities, and organizations that contribute data to OBIS and are registered in [Ocean Expert](https://oceanexpert.org/institutes). Each institution is represented as a **Group** in the catalog. Institution metadata is enriched with data from Ocean Expert, including contact information, geographic location, institution type, and activities. Data sources: [OBIS API](https://api.obis.org/v3/institute) and [Ocean Expert API](https://oceanexpert.org/api/v1/institute/).

### How Nodes and Institutions Relate

**Nodes** (Organizations) are the data stewardship entities — they manage, curate, and publish datasets to OBIS. Products in the catalog are **owned by** nodes.

**Institutions** (Groups) are the research entities that produce the data and products. Products can be **tagged with** multiple institutions to show all contributors.

For example, a publication analyzing Arctic fish distributions might be owned by `node-arctic-obis` (the data steward) and tagged with University of Alaska Fairbanks and Norwegian Polar Institute (the research institutions).

## Product Types

The catalog uses [Zenodo's resource type vocabulary](https://help.zenodo.org/docs/deposit/describe-records/resource-type/), based on the DataCite ResourceType standard:

| Type | Description | Examples |
|---|---|---|
| **Dataset** | Derived, aggregated, or processed data | Species distribution models, gridded biodiversity products |
| **Publication** | Peer-reviewed articles and reports | Journal articles, technical reports, book chapters |
| **Software** | Code, applications, and tools | R packages, Python libraries, web dashboards |
| **Presentation** | Conference slides and talks | Webinar decks, workshop materials |
| **Poster** | Scientific posters | Conference posters |
| **Image** | Maps, visualizations, infographics | Distribution maps, biodiversity heatmaps |
| **Video** | Animations and multimedia | Animated distribution changes, tutorials |
| **Lesson** | Educational and training materials | Training modules, online courses |
| **Other** | Anything that doesn't fit above | Interactive web experiences, data management plans |

## Thematic Areas

Products can be tagged with thematic areas describing their scientific domain:

Biodiversity, Climate Change, Ocean Acidification, Marine Protected Areas, eDNA, Invasive Species, Fisheries, Pollution, Coastal Management, Deep Sea, Coral Reefs, Species Distribution.

To suggest new themes, contact [helpdesk@obis.org](mailto:helpdesk@obis.org).

## Searching and Browsing

### Basic Search

Use the search bar at the top of any page to search across product titles, descriptions, author names, keywords, organizations, and institutions.

### Faceted Filtering

Narrow results using the sidebar filters: Product Type, Thematic Area, Organization (OBIS node), Institution, Tags, and License.

### Browse by Organization or Institution

Visit `/organization` to see all OBIS nodes, or `/group` to see all institutions and their associated products.

### API Access

The catalog provides full CKAN API v3 access for programmatic queries:

```bash
# Search for products
curl "https://products.obis.org/api/3/action/package_search?q=biodiversity"

# Filter by product type
curl "https://products.obis.org/api/3/action/package_search?fq=product_type:publication"

# Get a specific dataset
curl "https://products.obis.org/api/3/action/package_show?id=dataset-name"
```

## Contributing Products

### Recommended: Publish to Zenodo First

We recommend publishing products to [Zenodo](https://zenodo.org) first, then importing to the catalog. Zenodo provides a permanent DOI, long-term preservation, and a single place to maintain metadata. The import process pulls metadata automatically.

To add your product:

1. Create an account on Zenodo and upload your product
2. Obtain the DOI
3. Contact [helpdesk@obis.org](mailto:helpdesk@obis.org) to add your DOI to the harvest registry

### Metadata Best Practices

When creating product metadata:

- **Use ORCID** for author identification
- **Include spatial coverage** (bounding box or place names)
- **Specify temporal coverage** (time period of data used)
- **Add keywords** relevant to marine biodiversity
- **Choose an appropriate license** (we recommend CC-BY or CC0 for data)
- **Link to source datasets** when possible
- **Include funding information** to acknowledge support

### Required Metadata

At minimum, products should include: title, description, author(s), publication date, product type, license, and a persistent identifier (DOI preferred).

## Getting Help

- **Email:** [helpdesk@obis.org](mailto:helpdesk@obis.org)
- **GitHub Issues:** [Report bugs or request features](https://github.com/iobis/obis-products-catalog/issues)
- **OBIS Manual:** [manual.obis.org](https://manual.obis.org/)
