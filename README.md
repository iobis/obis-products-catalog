# OBIS Products Catalog

A CKAN 2.11 Docker-based catalog system for managing and publishing OBIS (Ocean Biodiversity Information System) products with custom theming, metadata schemas, and JSON-LD export capabilities.

## Repository Structure

```
.
├── bin/                          # Helper scripts for development
│   ├── ckan                      # CKAN CLI wrapper
│   ├── compose                   # Docker Compose wrapper
│   └── shell                     # Container shell access
│
├── ckan/                         # CKAN Docker configuration
│   ├── Dockerfile                # Production CKAN image
│   ├── Dockerfile.dev            # Development CKAN image
│   ├── docker-entrypoint.d/      # Container startup scripts
│   └── setup/                    # Override scripts for custom behavior
│       ├── prerun.py.override
│       ├── start_ckan.sh.override
│       └── start_ckan_development.sh.override
│
├── nginx/                        # NGINX reverse proxy configuration
│   ├── Dockerfile
│   └── setup/
│       ├── default.conf          # NGINX configuration
│       └── ckan-local.*          # SSL certificates
│
├── postgresql/                   # PostgreSQL configuration
│   ├── Dockerfile
│   └── docker-entrypoint-initdb.d/
│       ├── 10_create_ckandb.sh
│       ├── 20_create_datastore.sh
│       └── 30_setup_test_databases.sh
│
└── src/                          # CKAN extensions
    ├── ckanext-doi_import/       # DOI import functionality
    ├── ckanext-obis_theme/       # Custom OBIS theme and UI
    │   ├── ckanext/obis_theme/
    │   │   ├── assets/           # CSS and JavaScript
    │   │   ├── public/           # Static files (images, etc.)
    │   │   ├── templates/        # Jinja2 templates
    │   │   │   ├── home/         # Homepage templates
    │   │   │   ├── package/      # Dataset page templates
    │   │   │   └── snippets/     # Reusable template components
    │   │   └── helpers.py        # Template helper functions
    │   └── scripts/              # Sync scripts for OBIS data
    ├── ckanext-odis/             # ODIS Schema.org JSON-LD export
    │   └── ckanext/odis/
    │       └── plugin.py         # JSON-LD endpoint: /dataset/{id}/odis.jsonld
    └── ckanext-zenodo/           # Zenodo integration and custom schema
        └── ckanext/zenodo/
            ├── zenodo_schema.yaml # Custom metadata schema
            └── cli.py            # CLI commands for Zenodo import
```

## Key Features

### 1. Custom OBIS Theme (`ckanext-obis_theme`)
- **Responsive homepage** with product type and thematic area statistics
- **2×5 grid layout** that adapts to mobile devices
- **Custom dataset landing pages** with enhanced metadata display
- **Helper functions** for dynamic statistics and recent datasets

**Key Files:**
- `src/ckanext-obis_theme/ckanext/obis_theme/templates/home/` - Homepage templates
- `src/ckanext-obis_theme/ckanext/obis_theme/helpers.py` - Statistics and data helpers
- `src/ckanext-obis_theme/ckanext/obis_theme/assets/` - Custom CSS/JS

### 2. ODIS JSON-LD Export (`ckanext-odis`)
Exposes dataset metadata as Schema.org-compliant JSON-LD according to ODIS specifications.

**Endpoint:** `/dataset/{id}/odis.jsonld`

**Features:**
- Schema.org vocabulary with ODIS extensions
- Support for authors, contributors, funding, spatial/temporal coverage
- DOI and identifier mapping
- Proper content-type headers (`application/ld+json`)

**Key Files:**
- `src/ckanext-odis/ckanext/odis/plugin.py` - JSON-LD transformation logic

### 3. Custom Metadata Schema (`ckanext-zenodo`)
Extended metadata schema supporting:
- Product types (dataset, publication, software, etc.)
- Thematic areas (biodiversity, climate change, etc.)
- Author and contributor information with ORCID/ROR
- Funding and grant details
- Spatial and temporal coverage
- DOI and canonical identifiers

**Key Files:**
- `src/ckanext-zenodo/ckanext/zenodo/zenodo_schema.yaml` - Schema definition

### 4. DOI Import (`ckanext-doi_import`)
Import datasets from DOI sources like Zenodo and DataCite.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Initial Setup

1. **Clone and configure:**
   ```bash
   git clone https://github.com/iobis/obis-products-catalog.git
   cd obis-products-catalog
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Build and start:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d --build
   ```

