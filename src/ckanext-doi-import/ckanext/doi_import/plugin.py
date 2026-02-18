"""CKAN DOI Import Extension — import datasets from DOIs."""

import re
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.doi_import.mappers.base import extract_doi_from_url, detect_source
from ckanext.doi_import.mappers import zenodo as zenodo_mapper


class DoiImportPlugin(plugins.SingletonPlugin):
    """CKAN plugin for importing datasets from DOIs."""

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("public", "doi_import")

    # ITemplateHelpers

    def get_helpers(self):
        return {"doi_import_enabled": lambda: True}

    # IBlueprint

    def get_blueprint(self):
        from flask import Blueprint

        blueprint = Blueprint("doi_import", __name__)

        blueprint.add_url_rule(
            "/dataset/import-doi",
            "import_doi_form",
            self._import_doi_form,
            methods=["GET", "POST"],
        )
        blueprint.add_url_rule(
            "/dataset/new-choice",
            "dataset_new_choice",
            self._dataset_new_choice,
            methods=["GET"],
        )
        blueprint.add_url_rule(
            "/api/harvest-doi",
            "harvest_doi",
            self._harvest_doi_endpoint,
            methods=["POST"],
        )
        return blueprint

    # IActions

    def get_actions(self):
        return {
            "doi_fetch_metadata": doi_fetch_metadata,
            "doi_create_dataset": doi_create_dataset,
        }

    # --- Route handlers ---

    def _dataset_new_choice(self):
        """Show choice between manual dataset creation and DOI import."""
        from flask import render_template

        context = {"user": toolkit.c.user, "auth_user_obj": toolkit.c.userobj}
        try:
            toolkit.check_access("package_create", context)
        except toolkit.NotAuthorized:
            toolkit.abort(403, "Not authorized to create datasets")

        return render_template("doi_import/dataset_new_choice.html")

    def _import_doi_form(self):
        """Handle the DOI import form (GET: show form, POST: process import)."""
        from flask import request, render_template, redirect, url_for, flash

        context = {"user": toolkit.c.user, "auth_user_obj": toolkit.c.userobj}

        if request.method == "GET":
            try:
                user_orgs = toolkit.get_action("organization_list_for_user")(
                    context, {"id": toolkit.c.userobj.id}
                )
            except (AttributeError, toolkit.NotAuthorized):
                user_orgs = []

            try:
                groups = toolkit.get_action("group_list")(
                    context, {"all_fields": True, "limit": 1000}
                )
                contributing_orgs = [
                    {"value": g["id"], "label": g["display_name"]} for g in groups
                ]
            except Exception:
                contributing_orgs = []

            return render_template(
                "doi_import/import_form.html",
                user_orgs=user_orgs,
                contributing_orgs=contributing_orgs,
            )

        # POST
        doi_url = request.form.get("doi_url", "").strip()
        selected_org = request.form.get("owner_org")
        contributing_orgs = request.form.getlist("contributing_organizations")

        if not doi_url:
            flash("Please provide a DOI URL", "error")
            return redirect(url_for("doi_import.import_doi_form"))

        try:
            metadata = toolkit.get_action("doi_fetch_metadata")(
                context, {"doi_url": doi_url}
            )
            dataset_dict = toolkit.get_action("doi_create_dataset")(
                context,
                {
                    "metadata": metadata,
                    "owner_org": selected_org,
                    "contributing_organizations": contributing_orgs,
                },
            )
            flash(
                f'Dataset "{dataset_dict["title"]}" imported successfully!', "success"
            )
            return redirect(url_for("dataset.read", id=dataset_dict["name"]))

        except Exception as e:
            flash(f"Error importing dataset: {e}", "error")
            return redirect(url_for("doi_import.import_doi_form"))

    def _harvest_doi_endpoint(self):
        """API endpoint for automated DOI harvesting."""
        from flask import request, jsonify
        import ckan.model as model

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Authorization header required"}), 401

        token = auth_header.replace("Bearer ", "").replace("bearer ", "").strip()

        try:
            token_obj = (
                model.Session.query(model.ApiToken).filter_by(id=token).first()
            )
            if not token_obj:
                return jsonify({"error": "Invalid API token"}), 401

            user_obj = model.User.get(token_obj.user_id)
            if not user_obj:
                return jsonify({"error": "Token user not found"}), 401

            context = {
                "model": model,
                "session": model.Session,
                "user": user_obj.name,
                "auth_user_obj": user_obj,
                "api_version": 3,
                "ignore_auth": False,
            }

            try:
                toolkit.check_access("package_create", context)
            except toolkit.NotAuthorized:
                return (
                    jsonify({"error": "User not authorized to create datasets"}),
                    403,
                )

            data = request.get_json()
            if not data or not data.get("doi_url"):
                return jsonify({"error": "doi_url required in JSON body"}), 400

            doi_url = data["doi_url"]

            # Fetch metadata
            metadata = toolkit.get_action("doi_fetch_metadata")(
                context, {"doi_url": doi_url}
            )

            # Check for existing dataset by matching Zenodo URL
            metadata_url = metadata.get("url", "")
            existing_dataset = _find_existing_dataset(context, metadata_url)

            site_url = toolkit.config.get("ckan.site_url", "http://localhost:5000")

            if existing_dataset:
                metadata["id"] = existing_dataset["id"]
                metadata["name"] = existing_dataset["name"]

                dataset_dict = toolkit.get_action("doi_create_dataset")(
                    context,
                    {
                        "metadata": metadata,
                        "owner_org": existing_dataset.get("owner_org", "obis-community"),
                        "contributing_organizations": [],
                        "is_update": True,
                    },
                )
                action = "updated"
            else:
                dataset_dict = toolkit.get_action("doi_create_dataset")(
                    context,
                    {
                        "metadata": metadata,
                        "owner_org": "obis-community",
                        "contributing_organizations": [],
                        "is_update": False,
                    },
                )
                action = "created"

            return jsonify(
                {
                    "success": True,
                    "action": action,
                    "dataset": {
                        "id": dataset_dict["id"],
                        "name": dataset_dict["name"],
                        "title": dataset_dict["title"],
                        "url": f"{site_url}/dataset/{dataset_dict['name']}",
                    },
                }
            )

        except toolkit.ValidationError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Server error: {e}"}), 500


