# encoding: utf-8
"""
ckanext-oauth2-login

ORCID OAuth2 login for CKAN. Lets researchers sign in with their ORCID iD.

Flow:
1. User clicks "Sign in with ORCID" → redirected to ORCID authorization page
2. User authorizes → ORCID redirects back with an authorization code
3. Extension exchanges code for access token + ORCID iD
4. Extension creates or finds a matching CKAN user, logs them in

Requires these .env variables:
    CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID
    CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_SECRET
    CKANEXT__OAUTH2_LOGIN__REDIRECT_URI

Optional (defaults to production ORCID):
    CKANEXT__OAUTH2_LOGIN__ORCID_BASE_URL   (use https://sandbox.orcid.org for testing)
"""

import logging
import secrets
import re

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
# User management helpers
# ---------------------------------------------------------------------------

def _sanitize_username(orcid_id):
    """Convert an ORCID iD like 0000-0002-1825-0097 to a CKAN username.

    CKAN usernames must be lowercase, 2-100 chars, using only a-z, 0-9, - and _.
    """
    return 'orcid-' + orcid_id.lower()


def _find_or_create_user(orcid_id, name, email=None):
    """Find an existing CKAN user by ORCID-based username, or create one.

    Returns the CKAN user dict.
    """
    username = _sanitize_username(orcid_id)

    # Try to find existing user
    try:
        user = toolkit.get_action('user_show')(
            {'ignore_auth': True}, {'id': username}
        )
        log.info(f'Found existing user: {username}')
        return user
    except logic.NotFound:
        pass

    # Create new user
    # CKAN requires a password even for OAuth users. Generate a random one
    # that can never be used (OAuth is the only login path for these users).
    password = secrets.token_urlsafe(32)

    # Use provided name, or fall back to ORCID iD
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
        return user
    except logic.ValidationError as e:
        log.error(f'Failed to create user for ORCID {orcid_id}: {e.error_dict}')
        raise


def _login_user(username):
    """Set the CKAN session to log in the given user."""
    userobj = model.User.by_name(username)
    if userobj:
        # CKAN 2.10+ uses Flask-Login
        from ckan.common import login_user as ckan_login_user
        ckan_login_user(userobj)
        log.info(f'Logged in user: {username}')
    else:
        log.error(f'Cannot find user object for: {username}')


# ---------------------------------------------------------------------------
# Flask Blueprint (routes)
# ---------------------------------------------------------------------------

oauth2_login_blueprint = Blueprint(
    'oauth2_login',
    __name__,
)


@oauth2_login_blueprint.route('/oauth2/login/orcid')
def orcid_login():
    """Redirect user to ORCID authorization page."""
    client_id = _config('orcid_client_id')
    redirect_uri = _config('redirect_uri')

    if not client_id or not redirect_uri:
        toolkit.abort(500, 'OAuth2 login is not configured. '
                      'Set CKANEXT__OAUTH2_LOGIN__ORCID_CLIENT_ID and '
                      'CKANEXT__OAUTH2_LOGIN__REDIRECT_URI in .env')

    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth2_state'] = state

    # Store the page the user came from so we can redirect back after login
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


@oauth2_login_blueprint.route('/oauth2/callback')
def orcid_callback():
    """Handle the redirect back from ORCID after user authorizes."""

    # Check for errors from ORCID
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', 'Unknown error')
        log.warning(f'ORCID OAuth error: {error} - {error_desc}')
        toolkit.h.flash_error(f'ORCID login failed: {error_desc}')
        return redirect('/')

    # Verify state parameter (CSRF protection)
    state = request.args.get('state')
    expected_state = session.pop('oauth2_state', None)
    if not state or state != expected_state:
        log.warning('OAuth2 state mismatch - possible CSRF attack')
        toolkit.h.flash_error('Login failed: security check failed. Please try again.')
        return redirect('/')

    # Exchange authorization code for token
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
            headers={
                'Accept': 'application/json',
            },
            timeout=30,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
    except http_requests.RequestException as e:
        log.error(f'Failed to exchange code for token: {e}')
        toolkit.h.flash_error('Login failed: could not connect to ORCID.')
        return redirect('/')

    # ORCID returns the ORCID iD directly in the token response
    orcid_id = token_data.get('orcid')
    name = token_data.get('name', '')
    access_token = token_data.get('access_token')

    if not orcid_id:
        log.error(f'No ORCID iD in token response: {token_data}')
        toolkit.h.flash_error('Login failed: ORCID did not return your iD.')
        return redirect('/')

    log.info(f'ORCID login successful for: {orcid_id} ({name})')

    # Optionally fetch more user info from the userinfo endpoint
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
                # Use given_name + family_name if name wasn't in token response
                if not name:
                    given = userinfo.get('given_name', '')
                    family = userinfo.get('family_name', '')
                    name = f'{given} {family}'.strip()
                email = userinfo.get('email')
        except http_requests.RequestException as e:
            log.warning(f'Could not fetch userinfo (non-fatal): {e}')

    # Find or create the CKAN user
    user = _find_or_create_user(orcid_id, name, email)

    # Log them in
    _login_user(user['name'])

    # Redirect to where they came from
    came_from = session.pop('oauth2_came_from', '/')
    toolkit.h.flash_success(f'Welcome, {user.get("fullname", user["name"])}!')
    return redirect(came_from)


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------

class OAuth2LoginPlugin(plugins.SingletonPlugin):
    """ORCID OAuth2 login for CKAN.

    Implements:
    - IBlueprint: registers /oauth2/login/orcid and /oauth2/callback routes
    - IAuthenticator: hooks into CKAN's login flow to show ORCID button
    - IConfigurer: adds template directory for login page override
    - ITemplateHelpers: provides helper for templates
    """

    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAuthenticator, inherit=True)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # -- IBlueprint --

    def get_blueprint(self):
        return [oauth2_login_blueprint]

    # -- IAuthenticator --

    def login(self):
        """Called before the default login form is shown.

        We don't prevent the default login — we just add the ORCID option
        via template override. Return None to allow normal flow.
        """
        return None

    def identify(self):
        """Called on every request to identify the user.

        Flask-Login handles this for us, so we don't need to do anything.
        """
        pass

    def logout(self):
        """Called before logout. Nothing extra needed."""
        return None

    # -- IConfigurer --

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')

    # -- ITemplateHelpers --

    def get_helpers(self):
        return {
            'oauth2_login_orcid_enabled': _orcid_enabled,
            'oauth2_login_orcid_url': _orcid_login_url,
        }


def _orcid_enabled():
    """Template helper: is ORCID login configured?"""
    return bool(_config('orcid_client_id'))


def _orcid_login_url():
    """Template helper: URL to start ORCID login flow."""
    return '/oauth2/login/orcid'