3. **Initialize database:**
   ```bash
   docker exec -it obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini db init
   ```

4. **Create admin user:**
   ```bash
   docker exec -it obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini sysadmin add admin email=admin@localhost
   ```

5. **Access CKAN:**
   Open http://localhost:5000

## Development

### Modifying the Theme

**Homepage layout:**
Edit templates in `src/ckanext-obis_theme/ckanext/obis_theme/templates/home/`

**Statistics and helpers:**
Edit `src/ckanext-obis_theme/ckanext/obis_theme/helpers.py`

**CSS/JavaScript:**
Edit files in `src/ckanext-obis_theme/ckanext/obis_theme/assets/`

**After changes:**
```bash
docker-compose -f docker-compose.dev.yml restart ckan-dev
```

### Modifying the Schema

1. Edit `src/ckanext-zenodo/ckanext/zenodo/zenodo_schema.yaml`
2. Restart: `docker-compose -f docker-compose.dev.yml restart ckan-dev`
3. Changes apply immediately (no rebuild needed)

### Testing JSON-LD Export

Access any dataset's JSON-LD:
```
http://localhost:5000/dataset/{dataset-name}/odis.jsonld
```

## Environment Configuration

Key environment variables in `.env`:

```bash
# CKAN settings
CKAN_SITE_URL=http://localhost:5000
CKAN_PORT_HOST=5000

# Custom schema
CKAN___SCHEMING__DATASET_SCHEMAS=ckanext.zenodo:zenodo_schema.yaml

# Security (change in production!)
CKAN___SECRET_KEY=your_secret_key_here
CKAN___BEAKER__SESSION__SECRET=your_beaker_secret_here

# ODIS catalog information
CKAN___ODIS__CATALOG_NAME=OBIS Products Catalog
CKAN___ODIS__CATALOG_LEGAL_NAME=Ocean Biodiversity Information System (OBIS) Products Catalog
```

## Extensions Overview

| Extension | Purpose | Key Features |
|-----------|---------|--------------|
| `ckanext-obis_theme` | Custom UI/UX | Responsive homepage, statistics, dataset display |
| `ckanext-odis` | JSON-LD export | Schema.org metadata, ODIS compliance |
| `ckanext-zenodo` | Metadata schema | Custom fields, Zenodo import |
| `ckanext-doi_import` | DOI integration | Import from DOI sources |

## Useful Commands

```bash
# View logs
docker-compose -f docker-compose.dev.yml logs -f ckan-dev

# Restart CKAN
docker-compose -f docker-compose.dev.yml restart ckan-dev

# Shell access
docker exec -it obis-ckan-211-ckan-dev-1 bash

# Run CKAN commands
docker exec -it obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini [command]

# Clean rebuild
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d --build
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Test locally with Docker
4. Submit a pull request

## License

This project uses CKAN which is licensed under AGPL v3.0.

---

<details>
  <summary>📋 Detailed Setup Documentation (Click to expand)</summary>

## CKAN 2.11 Docker Setup - What We Did

### 1. Initial Setup

- Cloned the repo and checked out `obis-ckan-2.11` branch
- Copied `.env.example` to `.env`
- Updated `.env` with proper database credentials and secrets

### 2. Fixed Extension Installation Issue
Problem: Extensions in `src/` weren't being installed, causing `PluginNotFoundException`
Solution:
- Created override files in ckan/setup/:
   - `start_ckan_development.sh.override` - installs extensions from `/srv/app/src_extensions` at startup
   - `prerun.py.override` - handles database initialization
- Modified `ckan/Dockerfile.dev` to copy these override files:

```dockerfile
COPY --chown=ckan-sys:ckan-sys setup/start_ckan_development.sh.override /srv/app/start_ckan_development.sh
COPY --chown=ckan-sys:ckan-sys setup/prerun.py.override /srv/app/prerun.py
```

- Commented out the problematic volume mount in docker-compose.dev.yml:

```yaml
# - home_dir:/srv/app/  # This was overwriting our startup scripts
```

### 3. Fixed SECRET_KEY Configuration

Problem: Flask `SECRET_KEY` was missing, causing startup failure
Solution: Added to `.env`:

```
CKAN___SECRET_KEY=dev_flask_secret_key_change_in_production
CKAN___BEAKER__SESSION__SECRET=dev_secret_key_change_in_production
CKAN___API_TOKEN__JWT__ENCODE__SECRET=string:dev_jwt_encode_secret
CKAN___API_TOKEN__JWT__DECODE__SECRET=string:dev_jwt_decode_secret
```

### 4. Database Initialization and First Run

**Clean start and build:**
```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d --build
```

**Initialize database** (run once after first build):
```bash
docker exec -it obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini db init
```

**Create sysadmin user** (run once):
```bash
docker exec -it obis-ckan-211-ckan-dev-1 ckan -c /srv/app/ckan.ini sysadmin add ckan_admin email=admin@localhost name=ckan_admin
```
Enter a password when prompted (e.g., `test1234` for development).

**Restart to apply changes:**
```bash
docker-compose -f docker-compose.dev.yml restart ckan-dev
```

**Verify it's healthy:**
```bash
docker ps
```
Wait until STATUS shows `Up X seconds (healthy)`, then access CKAN at http://localhost:5000

**Note:** The datapusher token setup is currently skipped. Configure it later following the [DataStore documentation](https://docs.ckan.org/en/latest/maintaining/datastore.html#set-permissions) when needed.

### 5. Custom Schema Configuration

The OBIS CKAN instance uses a custom metadata schema defined in `ckanext-zenodo`.

**Schema configuration** is set via environment variables in `.env`:
```bash
# Dataset schema (active)
CKAN___SCHEMING__DATASET_SCHEMAS=ckanext.zenodo:zenodo_schema.yaml