# --- Action functions ---


def doi_fetch_metadata(context, data_dict):
    """Fetch metadata from a DOI URL.

    Determines the source (Zenodo, etc.) and delegates to the
    appropriate mapper.
    """
    doi_url = data_dict.get("doi_url", "").strip()
    if not doi_url:
        raise toolkit.ValidationError({"doi_url": "DOI URL is required"})

    doi = extract_doi_from_url(doi_url)
    if not doi:
        raise toolkit.ValidationError({"doi_url": "Invalid DOI URL format"})

    source = detect_source(doi)

    if source == "zenodo":
        return zenodo_mapper.fetch_metadata(doi)

    # Try searching Zenodo as a fallback for unknown DOIs
    result = zenodo_mapper.search_by_doi(doi)
    if result:
        return result

    raise toolkit.ValidationError(
        {
            "doi_url": (
                "This DOI is not available on Zenodo. "
                "We currently only support importing from Zenodo. "
                "Please use a Zenodo DOI (e.g., https://doi.org/10.5281/zenodo.XXXXX)"
            )
        }
    )


def doi_create_dataset(context, data_dict):
    """Create or update a dataset from fetched DOI metadata."""
    metadata = data_dict.get("metadata", {})
    owner_org = data_dict.get("owner_org")
    contributing_orgs = data_dict.get("contributing_organizations", [])

    if owner_org:
        metadata["owner_org"] = owner_org

    if contributing_orgs:
        if not isinstance(contributing_orgs, list):
            contributing_orgs = [contributing_orgs]
        metadata["groups"] = [{"id": org_id} for org_id in contributing_orgs]

    # Generate a URL-safe name for new datasets
    if "id" not in metadata:
        base_name = re.sub(r"[^\w\s-]", "", metadata.get("title", "dataset")).lower()
        base_name = re.sub(r"[-\s]+", "-", base_name)[:50]
        metadata["name"] = base_name or "imported-dataset"

    if "id" in metadata:
        dataset_dict = toolkit.get_action("package_update")(context, metadata)
    else:
        dataset_dict = toolkit.get_action("package_create")(context, metadata)

    return dataset_dict


# --- Helpers ---


def _find_existing_dataset(context, zenodo_url):
    """Search for an existing dataset that matches a Zenodo record URL."""
    if not zenodo_url:
        return None

    search_results = toolkit.get_action("package_search")(
        context, {"fq": "url:*zenodo.org/record*", "rows": 1000}
    )

    for result in search_results.get("results", []):
        if result.get("url") == zenodo_url:
            return result

    return None
