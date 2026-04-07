#!/usr/bin/env python3
"""
Generate docs from zenodo_schema.yaml:
1. Writes docs/data-model.md
2. Merges generated schemas into docs/api/openapi_base.yaml -> docs/api/openapi.yaml

Run before mkdocs build in the nginx Dockerfile.
"""
import yaml
import sys
import copy

SCHEMA_PATH = '/tmp/zenodo_schema.yaml'
OPENAPI_BASE_PATH = '/tmp/docs/api/openapi_base.yaml'
OPENAPI_OUTPUT_PATH = '/tmp/docs/api/openapi.yaml'
DATA_MODEL_OUTPUT_PATH = '/tmp/docs/data-model.md'

SKIP_FIELDS = {'name', 'owner_org', 'source_metadata'}

JSON_SCHEMAS = {
    'authors': [
        ('author_name', 'Full name'),
        ('author_given_name', 'Given name'),
        ('author_family_name', 'Family name'),
        ('author_orcid', 'ORCID URL'),
        ('author_affiliation_name', 'Affiliation name'),
        ('author_affiliation_ror', 'ROR ID'),
    ],
    'contributors': [
        ('contributor_name', 'Full name'),
        ('contributor_given_name', 'Given name'),
        ('contributor_family_name', 'Family name'),
        ('contributor_orcid', 'ORCID URL'),
        ('contributor_affiliation_name', 'Affiliation name'),
        ('contributor_affiliation_ror', 'ROR ID'),
    ],
    'funding': [
        ('funder_name', 'Funder name'),
        ('funder_id', 'Funder ID'),
        ('grant_name', 'Grant name'),
        ('grant_id', 'Grant ID'),
        ('grant_url', 'Grant URL'),
    ],
}


def get_field_type(field):
    preset = field.get('preset', '')
    if preset == 'multiple_checkbox':
        return 'multiple choice'
    if preset == 'select':
        return 'select'
    if preset == 'date':
        return 'date'
    if preset == 'title':
        return 'text'
    if field.get('form_snippet') == 'markdown.html':
        if 'json_array' in field.get('validators', ''):
            return 'JSON array'
        return 'text (markdown)'
    return 'text'


def build_data_model_md(fields):
    lines = []
    lines.append('# Data Model')
    lines.append('')
    lines.append('This page is auto-generated from `zenodo_schema.yaml` at build time.')
    lines.append('')

    lines.append('## Dataset Fields')
    lines.append('')
    lines.append('| Field | Label | Type | Required | Description |')
    lines.append('|---|---|---|---|---|')

    for field in fields:
        name = field.get('field_name', '')
        if name in SKIP_FIELDS:
            continue
        if field.get('choices'):
            continue
        label = field.get('label', '')
        required = '✓' if field.get('required') else ''
        help_text = field.get('help_text', '').replace('|', '\\|')
        ftype = get_field_type(field)
        lines.append(f'| `{name}` | {label} | {ftype} | {required} | {help_text} |')

    lines.append('')

    for field in fields:
        if field.get('field_name') == 'product_type':
            lines.append('## Product Types')
            lines.append('')
            lines.append('Controlled vocabulary for the `product_type` field.')
            lines.append('')
            lines.append('| Value | Label |')
            lines.append('|---|---|')
            for choice in field.get('choices', []):
                lines.append(f'| `{choice["value"]}` | {choice["label"]} |')
            lines.append('')

    for field in fields:
        if field.get('field_name') == 'thematic_tags':
            lines.append('## Thematic Areas')
            lines.append('')
            lines.append('Controlled vocabulary for the `thematic_tags` field.')
            lines.append('')
            lines.append('| Value | Label |')
            lines.append('|---|---|')
            for choice in field.get('choices', []):
                lines.append(f'| `{choice["value"]}` | {choice["label"]} |')
            lines.append('')

    lines.append('## Spatial Coverage')
    lines.append('')
    lines.append('The `spatial_coverage_type` field determines which spatial fields are used:')
    lines.append('')
    lines.append('| Type | Fields used |')
    lines.append('|---|---|')
    lines.append('| `point` | `spatial_point_latitude`, `spatial_point_longitude` |')
    lines.append('| `box` | `spatial_box` (format: `miny minx maxy maxx`) |')
    lines.append('')

    lines.append('## JSON Array Fields')
    lines.append('')
    lines.append('The `authors`, `contributors`, and `funding` fields store structured data as JSON arrays.')
    lines.append('')

    examples = {
        'authors': '[{"author_name": "Jane Doe", "author_orcid": "https://orcid.org/0000-0001-2345-6789", "author_affiliation_name": "VLIZ"}]',
        'contributors': '[{"contributor_name": "John Smith", "contributor_affiliation_name": "OBIS Secretariat"}]',
        'funding': '[{"funder_name": "European Commission", "grant_id": "12345", "grant_name": "Marine Biodiversity Project"}]',
    }

    for field_name, subfields in JSON_SCHEMAS.items():
        lines.append(f'### `{field_name}`')
        lines.append('')
        lines.append('| Key | Description |')
        lines.append('|---|---|')
        for key, desc in subfields:
            lines.append(f'| `{key}` | {desc} |')
        lines.append('')
        lines.append('Example:')
        lines.append('```json')
        lines.append(examples[field_name])
        lines.append('```')
        lines.append('')

    lines.append('## Data Pipeline')
    lines.append('')
    lines.append('```')
    lines.append('Source API (Zenodo, future: GBIF, Dryad, etc.)')
    lines.append('    ↓ mapper (Python function: API response → standard dict)')
    lines.append('    ↓')
    lines.append('CKAN (storage, curation UI, search, user management)')
    lines.append('    ↓ odis_export extension (CKAN dataset → Schema.org JSON-LD)')
    lines.append('    ↓')
    lines.append('ODIS (discovery, federated search)')
    lines.append('```')
    lines.append('')
    lines.append('Adding a new source requires writing one mapper file in `ckanext-doi-import/ckanext/doi_import/mappers/`.')

    return '\n'.join(lines)


