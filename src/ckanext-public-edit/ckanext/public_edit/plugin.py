# encoding: utf-8
"""
ckanext-public-edit

Policy: Any logged-in user can edit public datasets and create new datasets.
Delete is explicitly blocked (only org admins and sysadmins can delete).

Enable by adding 'public_edit' to CKAN__PLUGINS in .env.
Disable by removing it — default CKAN org-based permissions resume.
"""

import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic.auth as logic_auth
import ckan.authz as authz

log = logging.getLogger(__name__)


def public_edit_package_update(context, data_dict):
    """Allow any logged-in user to update any public dataset.

    - Sysadmins: always allowed (CKAN handles this before auth functions)
    - Logged-in user + public dataset: allowed
    - Logged-in user + private dataset: fall back to default CKAN org check
    - Anonymous user: not allowed
    """
    user = context.get('user')

    # Anonymous users cannot edit
    if not user or authz.auth_is_anon_user(context):
        return {'success': False, 'msg': 'You must be logged in to edit.'}

    # Get the dataset object
    try:
        package = logic_auth.get_package_object(context, data_dict)
    except toolkit.ObjectNotFound:
        return {'success': False, 'msg': 'Dataset not found.'}

    # If the dataset is public (not private), any logged-in user can edit
    if not package.private:
        return {'success': True}

    # For private datasets, fall back to default CKAN behavior:
    # user must be editor/admin in the owning organization
    if package.owner_org:
        authorized = authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'update_dataset'
        )
        if authorized:
            return {'success': True}

    return {
        'success': False,
        'msg': 'You are not authorized to edit this private dataset.'
    }


def public_edit_package_create(context, data_dict):
    """Allow any logged-in user to create datasets.

    - Sysadmins: always allowed
    - Any logged-in user: allowed
    - Anonymous: not allowed
    """
    user = context.get('user')

    if not user or authz.auth_is_anon_user(context):
        return {'success': False, 'msg': 'You must be logged in to create datasets.'}

    return {'success': True}


def public_edit_package_delete(context, data_dict):
    """Only org admins and sysadmins can delete datasets.

    This is more restrictive than default CKAN (which allows editors to delete).
    """
    user = context.get('user')

    if not user or authz.auth_is_anon_user(context):
        return {'success': False, 'msg': 'Not authorized to delete datasets.'}

    try:
        package = logic_auth.get_package_object(context, data_dict)
    except toolkit.ObjectNotFound:
        return {'success': False, 'msg': 'Dataset not found.'}

    # Only allow if user is admin in the owning organization
    if package.owner_org:
        authorized = authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'delete_dataset'
        )
        if authorized:
            return {'success': True}

    return {
        'success': False,
        'msg': 'Only organization admins can delete datasets.'
    }


class PublicEditPlugin(plugins.SingletonPlugin):
    """Grants any logged-in user edit access to all public datasets.

    Auth overrides:
    - package_update: logged-in + public dataset = allowed
    - package_create: any logged-in user = allowed
    - package_delete: org admins only (more restrictive than default)
    """

    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self):
        return {
            'package_update': public_edit_package_update,
            'package_create': public_edit_package_create,
            'package_delete': public_edit_package_delete,
        }
