FROM ckan/ckan-base:2.11

USER root

# Install community extensions
RUN pip3 install -e 'git+https://github.com/ckan/ckanext-scheming.git@master#egg=ckanext-scheming'

# Copy and install custom extensions
COPY --chown=ckan-sys:ckan-sys src/ckanext-obis_theme /srv/app/src/ckanext-obis_theme
COPY --chown=ckan-sys:ckan-sys src/ckanext-odis /srv/app/src/ckanext-odis
COPY --chown=ckan-sys:ckan-sys src/ckanext-zenodo /srv/app/src/ckanext-zenodo
COPY --chown=ckan-sys:ckan-sys src/ckanext-doi-import /srv/app/src/ckanext-doi-import

RUN pip3 install -e /srv/app/src/ckanext-obis_theme && \
    pip3 install -e /srv/app/src/ckanext-odis && \
    pip3 install -e /srv/app/src/ckanext-zenodo && \
    pip3 install -e /srv/app/src/ckanext-doi-import

# Copy startup overrides
COPY --chown=ckan-sys:ckan-sys ckan/setup/start_ckan.sh.override /srv/app/start_ckan.sh
COPY --chown=ckan-sys:ckan-sys ckan/setup/prerun.py.override /srv/app/prerun.py

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
