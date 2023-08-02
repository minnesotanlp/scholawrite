FROM alpine:latest

LABEL MAINTAINER="Ryan Koo kooryan03@gmail.com"

RUN apk --update add nginx && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log && \
    mkdir /etc/nginx/sites-enabled/ && \
    mkdir -p /run/nginx && \
    rm -rf /etc/nginx/http.d/default.conf && \
    rm -rf /var/cache/apk/*

COPY conf.d/app.conf /etc/nginx/http.d/app.conf

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]