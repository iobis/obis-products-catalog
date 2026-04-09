import os

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation
from ckanext.obis_theme import helpers
from flask import Blueprint


class ObisThemePlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "obis_theme")

    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        unicode_safe = toolkit.get_validator('unicode_safe')
        schema.update({
            'ckanext.obis_theme.featured_products': [ignore_missing, unicode_safe],
        })
        return schema

    # ITranslation

    def i18n_directory(self):
        return os.path.join(os.path.dirname(__file__), "i18n")

    def i18n_locales(self):
        return ["en"]

    def i18n_domain(self):
        return "ckan"

    # ITemplateHelpers

    def get_helpers(self):
        return {
            "dataset_type_class": helpers.dataset_type_class,
            "obis_get_product_type_stats": helpers.obis_get_product_type_stats,
            "obis_get_thematic_stats": helpers.obis_get_thematic_stats,
            "obis_get_recent_datasets": helpers.obis_get_recent_datasets,
            "obis_get_featured_datasets": helpers.obis_get_featured_datasets,
            "obis_parse_json_field": helpers.obis_parse_json_field,
            "obis_get_node_orgs": helpers.obis_get_node_orgs,
            "obis_is_sysadmin": helpers.obis_is_sysadmin,
        }

    # IBlueprint

    def get_blueprint(self):
        blueprint = Blueprint("obis_theme", __name__)
        blueprint.add_url_rule(
            "/ckan-admin/featured-products",
            "featured_products",
            helpers.featured_products_admin,
            methods=["GET", "POST"],
        )
        return blueprint