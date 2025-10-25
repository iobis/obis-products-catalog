---
layout: default
title: API Documentation
nav_order: 3
---

# API Documentation
{: .no_toc }

Access the OBIS Products Catalog programmatically.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The OBIS Products Catalog provides two API interfaces:

1. **CKAN API v3** - Full REST API for catalog operations
2. **JSON-LD Endpoints** - Schema.org-compliant metadata export

---

## CKAN API v3

### Base URL

```
https://products.obis.org/api/3/action/
```

### Authentication

Most read operations don't require authentication. For write operations, include an API token:

```bash
curl -H "Authorization: YOUR_API_TOKEN" \
  https://products.obis.org/api/3/action/package_create
```

### Common Endpoints

#### Search Datasets

```bash
# Basic search
curl "https://products.obis.org/api/3/action/package_search?q=biodiversity"

# Filter by product type
curl "https://products.obis.org/api/3/action/package_search?fq=product_type:publication"

# Faceted search
curl "https://products.obis.org/api/3/action/package_search?facet.field=[\"product_type\",\"organization\"]"
```

#### Get Dataset Details

```bash
curl "https://products.obis.org/api/3/action/package_show?id=dataset-name"
```

#### List Organizations

```bash
curl "https://products.obis.org/api/3/action/organization_list?all_fields=true"
```

#### List Groups (Institutions)

```bash
curl "https://products.obis.org/api/3/action/group_list?all_fields=true"
```

### Response Format

All responses are JSON with this structure:

```json
{
  "help": "API endpoint documentation URL",
  "success": true,
  "result": { ... }
}
```

---

## JSON-LD Endpoints

### Get Dataset as JSON-LD

Every dataset has a JSON-LD endpoint:

```
https://products.obis.org/dataset/{dataset-name}/odis.jsonld
```

**Example:**

```bash
curl -H "Accept: application/ld+json" \
  https://products.obis.org/dataset/arctic-biodiversity/odis.jsonld
```

### Schema

The JSON-LD follows Schema.org vocabulary with ODIS extensions:

- Base type: `schema:Dataset`, `schema:ScholarlyArticle`, or `schema:SoftwareSourceCode`
- Properties: title, description, creator, datePublished, spatialCoverage, etc.
- ODIS extensions: marine-specific properties

---

## Code Examples

### Python

```python
import requests

# Search for datasets
response = requests.get(
    'https://products.obis.org/api/3/action/package_search',
    params={'q': 'biodiversity', 'rows': 10}
)
data = response.json()
datasets = data['result']['results']

# Get JSON-LD
response = requests.get(
    'https://products.obis.org/dataset/dataset-name/odis.jsonld',
    headers={'Accept': 'application/ld+json'}
)
jsonld = response.json()
```

### R

```r
library(httr)
library(jsonlite)

# Search for datasets
response <- GET(
  "https://products.obis.org/api/3/action/package_search",
  query = list(q = "biodiversity", rows = 10)
)
data <- fromJSON(content(response, "text"))
datasets <- data$result$results
```

### JavaScript

```javascript
// Search for datasets
fetch('https://products.obis.org/api/3/action/package_search?q=biodiversity')
  .then(response => response.json())
  .then(data => {
    const datasets = data.result.results;
    console.log(datasets);
  });

// Get JSON-LD
fetch('https://products.obis.org/dataset/dataset-name/odis.jsonld', {
  headers: { 'Accept': 'application/ld+json' }
})
  .then(response => response.json())
  .then(jsonld => console.log(jsonld));
```

---

## Rate Limits

Current rate limits:
- **Anonymous users:** 60 requests per minute
- **Authenticated users:** 600 requests per minute

For bulk operations or harvesting, please contact [helpdesk@obis.org](mailto:helpdesk@obis.org).

---

## Full API Documentation

For complete CKAN API documentation, see:
- [CKAN API Guide](https://docs.ckan.org/en/latest/api/)
- [CKAN Action API Reference](https://docs.ckan.org/en/latest/api/index.html#action-api-reference)

---

*For questions or issues, contact [helpdesk@obis.org](mailto:helpdesk@obis.org)*