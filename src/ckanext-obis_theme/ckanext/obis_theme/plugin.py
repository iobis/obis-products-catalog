import os

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation
from ckanext.obis_theme import helpers


class ObisThemePlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "obis_theme")

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
        }
