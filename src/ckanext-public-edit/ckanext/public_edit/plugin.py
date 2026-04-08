# encoding: utf-8
"""
ckanext-public-edit

Authorization policy for the OBIS Products Catalog.

Permission model:
  Sysadmins:
    - Everything

  Org admins (admin capacity in a node-* org):
    - Edit and delete products belonging to their org
    - Manage members of their org
    - Create new products under their org
    - Cannot reassign products between orgs (sysadmin only)

  Regular editors (obis-community members):
    - Create new products (assigned to obis-community)
    - Edit and delete products belonging to obis-community only
    - Add institutions (groups) to any product (but not remove)

  Any logged-in user:
    - Manage group (institution) members
    - Add institutions to any product

  Anonymous:
    - Browse and search only
"""

import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic.auth as logic_auth
import ckan.authz as authz
import ckan.model as model

log = logging.getLogger(__name__)

OBIS_COMMUNITY_ORG = 'obis-community'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_sysadmin(username):
    if not username:
        return False
    userobj = model.User.by_name(username)
    return userobj and userobj.sysadmin


def _get_user_org_capacity(username, org_id):
    """Return the user's capacity in the given org, or None if not a member."""
    if not username or not org_id:
        return None
    try:
        members = toolkit.get_action('organization_show')(
            {'ignore_auth': True},
            {'id': org_id, 'include_users': True}
        ).get('users', [])
        for member in members:
            if member['name'] == username:
                return member['capacity']
    except Exception:
        pass
    return None


def _is_org_admin(username, org_id):
    """True if user has admin capacity in the given org."""
    return _get_user_org_capacity(username, org_id) == 'admin'


def _user_orgs_with_capacity(username, capacity):
    """Return set of org names where the user has at least the given capacity."""
    if not username:
        return set()
    try:
        orgs = toolkit.get_action('organization_list_for_user')(
            {'ignore_auth': True},
            {'id': username, 'permission': 'read'}
        )
        return {o['name'] for o in orgs if o.get('capacity') == capacity}
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# Auth functions
# ---------------------------------------------------------------------------

def public_edit_package_update(context, data_dict):
    """Control who can edit a product.

    - Sysadmin: always
    - Org admin: products in their org
    - Regular editor: products in obis-community only
    - Anonymous: never
    """
    user = context.get('user')

    if not user or authz.auth_is_anon_user(context):
        return {'success': False, 'msg': 'You must be logged in to edit.'}

    if _is_sysadmin(user):
        return {'success': True}

    try:
        package = logic_auth.get_package_object(context, data_dict)
    except toolkit.ObjectNotFound:
        return {'success': False, 'msg': 'Dataset not found.'}

    owner_org = package.owner_org
    if not owner_org:
        return {'success': False, 'msg': 'Product has no owning organization.'}

    # Resolve org_id to org name for comparison
    try:
        org = toolkit.get_action('organization_show')(
            {'ignore_auth': True}, {'id': owner_org}
        )
        org_name = org['name']
    except Exception:
        return {'success': False, 'msg': 'Could not resolve owning organization.'}

    # Org admins can edit their own org's products
    if _is_org_admin(user, owner_org):
        return {'success': True}

    # Regular editors can only edit obis-community products
    if org_name == OBIS_COMMUNITY_ORG:
        return {'success': True}

    return {
        'success': False,
        'msg': 'You can only edit products belonging to your organization.'
    }


def public_edit_package_create(context, data_dict):
    """Any logged-in user can create products."""
    user = context.get('user')

    if not user or authz.auth_is_anon_user(context):
        return {'success': False, 'msg': 'You must be logged in to create products.'}

    return {'success': True}


def public_edit_package_delete(context, data_dict):
    """Only org admins (for their org) and sysadmins can delete products."""
    user = context.get('user')

    if not user or authz.auth_is_anon_user(context):
        return {'success': False, 'msg': 'Not authorized to delete products.'}

    if _is_sysadmin(user):
        return {'success': True}

    try:
        package = logic_auth.get_package_object(context, data_dict)
    except toolkit.ObjectNotFound:
        return {'success': False, 'msg': 'Dataset not found.'}

    if package.owner_org and _is_org_admin(user, package.owner_org):
        return {'success': True}

    # Also allow deletion of obis-community products by any editor
    try:
        org = toolkit.get_action('organization_show')(
            {'ignore_auth': True}, {'id': package.owner_org}
        )
        if org['name'] == OBIS_COMMUNITY_ORG:
            return {'success': True}
    except Exception:
        pass

    return {
        'success': False,
        'msg': 'Only organization admins can delete products.'
    }


