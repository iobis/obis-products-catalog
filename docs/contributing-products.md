# Contributing Products

## Ways to Contribute

1. **Zenodo Import** — Import a product from its DOI (recommended)
2. **Direct Entry** — Create a record directly in the catalog

Both methods are available to any logged-in user.

## Recommended: Use Zenodo

We recommend publishing products to [Zenodo](https://zenodo.org) first, then importing to the catalog.

**Benefits:**

- Zenodo provides a permanent DOI
- Metadata is maintained in one place
- Automatic updates when you revise on Zenodo
- Zenodo provides long-term preservation

**Process:**

1. Create an account on Zenodo
2. Upload your product and fill in metadata
3. Obtain the DOI
4. Log in to the catalog and use the DOI import form, or contact [helpdesk@obis.org](mailto:helpdesk@obis.org) to add your DOI to the harvest registry

## Importing from a DOI

1. Sign in with your ORCID
2. Click "Add Product" and choose "Import from DOI"
3. Paste the DOI URL (e.g., `https://doi.org/10.5281/zenodo.11464531`)
4. Select the owning organization (OBIS node)
5. Optionally select contributing institutions
6. Click Import

The system fetches metadata from Zenodo automatically — title, description, authors, files, and license.

**Re-importing a DOI**: If the product already exists in the catalog, it will be updated from the source. Curated fields (organization, tags, thematic areas, contributing institutions) are preserved. You'll see a yellow notice confirming this.

**Blacklisted DOIs**: Some DOIs have been reviewed and excluded from the catalog. If you try to import one, you'll see a warning with the reason. Contact [helpdesk@obis.org](mailto:helpdesk@obis.org) if you believe this is an error.

## Editing Existing Products

Any logged-in user can edit the metadata of any public product in the catalog. Common curation tasks include:

- Adding or correcting **thematic area** tags
- Linking products to the correct **institutions**
- Improving **descriptions** and **titles**
- Adding **spatial coverage** information
- Correcting **author** information

When editing, the product remains under its original owning organization — your edits will not change which OBIS node owns the product.

## Metadata Best Practices

**Required fields:**

- Title
- Description
- Author(s)
- Publication date
- Product type
- License
- Identifier (DOI preferred)

**Recommended:**

- Use ORCID for author identification
- Include spatial coverage (bounding box or place names)
- Specify temporal coverage (time period of data used)
- Add keywords relevant to marine biodiversity
- Choose an open license (CC-BY or CC0 recommended)
- Link to source datasets when possible
- Include funding information

**A note on licenses:** The catalog displays licenses grouped by usage constraints (Public Domain, Open (Attribution required), etc.) rather than by license name. License strings are imported automatically from the source repository. If a product shows as "Unclassified" in the license filter, the license is recorded but hasn't been mapped yet — contact helpdesk@obis.org to report it.

## Catalog Manifest

The catalog maintains a version-controlled record of all products:

- **`catalog_whitelist.csv`** — Exported nightly from the database. Contains DOI, title, source URL, and catalog URL for every product.
- **`catalog_blacklist.csv`** — Manually curated list of DOIs that have been reviewed and excluded. Contact [helpdesk@obis.org](mailto:helpdesk@obis.org) to request additions or removals.