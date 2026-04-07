FROM nginx:stable-alpine

ENV NGINX_DIR=/etc/nginx

RUN apk update --no-cache && \
    apk upgrade --no-cache && \
    apk add --no-cache openssl python3 py3-pip && \
    pip3 install mkdocs-material --break-system-packages

COPY nginx/setup/nginx.conf ${NGINX_DIR}/nginx.conf
COPY nginx/setup/index.html /usr/share/nginx/html/index.html
COPY nginx/setup/error.html /usr/share/nginx/html/error.html
COPY nginx/setup/robots.txt /usr/share/nginx/html/robots.txt
COPY nginx/setup/default.conf ${NGINX_DIR}/conf.d/

# Build MkDocs site
COPY docs/ /tmp/docs/
COPY mkdocs.yml /tmp/mkdocs.yml
RUN cd /tmp && mkdocs build --config-file mkdocs.yml && \
    mv /tmp/site /usr/share/nginx/html/docs

RUN mkdir -p ${NGINX_DIR}/certs

ENTRYPOINT \
  openssl req \
    -subj '/C=DE/ST=Berlin/L=Berlin/O=None/CN=localhost' \
    -x509 -newkey rsa:4096 \
    -nodes -keyout /etc/nginx/ssl/default_key.pem \
    -keyout ${NGINX_DIR}/certs/ckan-local.key \
    -out ${NGINX_DIR}/certs/ckan-local.crt \
    -days 365 && \
  nginx -g 'daemon off;'