def build_openapi_schemas(fields):
    """Build OpenAPI schema components from zenodo_schema.yaml fields."""

    # Extract controlled vocabularies
    product_type_enum = []
    thematic_enum = []
    for field in fields:
        if field.get('field_name') == 'product_type':
            product_type_enum = [c['value'] for c in field.get('choices', [])]
        if field.get('field_name') == 'thematic_tags':
            thematic_enum = [c['value'] for c in field.get('choices', [])]

    # Build Dataset schema properties from fields
    properties = {}
    for field in fields:
        name = field.get('field_name', '')
        if name in SKIP_FIELDS:
            continue

        prop = {}
        help_text = field.get('help_text', '')
        if help_text:
            prop['description'] = help_text

        if name == 'product_type':
            prop['type'] = 'array'
            prop['items'] = {'type': 'string', 'enum': product_type_enum}
        elif name == 'thematic_tags':
            prop['type'] = 'array'
            prop['items'] = {'type': 'string', 'enum': thematic_enum}
        elif name in ('authors', 'contributors', 'funding'):
            prop['type'] = 'array'
            prop['items'] = {'$ref': f'#/components/schemas/{name.capitalize().rstrip("s")}'}
            if name == 'authors':
                prop['items'] = {'$ref': '#/components/schemas/Author'}
            elif name == 'contributors':
                prop['items'] = {'$ref': '#/components/schemas/Contributor'}
            elif name == 'funding':
                prop['items'] = {'$ref': '#/components/schemas/Funding'}
        else:
            prop['type'] = 'string'

        placeholder = field.get('form_placeholder', '')
        if placeholder:
            prop['example'] = placeholder

        properties[name] = prop

    schemas = {
        'Error': {
            'type': 'object',
            'properties': {
                'error': {
                    'type': 'string',
                    'example': 'doi_url required in JSON body'
                }
            }
        },
        'Dataset': {
            'type': 'object',
            'description': (
                'A product in the OBIS Products Catalog. Field names follow CKAN '
                'conventions (e.g. `name` = URL slug, `notes` = description). '
                'For the full field reference see [Data Model](/docs/data-model/).'
            ),
            'properties': properties
        },
        'Author': {
            'type': 'object',
            'properties': {k: {'type': 'string'} for k, _ in JSON_SCHEMAS['authors']}
        },
        'Contributor': {
            'type': 'object',
            'properties': {k: {'type': 'string'} for k, _ in JSON_SCHEMAS['contributors']}
        },
        'Funding': {
            'type': 'object',
            'properties': {k: {'type': 'string'} for k, _ in JSON_SCHEMAS['funding']}
        },
    }

    return schemas


def main():
    with open(SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)

    fields = schema.get('dataset_fields', [])

    # Generate data-model.md
    with open(DATA_MODEL_OUTPUT_PATH, 'w') as f:
        f.write(build_data_model_md(fields))
    print(f'Generated {DATA_MODEL_OUTPUT_PATH}')

    # Generate openapi.yaml by merging schemas into base
    with open(OPENAPI_BASE_PATH) as f:
        openapi = yaml.safe_load(f)

    openapi.setdefault('components', {})
    openapi['components']['schemas'] = build_openapi_schemas(fields)

    with open(OPENAPI_OUTPUT_PATH, 'w') as f:
        yaml.dump(openapi, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f'Generated {OPENAPI_OUTPUT_PATH}')


if __name__ == '__main__':
    main()