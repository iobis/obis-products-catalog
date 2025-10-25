---
layout: default
title: User Guide
nav_order: 2
has_children: false
---

# User Guide
{: .no_toc }

A comprehensive guide to using the OBIS Products Catalog.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Why We Created This Catalog

### The Challenge

As the Ocean Biodiversity Information System (OBIS) network has grown to encompass 38 regional and thematic nodes and 668 institutions worldwide, researchers have created an incredible variety of data products from OBIS-mediated marine biodiversity data. These products include:

- Scientific publications and reports
- Interactive maps and dashboards
- Statistical models and analyses
- Data visualizations and infographics
- Derived and aggregated datasets
- Software tools and applications
- Educational materials

However, these products were scattered across institutional repositories, personal websites, and various data platforms, making it difficult for the community to discover and access them.

### The Solution

The OBIS Products Catalog provides a **centralized metadata registry** that serves as a focal point for discovering OBIS-related data products. Rather than requiring researchers to maintain metadata in multiple places, the catalog:

- **Aggregates metadata** from existing sources (Zenodo, institutional repositories)
- **Links to authoritative sources** (OBIS nodes, Ocean Expert institutions)
- **Exposes machine-readable metadata** via JSON-LD for semantic web integration
- **Provides a unified search interface** with faceted filtering

This approach minimizes the maintenance burden on product creators while maximizing discoverability.

### Community Governance

The catalog is developed and maintained by the **OBIS Products Coordination Group (PCG)**, which coordinates data and information products that synthesize and generate new information from OBIS-hosted data. The PCG meets bimonthly and welcomes participation from the OBIS community.

