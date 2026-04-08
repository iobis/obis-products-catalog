# encoding: utf-8
"""
ckanext-oauth2-login

ORCID OAuth2 login for CKAN. Lets researchers sign in with their ORCID iD.

Flow:
1. User clicks "Sign in with ORCID" → redirected to ORCID authorization page
2. User authorizes → ORCID redirects back with an authorization code
3. Extension exchanges code for access token + ORCID iD
4. Extension checks ORCID iD against whitelist
5. Extension creates or finds a matching CKAN user, logs them in
6. Extension applies roles from whitelist (sysadmin, org admin) — on every login

Whitelist format: <orcid> [role1|role2|...] # comment
  sysadmin              → full system access (org role logic skipped)
  <org-name>            → admin capacity in that org (e.g. node-obis-uk)
  (no role)             → regular editor, added to obis-community on first login

Roles are re-applied on every login, including demotions.

Profile edit flow for ORCID users:
1. User submits profile edit form → intercepted by /user/edit-orcid/<id>
2. Form data saved to session
3. User redirected through ORCID OAuth to confirm identity
4. Callback verifies ORCID iD matches logged-in user
5. Profile update applied via user_update with ignore_auth
6. User redirected to their profile page

Requires these .env variables:
    CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID
    CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_SECRET
    CKANEXT__OAUTH2_LOGIN__REDIRECT_URI

Optional (defaults to production ORCID):
    CKANEXT__OAUTH2_LOGIN__ORCID_BASE_URL   (use https://sandbox.orcid.org for testing)
"""

import logging
import os
import secrets

import requests as http_requests
from flask import Blueprint, redirect, request, session

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _config(key, default=None):
    """Read a plugin config value from CKAN config."""
    return toolkit.config.get(f'ckanext.oauth2_login.{key}', default)


def _orcid_base_url():
    return _config('orcid_base_url', 'https://orcid.org')


def _orcid_api_url():
    """API base URL (for userinfo). Matches the base URL environment."""
    base = _orcid_base_url()
    if 'sandbox' in base:
        return 'https://sandbox.orcid.org'
    return 'https://orcid.org'


# ---------------------------------------------------------------------------
# ORCID OAuth endpoints
# ---------------------------------------------------------------------------

def _authorize_url():
    return f'{_orcid_base_url()}/oauth/authorize'


def _token_url():
    return f'{_orcid_base_url()}/oauth/token'


def _userinfo_url():
    return f'{_orcid_api_url()}/oauth/userinfo'


# ---------------------------------------------------------------------------
# Whitelist
# ---------------------------------------------------------------------------

_whitelist_cache = None


def _load_whitelist():
    """Load approved ORCID iDs and their roles from the whitelist file.

    Format per line: <orcid> [role1|role2|...] # comment
      - sysadmin: full system access
      - <org-name>: admin capacity in that org
      - (no role): regular editor

    Returns a dict mapping ORCID iD strings to a list of role strings.
    e.g. {
        '0000-0001-7418-1244': ['sysadmin'],
        '0000-0002-5806-0837': ['node-obis-uk'],
        '0000-0003-2807-5867': ['node-ocean-tracking-network', 'node-eurobis'],
        '0000-0002-1234-5678': [],
    }
    """
    global _whitelist_cache
    if _whitelist_cache is not None:
        return _whitelist_cache

    custom_path = _config('whitelist_path')
    ext_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        custom_path,
        os.path.join(ext_dir, '..', '..', 'orcid_whitelist.txt'),
        '/srv/app/orcid_whitelist.txt',
    ]

    whitelist = {}
    for path in candidates:
        if path and os.path.isfile(path):
            log.info(f'Loading ORCID whitelist from: {path}')
            with open(path, 'r') as f:
                for line in f:
                    # Strip comments
                    line = line.split('#')[0].strip()
                    if not line:
                        continue
                    parts = line.split()
                    orcid_id = parts[0]
                    # Second token (if present) is pipe-delimited roles
                    if len(parts) >= 2:
                        roles = parts[1].split('|')
                    else:
                        roles = []
                    whitelist[orcid_id] = roles
            log.info(f'Loaded {len(whitelist)} approved ORCID iDs')
            _whitelist_cache = whitelist
            return whitelist

    log.warning('No ORCID whitelist file found — all ORCID logins will be rejected')
    _whitelist_cache = whitelist
    return whitelist


def _is_orcid_approved(orcid_id):
    """Check if an ORCID iD is on the approved whitelist."""
    return orcid_id in _load_whitelist()


