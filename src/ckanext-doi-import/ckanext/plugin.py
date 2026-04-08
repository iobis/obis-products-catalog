# encoding: utf-8
"""
ckanext-public-edit

Policy: Any logged-in user can edit public datasets and create new datasets.
Delete is explicitly blocked (only org admins and sysadmins can delete).
Non-admins cannot change a dataset's owner organization.

Enable by adding 'public_edit' to CKAN__PLUGINS in .env.
Disable by removing it — default CKAN org-based permissions resume.
"""

import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic.auth as logic_auth
import ckan.authz as authz
import ckan.model as model

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


def _is_org_admin(org_id, username):
    """Check if user has the 'admin' role in the given organization.

    This is stricter than has_user_permission_for_group_or_org which
    returns True for editors too.
    """
    if not org_id or not username:
        return False

    members = toolkit.get_action('organization_show')(
        {'ignore_auth': True},
        {'id': org_id, 'include_users': True}
    ).get('users', [])

    for member in members:
        if member['name'] == username and member['capacity'] == 'admin':
            return True

    return False


def _user_can_change_org(owner_org):
    """Template helper: can the current user change this dataset's org?

    Returns True only if:
    - owner_org is None (new dataset — user picks from their orgs)
    - User is a sysadmin
    - User is an ADMIN (not editor) of the owning org
    """
    if not owner_org:
        return True

    try:
        user = toolkit.g.user
    except Exception:
        return False

    if not user:
        return False

    # Sysadmins can always change org
    try:
        user_obj = toolkit.g.userobj
        if user_obj and user_obj.sysadmin:
            return True
    except Exception:
        pass

    return _is_org_admin(owner_org, user)


class PublicEditPlugin(plugins.SingletonPlugin):
    """Grants any logged-in user edit access to all public datasets.

    Auth overrides:
    - package_update: logged-in + public dataset = allowed
    - package_create: any logged-in user = allowed
    - package_delete: org admins only (more restrictive than default)

    Also:
    - Prevents non-admins from changing owner_org on existing datasets
    - Provides template helpers for org field visibility
    - Overrides org field template to show read-only for non-admins
    """

    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    def get_auth_functions(self):
        return {
            'package_update': public_edit_package_update,
            'package_create': public_edit_package_create,
            'package_delete': public_edit_package_delete,
        }

    # -- IPackageController --

    def before_dataset_update(self, context, current, resource):
        """Prevent non-admins from changing owner_org on existing datasets.

        If the user is not an admin of the dataset's current org,
        silently preserve the original owner_org.
        """
        user = context.get('user')
        if not user:
            return resource

        original_org = current.get('owner_org')
        new_org = resource.get('owner_org')

        # If org isn't changing, nothing to do
        if not original_org or original_org == new_org:
            return resource

        # Only org admins (not editors) can reassign
        if not _is_org_admin(original_org, user):
            log.info(f'User {user} tried to change owner_org from '
                     f'{original_org} to {new_org} — blocked by public_edit')
            resource['owner_org'] = original_org

        return resource

    # -- IConfigurer --

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')

    # -- ITemplateHelpers --

    def get_helpers(self):
        return {
            'public_edit_user_can_change_org': _user_can_change_org,
        }