def public_edit_user_autocomplete(context, data_dict):
    """Allow anyone to call user_autocomplete.

    The API v2 legacy route used by the Add Member UI does not reliably pass
    session credentials into the auth context. The security boundary is the
    manage_members page itself, which requires org admin or sysadmin.
    """
    return {'success': True}


def public_edit_user_list(context, data_dict):
    """Allow anyone to call user_list (needed for member management UI)."""
    return {'success': True}


def public_edit_group_manage_members(context, data_dict):
    """Allow any logged-in user to manage institution (group) members."""
    user = context.get('user')

    if not user or authz.auth_is_anon_user(context):
        return {'success': False, 'msg': 'You must be logged in to manage members.'}

    return {'success': True}


def public_edit_member_create(context, data_dict):
    """Allow any logged-in user to add members to groups (institutions).

    For organizations (nodes), fall back to default CKAN behavior
    (org admins and sysadmins only).
    """
    user = context.get('user')

    if not user or authz.auth_is_anon_user(context):
        return {'success': False, 'msg': 'You must be logged in.'}

    # Determine if this is a group or an org
    group_id = data_dict.get('id')
    if group_id:
        try:
            group = model.Group.get(group_id)
            if group and not group.is_organization:
                # It's a group (institution) — any logged-in user can add members
                return {'success': True}
        except Exception:
            pass

    # For orgs, fall back to default CKAN (org admin / sysadmin)
    return authz.is_authorized('organization_member_create', context, data_dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_can_change_org(owner_org):
    """Template helper: can the current user change this dataset's org?

    Only sysadmins can reassign products between orgs.
    """
    if not owner_org:
        return True  # new product, user picks from their orgs

    try:
        user_obj = toolkit.g.userobj
        return user_obj and user_obj.sysadmin
    except Exception:
        return False


# ---------------------------------------------------------------------------
# IPackageController hook
# ---------------------------------------------------------------------------

def _before_dataset_update(context, current, resource):
    """Enforce org reassignment and group field rules on update.

    - Only sysadmins can change owner_org
    - Any logged-in user can add groups (institutions) to a product
    - Only org admins and sysadmins can remove groups from a product
    """
    user = context.get('user')
    if not user:
        return resource

    if _is_sysadmin(user):
        return resource

    # --- Block org reassignment ---
    original_org = current.get('owner_org')
    new_org = resource.get('owner_org')
    if original_org and original_org != new_org:
        log.info(f'User {user} tried to change owner_org — blocked, sysadmin only')
        resource['owner_org'] = original_org

    # --- Group (institution) field: allow adds, block removes for non-admins ---
    original_groups = {g['name'] for g in (current.get('groups') or [])}
    new_groups = {g['name'] for g in (resource.get('groups') or [])}

    removed_groups = original_groups - new_groups
    if removed_groups:
        # Check if user is org admin for the product's org
        owner_org = current.get('owner_org')
        if not (owner_org and _is_org_admin(user, owner_org)):
            log.info(
                f'User {user} tried to remove institutions {removed_groups} — blocked'
            )
            # Restore removed groups by merging back
            merged = list(resource.get('groups') or [])
            existing_names = {g['name'] for g in merged}
            for g in (current.get('groups') or []):
                if g['name'] in removed_groups and g['name'] not in existing_names:
                    merged.append(g)
            resource['groups'] = merged

    return resource


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------

class PublicEditPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    def get_auth_functions(self):
        return {
            'package_update': public_edit_package_update,
            'package_create': public_edit_package_create,
            'package_delete': public_edit_package_delete,
            'user_autocomplete': public_edit_user_autocomplete,
            'user_list': public_edit_user_list,
            'group_edit_permissions': public_edit_group_manage_members,
            'member_create': public_edit_member_create,
        }

    def before_dataset_update(self, context, current, resource):
        return _before_dataset_update(context, current, resource)

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')

    def get_helpers(self):
        return {
            'public_edit_user_can_change_org': _user_can_change_org,
        }