# ckanext-oauth2-login

**ORCID OAuth2 login for CKAN.** Lets researchers sign in with their ORCID iD.

This extension was built for the OBIS Products Catalog. It replaces the unmaintained `ckanext-oauth2` extensions with a focused, minimal implementation that does one thing: lets users log in via ORCID.

## What it does

1. Adds a "Sign in with ORCID" button to the CKAN login page
2. Handles the OAuth2 authorization code flow with ORCID
3. Creates a CKAN user account on first login (username: `orcid-XXXX-XXXX-XXXX-XXXX`)
4. Logs the user into CKAN on subsequent visits
5. Stores the ORCID iD in user `plugin_extras` for future use (e.g., auto-linking as author)

## What it doesn't do

- No API token management or delegation (this is login only)
- No GitHub, Google, or other providers (ORCID is the only provider for now)
- No role assignment (use `ckanext-public-edit` for cross-org editing, or manually assign org roles)

## Requirements

- CKAN 2.10+ (uses Flask-Login)
- HTTPS in production (required by ORCID for redirect URIs)
- An ORCID OAuth application (register at https://orcid.org/developer-tools)

## Setup

### 1. Register an ORCID OAuth application

**For testing** (sandbox): https://sandbox.orcid.org/developer-tools
**For production**: https://orcid.org/developer-tools

Set the redirect URI to: `https://your-catalog-domain/oauth2/callback`

### 2. Add to `.env`

```bash
# Add oauth2_login to your plugins list
CKAN__PLUGINS=envvars ... oauth2_login ...

# ORCID OAuth credentials
CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID=APP-XXXXXXXXXXXXXXXX
CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CKANEXT__OAUTH2_LOGIN__REDIRECT_URI=https://your-catalog-domain/oauth2/callback

# Optional: use sandbox for testing (defaults to production)
# CKANEXT__OAUTH2_LOGIN__ORCID_BASE_URL=https://sandbox.orcid.org
```

Note: The triple-underscore convention applies here. `CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID` maps to `ckanext.oauth2_login.orcid_client_id` in CKAN config.

### 3. Build and restart

```bash
docker compose build ckan && docker compose up -d
```

## How it works

```
User clicks "Sign in with ORCID"
  → GET /oauth2/login/orcid
  → Redirect to orcid.org/oauth/authorize
  → User signs in at ORCID
  → ORCID redirects to /oauth2/callback?code=...&state=...
  → Extension exchanges code for token (gets ORCID iD + name)
  → Extension creates/finds CKAN user
  → User is logged into CKAN
  → Redirect to original page
```

## Routes

| Route | Purpose |
|---|---|
| `/oauth2/login/orcid` | Starts the ORCID login flow |
| `/oauth2/callback` | Handles the redirect back from ORCID |

## Template helpers

| Helper | Returns |
|---|---|
| `h.oauth2_login_orcid_enabled()` | `True` if ORCID client ID is configured |
| `h.oauth2_login_orcid_url()` | URL to start ORCID login (`/oauth2/login/orcid`) |

## User accounts

Users created via ORCID login:
- Username: `orcid-0000-0002-1825-0097` (derived from ORCID iD)
- Full name: from ORCID profile
- Email: from ORCID userinfo endpoint (if available)
- Password: random (cannot be used — ORCID is the only login method)
- `plugin_extras.oauth2_login.orcid_id`: the raw ORCID iD
- `plugin_extras.oauth2_login.provider`: `"orcid"`

## Security

- **CSRF protection**: State parameter in OAuth flow, verified on callback
- **No client secret in browser**: All token exchange happens server-side
- **Random passwords**: OAuth users cannot log in via username/password

## Adding more providers (future)

The extension is structured so that additional providers could be added by:
1. Adding new routes (`/oauth2/login/<provider>`)
2. Adding provider-specific config and endpoint URLs
3. Updating `_find_or_create_user` to handle the new provider

But for the OBIS Products Catalog, ORCID is likely sufficient.