def _get_roles(orcid_id):
    """Return the list of roles for an ORCID iD. Empty list = regular editor."""
    return _load_whitelist().get(orcid_id, [])


def reload_whitelist():
    """Force reload of the whitelist (e.g. after editing the file)."""
    global _whitelist_cache
    _whitelist_cache = None
    return _load_whitelist()


# ---------------------------------------------------------------------------
# Role application
# ---------------------------------------------------------------------------

def _apply_roles(orcid_id, username):
    """Apply (or revoke) roles for a user based on the whitelist.

    Called on every login so whitelist changes propagate without manual
    shell intervention. Handles:
    - sysadmin promotion and demotion
    - org admin promotion and demotion (per org, for non-sysadmins only)

    Sysadmins are skipped for org-level role logic entirely — they have
    implicit access everywhere and querying their org memberships causes
    spurious editor assignments.
    """
    roles = _get_roles(orcid_id)
    userobj = model.User.by_name(username)
    if not userobj:
        log.error(f'Cannot apply roles: user {username} not found')
        return

    # --- Sysadmin ---
    should_be_sysadmin = 'sysadmin' in roles
    if userobj.sysadmin != should_be_sysadmin:
        log.info(f'Setting {username} sysadmin={should_be_sysadmin}')
        userobj.sysadmin = should_be_sysadmin
        model.Session.commit()

    # Sysadmins don't need explicit org roles — skip the rest
    if should_be_sysadmin:
        return

    # --- Org admin roles (non-sysadmins only) ---
    # Collect orgs this user should be admin of
    desired_admin_orgs = set(r for r in roles if r != 'sysadmin')

    # Get all orgs the user currently belongs to
    context = {'ignore_auth': True}
    try:
        current_orgs = toolkit.get_action('organization_list_for_user')(
            context, {'id': username, 'permission': 'read'}
        )
    except Exception as e:
        log.warning(f'Could not fetch org list for {username}: {e}')
        current_orgs = []

    current_org_capacities = {org['name']: org.get('capacity', 'editor')
                               for org in current_orgs}

    # Promote to admin where needed
    for org_name in desired_admin_orgs:
        current_capacity = current_org_capacities.get(org_name)
        if current_capacity != 'admin':
            log.info(f'Promoting {username} to admin in {org_name}')
            try:
                toolkit.get_action('organization_member_create')(
                    context,
                    {'id': org_name, 'username': username, 'role': 'admin'}
                )
            except Exception as e:
                log.warning(f'Could not promote {username} to admin in {org_name}: {e}')

    # Demote from admin in node orgs where no longer listed
    for org_name, capacity in current_org_capacities.items():
        if capacity == 'admin' and org_name not in desired_admin_orgs:
            if org_name.startswith('node-'):
                log.info(f'Demoting {username} from admin to editor in {org_name}')
                try:
                    toolkit.get_action('organization_member_create')(
                        context,
                        {'id': org_name, 'username': username, 'role': 'editor'}
                    )
                except Exception as e:
                    log.warning(f'Could not demote {username} in {org_name}: {e}')


# ---------------------------------------------------------------------------
# User management helpers
# ---------------------------------------------------------------------------

def _sanitize_username(orcid_id):
    """Convert an ORCID iD like 0000-0002-1825-0097 to a CKAN username."""
    return 'orcid-' + orcid_id.lower()


def _find_or_create_user(orcid_id, name, email=None):
    """Find an existing CKAN user by ORCID-based username, or create one.

    Returns the CKAN user dict.
    """
    username = _sanitize_username(orcid_id)

    # Try to find existing user (including deleted/inactive)
    try:
        user = toolkit.get_action('user_show')(
            {'ignore_auth': True}, {'id': username, 'include_deleted': True}
        )
        # Reactivate if user was deleted (but still on whitelist)
        if user.get('state') == 'deleted':
            log.info(f'Reactivating deleted user: {username}')
            userobj = model.User.by_name(username)
            if userobj:
                userobj.state = 'active'
                model.Session.commit()
                user = toolkit.get_action('user_show')(
                    {'ignore_auth': True}, {'id': username}
                )
        log.info(f'Found existing user: {username}')
        return user
    except logic.NotFound:
        pass

    # Create new user
    password = secrets.token_urlsafe(32)
    fullname = name if name else orcid_id
    user_email = email if email else f'{username}@orcid.placeholder'

    try:
        user = toolkit.get_action('user_create')(
            {'ignore_auth': True},
            {
                'name': username,
                'fullname': fullname,
                'email': user_email,
                'password': password,
                'plugin_extras': {
                    'oauth2_login': {
                        'orcid_id': orcid_id,
                        'provider': 'orcid',
                    }
                }
            }
        )
        log.info(f'Created new user: {username} (ORCID: {orcid_id})')

        # Auto-assign to OBIS Community as editor on first login only.
        # Sysadmins are skipped — they don't need an explicit org assignment.
        roles = _get_roles(orcid_id)
        if 'sysadmin' not in roles:
            try:
                toolkit.get_action('organization_member_create')(
                    {'ignore_auth': True},
                    {'id': 'obis-community', 'username': username, 'role': 'editor'}
                )
                log.info(f'Added {username} to obis-community as editor')
            except Exception as e:
                log.warning(f'Could not add {username} to obis-community: {e}')

        return user
    except logic.ValidationError as e:
        log.error(f'Failed to create user for ORCID {orcid_id}: {e.error_dict}')
        raise


