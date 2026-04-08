# How the Catalog is Organized

## OBIS Nodes (Organizations)

OBIS nodes are the regional and thematic nodes that form the OBIS network. In the catalog, each node is represented as an **Organization**. The OBIS Secretariat and OBIS Community are also represented as organizations.

Products are associated with the node that stewarded the underlying data. Node metadata is synchronized from the [OBIS API](https://api.obis.org/v3/node).

**Examples:** EurOBIS, Antarctic OBIS, Caribbean OBIS, Ocean Tracking Network

## OBIS Institutions (Groups)

Institutions are the research organizations, universities, and agencies that contribute data to OBIS and are registered in [Ocean Expert](https://oceanexpert.org/institutes). Each institution is represented as a **Group** in the catalog, enriched with data from Ocean Expert including contact information, location, and acronyms.

Products can be tagged with one or more institutions to show all contributors.

**Examples:** CSIRO National Collections, Flanders Marine Institute (VLIZ), Alfred Wegener Institute

## Nodes vs. Institutions

**Nodes** are the data stewardship entities — products are **owned by** nodes.

**Institutions** are the research entities that produce the data — products are **tagged with** institutions.

A publication analyzing Arctic fish distributions might be owned by `node-arctic-obis` and tagged with the University of Alaska Fairbanks and the Norwegian Polar Institute.

## Product Types

The catalog uses [Zenodo's resource type vocabulary](https://help.zenodo.org/docs/deposit/describe-records/resource-type/):

| Type | Description |
|---|---|
| **Dataset** | Derived, aggregated, or processed datasets |
| **Publication** | Peer-reviewed articles, reports, technical documents |
| **Software** | Code, applications, and tools |
| **Presentation** | Conference slides and webinar decks |
| **Poster** | Scientific posters |
| **Image** | Maps, visualizations, infographics |
| **Video** | Animated visualizations and educational content |
| **Lesson** | Educational materials and tutorials |
| **Other** | Products that don't fit the above categories |

## Thematic Areas

Products can be tagged with one or more thematic areas:

- Biodiversity
- Climate Change
- Ocean Acidification
- Marine Protected Areas
- eDNA
- Invasives
- Fisheries
- Pollution
- Coastal Management
- Deep Sea
- Coral Reefs
- Species Distribution
- Near-Realtime

To suggest new themes, contact [helpdesk@obis.org](mailto:helpdesk@obis.org).