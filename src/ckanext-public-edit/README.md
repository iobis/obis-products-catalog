# ckanext-public-edit

**Policy: Any logged-in user can edit any public dataset. No one except org admins can delete.**

This is a standalone authorization extension for the OBIS Products Catalog. It overrides three CKAN auth functions:

| Auth function | Default CKAN behavior | This extension |
|---|---|---|
| `package_update` | Only org editors/admins | Any logged-in user (public datasets) |
| `package_create` | Only org members | Any logged-in user |
| `package_delete` | Org editors and admins | Org admins only |

For **private datasets**, the default org-based permission check still applies — only editors/admins of the owning organization can edit them.

## Why

The OBIS Products Catalog is a shared curation space. Researchers need to annotate datasets across all OBIS nodes — adding thematic tags, linking institutions, updating metadata — regardless of which node owns the dataset. Standard CKAN org-based permissions prevent this.

## Enable

Add `public_edit` to `CKAN__PLUGINS` in your `.env`:

```
CKAN__PLUGINS=envvars ... public_edit ...
```

Then rebuild and restart:

```bash
docker compose build ckan && docker compose up -d
```

## Disable

Remove `public_edit` from `CKAN__PLUGINS`. Default CKAN org-based permissions resume immediately.

## Sysadmins

Sysadmins bypass all auth checks (this is standard CKAN behavior, not something this extension changes).
