# Nginx site config for cda.enduhub.com (Streamlit CdA Kalkulator)
# Szczegóły wdrożenia: README.md (sekcja Deploy)
#
# /           → statyczny landing (SEO)
# /app/       → Streamlit (baseUrlPath=app w .streamlit/config.toml)

include /etc/nginx/bots.conf;

limit_req_zone $binary_remote_addr zone=cda_general_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=cda_api_limit:10m rate=5r/s;

server {
    server_name cda.enduhub.com;

    charset utf8;
    client_max_body_size 50M;
    add_header Strict-Transport-Security max-age=15768000 always;

    deny 207.46.13.210;
    deny 149.115.239.38;

    if ($block_ua) {
        return 444;
    }

    if ($allowed_country = no) {
        return 444;
    }

    error_page 502 /50x.html;

    root /home/enduhub/enduhub.com/cda/landing;

    location = / {
        try_files /index.html =404;
    }

    location = /en {
        return 301 /en/;
    }

    location = /en/ {
        try_files /en/index.html =404;
    }

    location = /landing.css {
        try_files /landing.css =404;
        expires 7d;
        access_log off;
    }

    location = /robots.txt {
        try_files /robots.txt =404;
        access_log off;
    }

    location = /sitemap.xml {
        try_files /sitemap.xml =404;
        access_log off;
    }

    location /app/ {
        limit_req zone=cda_general_limit burst=20 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8502/app/;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        proxy_connect_timeout 60s;
        proxy_buffering off;
    }

    location = /50x.html {
        alias /home/enduhub/enduhub.com/p3/staticfiles_collected/endu/502.html;
        internal;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/cda.enduhub.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cda.enduhub.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    listen 80;
    server_name cda.enduhub.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
