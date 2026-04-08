# Searching Products

## Basic Search

Use the search bar at the top of any page to search across product titles, descriptions, author names, keywords, organizations, and institutions.

## Faceted Filtering

Narrow your results using filters on the left sidebar:

- **Product Type** - Filter by dataset, publication, software, etc.
- **Thematic Area** - Filter by conservation, climate change, etc.
- **Organization** - Filter by OBIS node
- **Institution** - Filter by research institution
- **Tags** - Filter by keywords
- **License** - Filter by usage rights

## Browse by Node or Institution

- Visit `/organization` to see all OBIS nodes and the products they steward
- Visit `/group` to see all OBIS institutions and their associated products

## Advanced Search

Use the CKAN API for programmatic access. See the [API Reference](/api-docs/) for full documentation.

```bash
# Search for datasets
curl "https://products.obis.org/api/3/action/package_search?q=biodiversity"

# Filter by product type
curl "https://products.obis.org/api/3/action/package_search?fq=vocab_product_type_tags:software"

# Get specific dataset
curl "https://products.obis.org/api/3/action/package_show?id=dataset-name"
```