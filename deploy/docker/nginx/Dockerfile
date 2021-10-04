FROM nginxinc/nginx-unprivileged:1-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d
COPY uwsgi_params /etc/nginx/uwsgi_params

USER root

# setup static dirs
RUN mkdir -p /vol/static
RUN chmod 755 /vol/static

USER nginx


# CMD ["nginx", "-g", "daemon off;"]