def _login_user(username):
    """Set the CKAN session to log in the given user."""
    userobj = model.User.by_name(username)
    if userobj:
        from flask import current_app, session as flask_session
        from ckan.common import login_user as ckan_login_user

        regenerate = getattr(current_app.session_interface, "regenerate", None)
        if regenerate is not None:
            regenerate(flask_session)

        ckan_login_user(userobj)

        try:
            from ckan.views.user import rotate_token
            rotate_token()
        except ImportError:
            pass

        log.info(f'Logged in user: {username}')
    else:
        log.error(f'Cannot find user object for: {username}')


# ---------------------------------------------------------------------------
# Profile update handler
# ---------------------------------------------------------------------------

def _handle_profile_update(orcid_id):
    """Apply pending profile update after ORCID identity verification."""
    pending_id = session.pop('pending_profile_update_id', None)
    form_data = session.pop('pending_profile_update', None)

    if not pending_id or not form_data:
        toolkit.h.flash_error('Profile update failed: no pending update found.')
        return redirect('/')

    expected_username = _sanitize_username(orcid_id)
    if expected_username != pending_id:
        log.warning(
            f'Profile update ORCID mismatch: expected {pending_id}, '
            f'got {expected_username}'
        )
        toolkit.h.flash_error('Profile update failed: ORCID identity mismatch.')
        return redirect('/')

    try:
        toolkit.get_action('user_update')(
            {'ignore_auth': True},
            {
                'id': pending_id,
                'fullname': form_data.get('fullname', ''),
                'email': form_data.get('email', ''),
                'about': form_data.get('about', ''),
                'image_url': form_data.get('image_url', ''),
            }
        )
        log.info(f'Profile updated for {pending_id}')
        toolkit.h.flash_success('Profile updated successfully.')
    except Exception as e:
        log.error(f'Profile update failed for {pending_id}: {e}')
        toolkit.h.flash_error(f'Profile update failed: {str(e)}')

    return redirect(toolkit.url_for('user.read', id=pending_id))


# ---------------------------------------------------------------------------
# Flask Blueprint (routes)
# ---------------------------------------------------------------------------

oauth2_login_blueprint = Blueprint('oauth2_login', __name__)


@oauth2_login_blueprint.route('/oauth2/login/orcid')
def orcid_login():
    """Redirect user to ORCID authorization page."""
    client_id = _config('orcid_client_id')
    redirect_uri = _config('redirect_uri')

    if not client_id or not redirect_uri:
        toolkit.abort(500, 'OAuth2 login is not configured. '
                      'Set CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID and '
                      'CKANEXT__OAUTH2_LOGIN__REDIRECT_URI in .env')

    state = secrets.token_urlsafe(32)
    session['oauth2_state'] = state

    came_from = request.args.get('came_from', '/')
    session['oauth2_came_from'] = came_from

    authorize_url = (
        f'{_authorize_url()}'
        f'?client_id={client_id}'
        f'&response_type=code'
        f'&scope=openid'
        f'&redirect_uri={redirect_uri}'
        f'&state={state}'
    )

    return redirect(authorize_url)


@oauth2_login_blueprint.route('/user/edit-orcid/<id>', methods=['POST'])
def orcid_profile_edit(id):
    """Handle profile edit for ORCID users — verify via ORCID before saving."""
    from ckan.common import current_user

    if not current_user.is_authenticated:
        toolkit.abort(403, 'Not authorized')
    if current_user.name != id and not current_user.sysadmin:
        toolkit.abort(403, 'Not authorized')

    form_data = {k: v for k, v in request.form.items()}
    session['pending_profile_update'] = form_data
    session['pending_profile_update_id'] = id

    client_id = _config('orcid_client_id')
    redirect_uri = _config('redirect_uri')

    state = 'profile_update:' + secrets.token_urlsafe(32)
    session['oauth2_state'] = state

    authorize_url = (
        f'{_authorize_url()}'
        f'?client_id={client_id}'
        f'&response_type=code'
        f'&scope=openid'
        f'&redirect_uri={redirect_uri}'
        f'&state={state}'
    )

    return redirect(authorize_url)