# Group schema (currently disabled)
# CKAN___SCHEMING__GROUP_SCHEMAS=ckanext.zenodo:group.yaml
```

**Note:** Use `CKAN___` (3 underscores) for extension configurations with dots in the key name.

**Verify schema is loaded:**
```bash
docker exec obis-ckan-211-ckan-dev-1 grep "scheming\." /srv/app/ckan.ini
```

You should see:
```
scheming.dataset_schemas=ckanext.zenodo:zenodo_schema.yaml
```

**Testing the schema:**
1. Log in to CKAN at http://localhost:5000
2. Go to "Datasets" → "Add Dataset"
3. You should see the custom fields defined in `src/ckanext-zenodo/ckanext/zenodo/zenodo_schema.yaml`

**Modifying the schema:**
1. Edit `src/ckanext-zenodo/ckanext/zenodo/zenodo_schema.yaml`
2. Restart the container: `docker-compose -f docker-compose.dev.yml restart ckan-dev`
3. Changes will be reflected immediately (no rebuild needed)

### Key Files Changed

1. `ckan/Dockerfile.dev` - added COPY commands for override files
1. `docker-compose.dev.yml` - commented out `home_dir` volume mount
1. `.env` - added SECRET_KEY and other secrets
1. `ckan/setup/*.override` - custom startup scripts (already existed, just needed to be used)

</details>

<details>
  <summary>📖 Original Docker CKAN README (Click to expand)</summary>

# Docker Compose setup for CKAN


- [Docker Compose setup for CKAN](#docker-compose-setup-for-ckan)
  - [1.  Overview](#1--overview)
  - [2.  Installing Docker](#2--installing-docker)
  - [3.  docker compose *vs* docker-compose](#3--docker-compose-vs-docker-compose)
  - [4.  Install (build and run) CKAN plus dependencies](#4--install-build-and-run-ckan-plus-dependencies)
    - [Base mode](#base-mode)
    - [Development mode](#development-mode)
      - [Create an extension](#create-an-extension)
      - [Running HTTPS on development mode](#running-https-on-development-mode)
      - [Remote Debugging with VS Code](#remote-debugging-with-vs-code)
      - [Updating the environment file for development mode](#updating-the-environment-file-for-development-mode)
  - [5. CKAN images](#5-ckan-images)
    - [Extending the base images](#extending-the-base-images)
    - [Applying patches](#applying-patches)
    - [_uWSGI_ command line arguments](#uwsgi-command-line-arguments)
  - [6. Debugging with pdb](#6-debugging-with-pdb)
  - [7. Datastore and datapusher](#7-datastore-and-datapusher)
  - [8. NGINX](#8-nginx)
  - [9. ckanext-envvars](#9-ckanext-envvars)
  - [10. CKAN\_SITE\_URL](#10-ckan_site_url)
  - [11. Manage new users](#11-manage-new-users)
  - [12. Changing the base image](#12-changing-the-base-image)
  - [13. Replacing DataPusher with XLoader](#13-replacing-datapusher-with-xloader)
  - [Copying and License](#copying-and-license)


## 1.  Overview

This is a set of configuration and setup files to run a CKAN site.

The CKAN images used are from the official CKAN [ckan-docker](https://github.com/ckan/ckan-docker-base) repo

The non-CKAN images are as follows:

* DataPusher: CKAN's [pre-configured DataPusher image](https://github.com/ckan/ckan-docker-base/tree/main/datapusher).
* PostgreSQL: Official PostgreSQL image. Database files are stored in a named volume.
* Solr: CKAN's [pre-configured Solr image](https://github.com/ckan/ckan-solr). Index data is stored in a named volume.
* Redis: standard Redis image
* NGINX: latest stable nginx image that includes SSL and Non-SSL endpoints

The site is configured using environment variables that you can set in the `.env` file.

## 2.  Installing Docker

Install Docker by following the following instructions: [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

To verify a successful Docker installation, run `docker run hello-world` and `docker version`. These commands should output
versions for client and server.

## 3.  docker compose *vs* docker-compose

All Docker Compose commands in this README will use the V2 version of Compose ie: `docker compose`. The older version (V1)
used the `docker-compose` command. Please see [Docker Compose](https://docs.docker.com/compose/compose-v2/) for
more information.

## 4.  Install (build and run) CKAN plus dependencies

### Base mode

Use this if you are a maintainer and will not be making code changes to CKAN or to CKAN extensions

Copy the included `.env.example` and rename it to `.env`. Modify it depending on your own needs.

Please note that when accessing CKAN directly (via a browser) ie: not going through NGINX you will need to make sure you have "ckan" set up
to be an alias to localhost in the local hosts file. Either that or you will need to change the `.env` entry for CKAN_SITE_URL

Using the default values on the `.env.example` file will get you a working CKAN instance. There is a sysadmin user created by default with the values defined in `CKAN_SYSADMIN_NAME` and `CKAN_SYSADMIN_PASSWORD`(`ckan_admin` and `test1234` by default). This should be obviously changed before running this setup as a public CKAN instance.

To build the images:

	docker compose build

To start the containers:

	docker compose up

This will start up the containers in the current window. By default the containers will log direct to this window with each container
using a different colour. You could also use the -d "detach mode" option ie: `docker compose up -d` if you wished to use the current
window for something else.

Or, you can use the `bin/compose` script, which uses `docker compose` if the `docker compose` command is available, or `docker-compose` if it is not.

    ./bin/compose build
    ./bin/compose up

Note: The `./bin/compose` script will silently prepend your commands with `-f docker-compose.yml` so you can use it as a drop-in replacement for `docker-compose` or `docker compose`.

At the end of the container start sequence there should be 6 containers running

![Screenshot 2023-01-13 at 1 36 02 pm](https://user-images.githubusercontent.com/54408245/212242267-f7662c46-574c-4894-a0be-6d713adc4a72.png)

After this step, CKAN should be running at `CKAN_SITE_URL`.


### Development mode

Use this if you are making code changes to CKAN and to CKAN extensions

Copy the included `.env.example` and rename it to `.env`. Modify it depending on your own needs.

To build the images:

	docker compose -f docker-compose.dev.yml build

To start the containers:

	docker compose -f docker-compose.dev.yml up

See [CKAN Images](#ckan-images) for more details on how to add extensions or any other customizations

#### Create an extension

You can use the ckan [extension](https://docs.ckan.org/en/latest/extensions/tutorial.html#creating-a-new-extension) instructions to create a CKAN extension, only executing the command inside the CKAN container and setting the mounted `src/` folder as output:

    docker compose -f docker-compose.dev.yml exec ckan ckan generate extension --output-dir /srv/app/src_extensions

The new extension files and directories will be created in the `src/` folder in your host.

#### Running HTTPS on development mode

Sometimes is useful to run your local development instance under HTTPS, for instance if you are using authentication extensions like [ckanext-saml2auth](https://github.com/keitaroinc/ckanext-saml2auth). To enable it, set the following in your `.env` file:

    USE_HTTPS_FOR_DEV=true

and update the site URL setting:

    CKAN_SITE_URL=https://localhost:5000

After recreating the `ckan-dev` container, you should be able to access CKAN at https://localhost:5000


#### Remote Debugging with VS Code

To enable remote debugging with VS Code, you need to set the `USE_DEBUGPY` environment variable to `true` in the `.env` file. This will launch the CKAN instance with remote debugging enabled. You can then attach your VS Code debugger to the running container (use `F5` or the `Debug: Attach to CKAN` command).

You can also uncomment the example configuration in `.vscode/launch.json.example` and save it as `.vscode/launch.json` to have a pre-configured debugger ready to attach to the CKAN instance.

#### Updating the environment file for development mode

Remember to modify the `.env` file with the relevant environment variables for your setup like `CKAN_SITE_URL`, database connections or CKAN core or extension settings.

## 5. CKAN images



The Docker image config files used to build your CKAN project are located in the `ckan/` folder. There are two Docker files:

* `Dockerfile`: this is based on `ckan/ckan-base:<version>`, a base image located in the DockerHub repository, that has CKAN installed along with all its dependencies, properly configured and running on [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) (production setup)
* `Dockerfile.dev`:  this is based on `ckan/ckan-base:<version>-dev` also located located in the DockerHub repository, and extends `ckan/ckan-base:<version>` to include:

  * Any extension cloned on the `src` folder will be installed in the CKAN container when booting up Docker Compose (`docker compose up`). This includes installing any requirements listed in a `requirements.txt` (or `pip-requirements.txt`) file and running `python setup.py develop`.
  * CKAN is started running this: `/usr/bin/ckan -c /srv/app/ckan.ini run -H 0.0.0.0`.
  * Make sure to add the local plugins to the `CKAN__PLUGINS` env var in the `.env` file.

* Any custom changes to the scripts run during container start up can be made to scripts in the `setup/` directory. For instance if you wanted to change the port on which CKAN runs you would need to make changes to the Docker Compose yaml file, and the `start_ckan.sh.override` file. Then you would need to add the following line to the Dockerfile ie: `COPY setup/start_ckan.sh.override ${APP_DIR}/start_ckan.sh`. The `start_ckan.sh` file in the locally built image would override the `start_ckan.sh` file included in the base image

### Extending the base images

The CKAN base images are built from https://github.com/ckan/ckan-docker-base/

You can modify the docker files to build your own customized image tailored to your project, installing any extensions and extra requirements needed. For example here is where you would update to use a different CKAN base image ie: `ckan/ckan-base:<new version>`

To perform extra initialization steps you can add scripts to your custom images and copy them to the `/docker-entrypoint.d` folder (The folder should be created for you when you build the image). Any `*.sh` and `*.py` file in that folder will be executed just after the main initialization script ([`prerun.py`](https://github.com/ckan/ckan-docker-base/blob/main/ckan-2.9/base/setup/prerun.py)) is executed and just before the web server and supervisor processes are started.

For instance, consider the following custom image:

```
ckan
├── docker-entrypoint.d
│   └── setup_validation.sh
├── Dockerfile
└── Dockerfile.dev

```

We want to install an extension like [ckanext-validation](https://github.com/frictionlessdata/ckanext-validation) that needs to create database tables on startup time. We create a `setup_validation.sh` script in a `docker-entrypoint.d` folder with the necessary commands:

```bash
#!/bin/bash

# Create DB tables if not there
ckan -c /srv/app/ckan.ini validation init-db
```

And then in our `Dockerfile.dev` file we install the extension and copy the initialization scripts:

```Dockerfile
FROM ckan/ckan-base:2.9.7-dev

RUN pip install -e git+https://github.com/frictionlessdata/ckanext-validation.git#egg=ckanext-validation && \
    pip install -r https://raw.githubusercontent.com/frictionlessdata/ckanext-validation/master/requirements.txt

COPY docker-entrypoint.d/* /docker-entrypoint.d/
```

NB: There are a number of extension examples commented out in the Dockerfile.dev file

### Applying patches

When building your project specific CKAN images (the ones defined in the `ckan/` folder), you can apply patches
to CKAN core or any of the built extensions. To do so create a folder inside `ckan/patches` with the name of the
package to patch (ie `ckan` or `ckanext-??`). Inside you can place patch files that will be applied when building
the images. The patches will be applied in alphabetical order, so you can prefix them sequentially if necessary.

For instance, check the following example image folder:

```
ckan
├── patches
│   ├── ckan
│   │   ├── 01_datasets_per_page.patch
│   │   ├── 02_groups_per_page.patch
│   │   ├── 03_or_filters.patch
│   └── ckanext-harvest
│       └── 01_resubmit_objects.patch
├── setup
├── Dockerfile
└── Dockerfile.dev
```

### _uWSGI_ command line arguments

The images use the application server [_uWSGI_](https://uwsgi-docs.readthedocs.io/en/latest/) to run _CKAN_. There are two environment variables, that allow to configure _uWSGI_ using [command line arguments](https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html#command-line-arguments). The available options are described [here](https://uwsgi-docs.readthedocs.io/en/latest/Options.html).

For most use cases, the defaults specified in `ckan-X.XX/setup/start_ckan.sh` in `DEFAULT_UWSGI_OPTS` of the [ckan/ckan-docker-base](https://github.com/ckan/ckan-docker-base) image are fine. If required, you can either _overwrite_ the defaults or _append_ additional arguments.

| Variable            | Description                                           | Defaults           |
|:--------------------|:------------------------------------------------------| :------------------|
| `UWSGI_OPTS`        | If set, overwrites `DEFAULT_UWSGI_OPTS`. If not set, `UWSGI_OPTS` will bet set to `DEFAULT_UWSGI_OPTS`.             | unset              |
| `EXTRA_UWSGI_OPTS`  | If set, appends its content to `UWSGI_OPTS`.          | unset              |

> [!IMPORTANT]
> These setting **do not** apply for the dev images.


## 6. Debugging with pdb

Add these lines to the `ckan-dev` service in the docker-compose.dev.yml file

```yaml
stdin_open: true
tty: true
```

Debug with pdb (example) - Interact with `docker attach $(docker container ls -qf name=ckan)`

command: `python -m pdb /usr/lib/ckan/venv/bin/ckan --config /srv/app/ckan.ini run --host 0.0.0.0 --passthrough-errors`

## 7. Datastore and datapusher

The Datastore database and user is created as part of the entrypoint scripts for the db container. There is also a Datapusher container
running the latest version of Datapusher.

## 8. NGINX

The base Docker Compose configuration uses an NGINX image as the front-end (ie: reverse proxy). It includes HTTPS running on port number 8443. A "self-signed" SSL certificate is generated as part of the ENTRYPOINT. The NGINX `server_name` directive and the `CN` field in the SSL certificate have been both set to 'localhost'. This should obviously not be used for production.

Creating the SSL cert and key files as follows:
`openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj "/C=DE/ST=Berlin/L=Berlin/O=None/CN=localhost" -keyout ckan-local.key -out ckan-local.crt`
The `ckan-local.*` files will then need to be moved into the nginx/setup/ directory

## 9. ckanext-envvars

The ckanext-envvars extension is used in the CKAN Docker base repo to build the base images.
This extension checks for environmental variables conforming to an expected format and updates the corresponding CKAN config settings with its value.

For the extension to correctly identify which env var keys map to the format used for the config object, env var keys should be formatted in the following way:

  All uppercase
  Replace periods ('.') with two underscores ('__')
  Keys must begin with 'CKAN' or 'CKANEXT', if they do not you can prepend them with '`CKAN___`'

For example:

  * `CKAN__PLUGINS="envvars image_view text_view recline_view datastore datapusher"`
  * `CKAN__DATAPUSHER__CALLBACK_URL_BASE=http://ckan:5000`
  * `CKAN___BEAKER__SESSION__SECRET=CHANGE_ME`

These parameters can be added to the `.env` file

For more information please see [ckanext-envvars](https://github.com/okfn/ckanext-envvars)

## 10. CKAN_SITE_URL

For convenience the CKAN_SITE_URL parameter should be set in the .env file. For development it can be set to http://localhost:5000 and non-development set to https://localhost:8443

## 11. Manage new users

1. Create a new user from the Docker host, for example to create a new user called 'admin'

   `docker compose exec ckan ckan user add admin email=admin@localhost`

   To set this user as a sysadmin run

   `docker compose exec ckan ckan sysadmin add admin`

   To delete the 'admin' user

   `docker compose exec ckan ckan user remove admin`

   In development mode use `bin/ckan` instead of `docker compose exec ckan ckan` for the above commands.


## 12. Changing the base image

The base image used in the CKAN Dockerfile and Dockerfile.dev can be changed so a different DockerHub image is used eg: ckan/ckan-base:2.10.5 can be used instead of ckan/ckan-base:2.11.0

## 13. Replacing DataPusher with XLoader

Check out the wiki page for this: https://github.com/ckan/ckan-docker/wiki/Replacing-DataPusher-with-XLoader

Copying and License
-------------------

This material is copyright (c) 2006-2023 Open Knowledge Foundation and contributors.

It is open and licensed under the GNU Affero General Public License (AGPL) v3.0
whose full text may be found at:

http://www.fsf.org/licensing/licenses/agpl-3.0.html

</details>