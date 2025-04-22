FROM nginx:latest

COPY default.conf /etc/nginx/conf.d/default.conf
COPY selfsigned.crt /etc/ssl/certs/selfsigned.crt
COPY selfsigned.key /etc/ssl/private/selfsigned.key
