FROM ckan/ckan-base:2.11

USER root

# Install community extensions
RUN pip3 install -e 'git+https://github.com/ckan/ckanext-scheming.git@master#egg=ckanext-scheming'

# Copy and install custom extensions
COPY --chown=ckan-sys:ckan-sys src/ckanext-obis_theme /srv/app/src/ckanext-obis_theme
COPY --chown=ckan-sys:ckan-sys src/ckanext-odis_export /srv/app/src/ckanext-odis_export
COPY --chown=ckan-sys:ckan-sys src/ckanext-obis_schema /srv/app/src/ckanext-obis_schema
COPY --chown=ckan-sys:ckan-sys src/ckanext-doi-import /srv/app/src/ckanext-doi-import
COPY --chown=ckan-sys:ckan-sys src/ckanext-obis_sync /srv/app/src/ckanext-obis_sync
COPY --chown=ckan-sys:ckan-sys src/ckanext-public-edit /srv/app/src/ckanext-public-edit
COPY --chown=ckan-sys:ckan-sys src/ckanext-oauth2-login /srv/app/src/ckanext-oauth2-login

RUN pip3 install -e /srv/app/src/ckanext-obis_theme && \
    pip3 install -e /srv/app/src/ckanext-odis_export && \
    pip3 install -e /srv/app/src/ckanext-obis_schema && \
    pip3 install -e /srv/app/src/ckanext-doi-import && \
    pip3 install -e /srv/app/src/ckanext-obis_sync && \
    pip3 install -e /srv/app/src/ckanext-public-edit && \
    pip3 install -e /srv/app/src/ckanext-oauth2-login

# Copy custom initialization scripts
COPY --chown=ckan-sys:ckan-sys ckan/docker-entrypoint.d/* /docker-entrypoint.d/

# Apply patches
COPY --chown=ckan-sys:ckan-sys ckan/patches ${APP_DIR}/patches

USER ckan

RUN for d in $APP_DIR/patches/*; do \
        if [ -d $d ]; then \
            for f in `ls $d/*.patch | sort -g`; do \
                cd $SRC_DIR`basename "$d"` && echo "$0: Applying patch $f to $SRC_DIR`basename $d`"; patch -p1 < "$f" ; \
            done ; \
        fi ; \
    done
