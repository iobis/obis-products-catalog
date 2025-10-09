import ckan.plugins.toolkit as tk
import json

def scheming_required_if_spatial_type_is_point(value, context):
    """Required when spatial_type is 'point'."""
    data = context.get('package', {})
    if data.get('spatial_type') == 'point' and not value:
        raise tk.Invalid('Required when spatial type is Point')
    return value

def scheming_required_if_spatial_type_is_bbox(value, context):
    """Required when spatial_type is 'bbox'."""
    data = context.get('package', {})
    if data.get('spatial_type') == 'bbox' and not value:
        raise tk.Invalid('Required when spatial type is Bounding Box')
    return value

def scheming_valid_json_array(value, context):
    """
    Accept JSON arrays as strings or already parsed lists.
    Used for repeating metadata like authors, contributors, funding.
    
    Validates the input and converts back to JSON string for database storage.
    
    Accepts:
    - Empty/None values (returns empty string)
    - Python lists (validates and converts to JSON string)
    - JSON array strings (parses, validates, and returns as JSON string)
    
    Rejects:
    - JSON objects {}
    - Invalid JSON
    - Non-array types
    """
    if value is None or value == '':
        return ''
    
    # Already a list - validate it and convert to JSON string
    if isinstance(value, list):
        # Convert to JSON string for storage
        return json.dumps(value, ensure_ascii=False)
    
    # Try to parse JSON string
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                # Valid JSON array - return as JSON string
                return json.dumps(parsed, ensure_ascii=False)
            else:
                raise tk.Invalid('Expected JSON array, got JSON object. Use [...] not {...}')
        except json.JSONDecodeError as e:
            raise tk.Invalid('Invalid JSON syntax: {}'.format(str(e)))
        except Exception as e:
            raise tk.Invalid('Error parsing JSON: {}'.format(str(e)))
    
    raise tk.Invalid('Expected JSON array string or list, got: {}'.format(type(value).__name__))

def convert_to_json_string(value, context):
    """
    Convert Python lists/dicts to JSON strings for storage in database.
    This is the output converter that runs before saving to DB.
    """
    if value is None or value == '':
        return None
    
    if isinstance(value, str):
        # Already a string, return as-is
        return value
    
    if isinstance(value, (list, dict)):
        # Convert to JSON string
        return json.dumps(value, ensure_ascii=False)
    
    return value