#!/bin/sh
echo "Setting up scheming configuration..."
if [ -n "$CKAN___SCHEMING__DATASET_SCHEMAS" ]; then
    ckan config-tool $CKAN_INI "scheming.dataset_schemas = $CKAN___SCHEMING__DATASET_SCHEMAS"
    echo "Scheming dataset schemas set to: $CKAN___SCHEMING__DATASET_SCHEMAS"
fi