For more information, see the [OBIS Manual](https://manual.obis.org/nodes.html#obis-products-coordination-group) or contact [helpdesk@obis.org](mailto:helpdesk@obis.org).

---

## Understanding the Data Model

The catalog organizes metadata using three main entities that reflect the OBIS organizational structure:

### OBIS Nodes (Organizations)

**What they are:** The 38 regional and thematic nodes that form the OBIS network.

**Examples:**
- OBIS USA
- EurOBIS (European node)
- Antarctic OBIS
- Caribbean OBIS
- Ocean Tracking Network (OTN)

**How they work in the catalog:**
- Each node is represented as an **Organization** in CKAN
- Products are associated with the node(s) that stewarded the underlying data
- Node metadata is synchronized from the OBIS API
- Organizations are prefixed with `node-` (e.g., `node-obis-usa`) to avoid naming conflicts

**Data Source:** [https://api.obis.org/v3/node](https://api.obis.org/v3/node)

### OBIS Institutions (Groups)

**What they are:** The 668+ research institutions, universities, and organizations that contribute data to OBIS.

**Examples:**
- CSIRO National Collections
- Flanders Marine Institute (VLIZ)
- Ocean Tracking Network
- Alfred Wegener Institute

**How they work in the catalog:**
- Each institution is represented as a **Group** in CKAN
- Products can be tagged with relevant institutions
- Institution metadata is enriched with data from Ocean Expert, including:
  - Contact information (email, phone, address)
  - Geographic location and region
  - Institution type and activities
  - Website and social media links
  - Acronyms and alternative names

**Data Sources:** 
- [https://api.obis.org/v3/institute](https://api.obis.org/v3/institute)
- [https://oceanexpert.org/api/v1/institute/](https://oceanexpert.org/api/v1/institute/)

**Data Quality Indicators:**
- `ocean_expert_full` - Complete Ocean Expert metadata retrieved
- `ocean_expert_partial` - Partial Ocean Expert data available
- `obis_only` - Only OBIS data available (Ocean Expert unavailable)

### Relationship Between Nodes and Institutions

**Nodes** (Organizations) are the data stewardship entities—they manage, curate, and publish datasets to OBIS. Products in the catalog are **owned by** nodes.

**Institutions** (Groups) are the research entities that produce the data and products. Products can be **tagged with** multiple institutions to show all contributors.

**Example:** A publication analyzing Arctic fish distributions might be:
- **Owned by:** node-arctic-obis (the steward of Arctic data)
- **Tagged with:** University of Alaska Fairbanks, Norwegian Polar Institute (the research institutions)

This structure mirrors how OBIS itself organizes data and reflects real-world collaborations.

---

## Product Types

The catalog uses [Zenodo's resource type vocabulary](https://help.zenodo.org/docs/deposit/describe-records/resource-type/), which is based on DataCite's ResourceType standard. Products are classified into nine main types:

### Dataset
**Description:** Derived, aggregated, or processed datasets created from OBIS data.

**Examples:**
- Species distribution models
- Aggregated occurrence data for a specific region or taxon
- Gridded biodiversity data products
- Quality-controlled subsets of OBIS data

### Publication
**Description:** Peer-reviewed articles, research reports, and technical documents.

**Examples:**
- Journal articles citing OBIS data
- Technical reports on biodiversity assessments
- Book chapters on marine biodiversity
- Conference papers

### Software
**Description:** Code, applications, and tools for analyzing or visualizing OBIS data.

**Examples:**
- R packages for OBIS data access
- Python libraries for biodiversity analysis
- Web applications and dashboards
- Analysis scripts and workflows

### Presentation
**Description:** Slides and materials from conference presentations and talks.

**Examples:**
- Conference presentations
- Webinar slide decks
- Workshop materials

### Poster
**Description:** Scientific posters presented at conferences and meetings.

**Examples:**
- Conference posters
- Poster presentations at workshops

### Image
**Description:** Maps, visualizations, infographics, and other visual products.

**Examples:**
- Distribution maps
- Biodiversity heatmaps
- Infographics on marine species
- Data visualization galleries

### Video
**Description:** Animated visualizations, educational videos, and multimedia content.

**Examples:**
- Animated species distribution changes over time
- Educational videos about OBIS data
- Video tutorials

### Lesson
**Description:** Educational materials, tutorials, and training resources.

**Examples:**
- Training materials for OBIS data use
- Educational modules
- Online courses featuring OBIS data

### Other
**Description:** Products that don't fit the above categories.

**Examples:**
- Interactive web experiences
- Data management plans
- Citizen science projects

### Why These Categories?

This classification system:
- **Aligns with international standards** (DataCite)
- **Matches Zenodo**, making import seamless
- **Covers the full spectrum** of OBIS-related outputs
- **Is recognized** by research communities and indexing services

---

## Thematic Areas

Products can be tagged with thematic areas that describe the scientific domains or applications:

### Current Themes

- **Biodiversity Assessment** - Species richness, diversity indices, community composition
- **Climate Change** - Climate impacts on marine life, range shifts, phenology
- **Conservation Planning** - Protected area design, threat assessment, priority setting
- **Ecosystem Health** - Indicators, monitoring, environmental quality
- **Fisheries Management** - Stock assessment, bycatch, sustainable fishing
- **Invasive Species** - Non-native species distribution, impacts, management
- **Ocean Acidification** - pH impacts on marine organisms
- **Pollution** - Marine debris, chemical contaminants, impacts
- **Species Distribution** - Range maps, ecological niche models, habitat suitability

### Adding New Themes

Themes are managed as CKAN vocabulary tags and can be expanded by the community. To suggest new themes, contact [helpdesk@obis.org](mailto:helpdesk@obis.org).

---

## JSON-LD and Semantic Web

### What is JSON-LD?

JSON-LD (JavaScript Object Notation for Linked Data) is a method of encoding linked data using JSON. It allows the catalog to expose metadata in a format that machines can understand and reason about.

### Why It Matters

**For researchers:**
- Your products become part of the semantic web
- Metadata can be automatically harvested by search engines and discovery services
- Links between products, datasets, and researchers are machine-readable

**For the community:**
- Enables automated aggregation of OBIS products across platforms
- Facilitates integration with other marine data infrastructures (e.g., ODIS, EDMO)
- Supports FAIR principles (Findable, Accessible, Interoperable, Reusable)

### How It Works

Every dataset in the catalog has a JSON-LD endpoint that follows the [Schema.org](https://schema.org) vocabulary with ODIS extensions:

**Endpoint format:**
```
https://products.obis.org/dataset/{dataset-name}/odis.jsonld
```

**Example:**
```
https://products.obis.org/dataset/arctic-fish-distributions/odis.jsonld
```

### What's Included in JSON-LD

The JSON-LD export includes:

- **Basic metadata:** Title, description, keywords, publication date
- **Authors and contributors:** Names, affiliations, ORCID identifiers
- **Organizations:** ROR identifiers for institutional affiliations
- **Identifiers:** DOI, URLs, canonical identifiers
- **Spatial coverage:** Geographic bounding boxes, place names
- **Temporal coverage:** Time periods covered by the product
- **Funding:** Grant information and funding agencies
- **Related resources:** Citations, source datasets, derived products

### Schema.org + ODIS

The catalog uses [Schema.org](https://schema.org) as the base vocabulary (widely recognized by search engines like Google Scholar) and extends it with [ODIS (Ocean Data and Information System)](https://book.oceaninfohub.org/) properties for marine-specific metadata.

**Standard Schema.org types used:**
- `Dataset` - For data products
- `ScholarlyArticle` - For publications
- `SoftwareSourceCode` - For software
- `CreativeWork` - For other products

**ODIS extensions include:**
- Marine ecosystem types
- Ocean regions and features
- Oceanographic parameters
- Marine species identifiers

### Using JSON-LD

**For web developers:**
```html
<script type="application/ld+json">
  <!-- Embed JSON-LD in your web page -->
</script>
```

**For harvesters:**
```bash
curl -H "Accept: application/ld+json" \
  https://products.obis.org/dataset/dataset-name/odis.jsonld
```

**For validation:**
- [Google Rich Results Test](https://search.google.com/test/rich-results)
- [Schema.org Validator](https://validator.schema.org/)

---

## Searching and Browsing

### Basic Search

Use the search bar at the top of any page to search across:
- Product titles
- Descriptions
- Author names
- Keywords
- Organizations and institutions

### Faceted Filtering

Narrow your results using filters on the left sidebar:

- **Product Type** - Filter by dataset, publication, software, etc.
- **Thematic Area** - Filter by conservation, climate change, etc.
- **Organization** - Filter by OBIS node
- **Institution** - Filter by research institution
- **Tags** - Filter by keywords
- **License** - Filter by usage rights

### Browse by Organization

Visit `/organization` to see all OBIS nodes and the products they steward.

### Browse by Institution

Visit `/group` to see all OBIS institutions and their associated products.

### Advanced Search

Use the CKAN API for programmatic access:

```bash
# Search for datasets
curl "https://products.obis.org/api/3/action/package_search?q=biodiversity"

# Filter by product type
curl "https://products.obis.org/api/3/action/package_search?fq=product_type:publication"

# Get specific dataset
curl "https://products.obis.org/api/3/action/package_show?id=dataset-name"
```

---

## Contributing Products

### Ways to Contribute

1. **Zenodo Import** - Add your DOI to the harvest registry
2. **Direct Entry** - Create a record directly in the catalog
3. **API Upload** - Use the CKAN API to batch upload products

### Recommended: Use Zenodo

We recommend publishing products to [Zenodo](https://zenodo.org) first, then importing to the catalog:

**Benefits:**
- Zenodo provides a permanent DOI
- Metadata is maintained in one place
- Automatic updates when you revise on Zenodo
- Zenodo provides long-term preservation

**Process:**
1. Create account on Zenodo
2. Upload your product and fill in metadata
3. Obtain the DOI
4. Contact [helpdesk@obis.org](mailto:helpdesk@obis.org) to add your DOI to the harvest registry

### Metadata Best Practices

When creating product metadata:

- **Use ORCID** for author identification
- **Include spatial coverage** (bounding box or place names)
- **Specify temporal coverage** (time period of data used)
- **Add keywords** relevant to marine biodiversity
- **Choose appropriate license** (we recommend CC-BY or CC0 for data)
- **Link to source datasets** when possible
- **Include funding information** to acknowledge support

### Required Metadata

At minimum, products should include:

- Title
- Description
- Author(s)
- Publication date
- Product type
- License
- Identifier (DOI preferred)

---

## Getting Help

- **Email:** [helpdesk@obis.org](mailto:helpdesk@obis.org)
- **GitHub Issues:** [Report bugs or request features](https://github.com/iobis/obis-products-catalog/issues)
- **OBIS Manual:** [Read the documentation](https://manual.obis.org/)

---

*This user guide is maintained by the OBIS Products Coordination Group. Last updated: October 2025.*