FROM nginx:latest

# Only copy SSL certs now, config is mounted via docker-compose
COPY selfsigned.crt /etc/ssl/certs/selfsigned.crt
COPY selfsigned.key /etc/ssl/private/selfsigned.key

# Optional: Ensure log directory exists and has correct permissions (though volume mount often handles this)
RUN mkdir -p /var/log/nginx && chown nginx:nginx /var/log/nginx
