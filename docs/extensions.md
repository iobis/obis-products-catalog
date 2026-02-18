# Extensions

The catalog uses seven custom CKAN extensions:

## ckanext-obis_theme

Visual theming for the OBIS look and feel. Overrides CKAN templates for the homepage, header, footer, and dataset pages. Provides template helpers for product type and thematic area stats.

**Plugin name**: `obis_theme`

## ckanext-obis_sync

OBIS data synchronization CLI commands. Syncs OBIS nodes as organizations and institutions as groups (with Ocean Expert enrichment).

**Plugin name**: `obis_sync`

**Commands**:

- `ckan obis sync-nodes` — Sync OBIS nodes as CKAN organizations
- `ckan obis sync-institutions` — Sync institutions as CKAN groups

## ckanext-odis_export

ODIS Schema.org JSON-LD export. Adds a `/dataset/<id>/odis.jsonld` endpoint to every dataset, transforming CKAN metadata to ODIS-compliant Schema.org JSON-LD.

**Plugin name**: `odis_export`

This is the primary output of the catalog — making curated metadata discoverable by ODIS.

## ckanext-zenodo

Schema definition and Zenodo-specific facets/indexing. Defines the dataset schema via `zenodo_schema.yaml`, provides custom validators and Solr indexing, and adds Product Type and Thematic Area facets.

**Plugin name**: `zenodo`

## ckanext-doi-import

Import datasets from DOIs (currently Zenodo). Provides a web UI for DOI import and an API endpoint for automated harvesting. Uses a mapper pattern — adding new sources requires writing one mapper file.

**Plugin name**: `doi_import`

## ckanext-public-edit

Authorization policy extension that enables cross-node curation. Any logged-in user can edit public datasets and create new datasets, but only organization admins can delete datasets or reassign a dataset to a different organization.

**Plugin name**: `public_edit`

**What it overrides**:

| Auth function | Default CKAN | With public_edit |
|---|---|---|
| `package_update` | Only org editors/admins | Any logged-in user (public datasets) |
| `package_create` | Only org members | Any logged-in user |
| `package_delete` | Org editors and admins | Org admins only |

**Organization field behavior**:

- When editing an existing dataset, non-admins see the owning organization as read-only text
- When creating a new dataset, users see a dropdown of their organizations (typically OBIS Community)
- Organization admins and sysadmins see the full dropdown and can reassign datasets

**Server-side protection**: Even if the UI is bypassed, the `before_dataset_update` hook silently reverts any unauthorized org changes.

!!! warning "Plugin load order"
    `public_edit` must be loaded **before** `scheming_datasets` in `CKAN__PLUGINS` so that its template override for the organization field takes effect.

## ckanext-oauth2-login

ORCID OAuth2 login for researchers. Allows users to sign in with their ORCID iD instead of a CKAN username and password. Only ORCID iDs on the approved whitelist can log in. Creates a CKAN account on first login and auto-assigns new users to the OBIS Community organization as editors.

**Plugin name**: `oauth2_login`

**Access control**: Login is restricted to ORCID iDs listed in `orcid_whitelist.txt` in the extension root. Unapproved users are shown a message to contact helpdesk@obis.org. See [Operations > User Management](operations.md#orcid-whitelist) for how to manage the whitelist.

**Key behaviors**:

- Whitelist checked after ORCID authentication, before account creation
- First-time approved users get a CKAN account and OBIS Community membership automatically
- Deleted users are reactivated on next login (remove from whitelist to block)
- Session handling mirrors CKAN's native login (session regeneration + CSRF token rotation)

**Routes**:

| Route | Purpose |
|---|---|
| `/oauth2/login/orcid` | Starts the ORCID login flow |
| `/oauth2/callback` | Handles the redirect back from ORCID |

**Template helpers**:

| Helper | Returns |
|---|---|
| `h.oauth2_login_orcid_enabled()` | `True` if ORCID client ID is configured |
| `h.oauth2_login_orcid_url()` | URL to start ORCID login |

**Required `.env` variables**:

```
CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID=APP-XXXXXXXXXXXXXXXX
CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CKANEXT__OAUTH2_LOGIN__REDIRECT_URI=https://your-domain/oauth2/callback
```