@oauth2_login_blueprint.route('/user/reset', methods=['GET', 'POST'])
@oauth2_login_blueprint.route('/user/reset/<id>', methods=['GET', 'POST'])
def block_reset(id=None):
    """Block password reset — all auth is via ORCID."""
    toolkit.abort(404)


@oauth2_login_blueprint.route('/oauth2/callback')
def orcid_callback():
    """Handle the redirect back from ORCID after user authorizes."""

    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', 'Unknown error')
        log.warning(f'ORCID OAuth error: {error} - {error_desc}')
        toolkit.h.flash_error(f'ORCID login failed: {error_desc}')
        return redirect('/')

    state = request.args.get('state')
    expected_state = session.pop('oauth2_state', None)
    if not state or state != expected_state:
        log.warning('OAuth2 state mismatch - possible CSRF attack')
        toolkit.h.flash_error('Login failed: security check failed. Please try again.')
        return redirect('/')

    code = request.args.get('code')
    if not code:
        toolkit.h.flash_error('Login failed: no authorization code received.')
        return redirect('/')

    client_id = _config('orcid_client_id')
    client_secret = _config('orcid_client_secret')
    redirect_uri = _config('redirect_uri')

    try:
        token_response = http_requests.post(
            _token_url(),
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
            },
            headers={'Accept': 'application/json'},
            timeout=30,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
    except http_requests.RequestException as e:
        log.error(f'Failed to exchange code for token: {e}')
        toolkit.h.flash_error('Login failed: could not connect to ORCID.')
        return redirect('/')

    orcid_id = token_data.get('orcid')
    name = token_data.get('name', '')
    access_token = token_data.get('access_token')

    if not orcid_id:
        log.error(f'No ORCID iD in token response: {token_data}')
        toolkit.h.flash_error('Login failed: ORCID did not return your iD.')
        return redirect('/')

    log.info(f'ORCID callback for: {orcid_id} ({name}), state: {state[:20]}...')

    if state.startswith('profile_update:'):
        return _handle_profile_update(orcid_id)

    # Check whitelist
    if not _is_orcid_approved(orcid_id):
        log.warning(f'ORCID {orcid_id} ({name}) not on whitelist — login rejected')
        toolkit.h.flash_error(
            'Your ORCID iD is not yet approved for this catalog. '
            'Please contact helpdesk@obis.org to request access.'
        )
        return redirect('/')

    # Fetch email from userinfo if available
    email = None
    if access_token:
        try:
            userinfo_response = http_requests.get(
                _userinfo_url(),
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json',
                },
                timeout=15,
            )
            if userinfo_response.ok:
                userinfo = userinfo_response.json()
                if not name:
                    given = userinfo.get('given_name', '')
                    family = userinfo.get('family_name', '')
                    name = f'{given} {family}'.strip()
                email = userinfo.get('email')
        except http_requests.RequestException as e:
            log.warning(f'Could not fetch userinfo (non-fatal): {e}')

    # Find or create user
    user = _find_or_create_user(orcid_id, name, email)

    # Apply roles from whitelist (every login)
    _apply_roles(orcid_id, user['name'])

    # Log in
    _login_user(user['name'])

    came_from = session.pop('oauth2_came_from', '/')
    toolkit.h.flash_success(f'Welcome, {user.get("fullname", user["name"])}!')
    return redirect(came_from)


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------

class OAuth2LoginPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAuthenticator, inherit=True)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IMiddleware, inherit=True)

    def get_blueprint(self):
        return [oauth2_login_blueprint]

    def login(self):
        return None

    def identify(self):
        pass

    def logout(self):
        return None

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')

    def make_middleware(self, app, config):
        app.config['WTF_CSRF_SSL_STRICT'] = False
        return app

    def make_error_log_middleware(self, app, config):
        return app

    def get_helpers(self):
        return {
            'oauth2_login_orcid_enabled': _orcid_enabled,
            'oauth2_login_orcid_url': _orcid_login_url,
        }


def _orcid_enabled():
    return bool(_config('orcid_client_id'))


def _orcid_login_url():
    return '/oauth2/login/orcid'