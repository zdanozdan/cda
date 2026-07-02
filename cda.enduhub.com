# Nginx site config for cda.enduhub.com (Streamlit CdA Kalkulator)
# Szczegóły wdrożenia: README.md (sekcja Deploy)
#
# Pierwszy deploy bez certu: zakomentuj blok HTTPS i użyj proxy na :80 — patrz README.

include /etc/nginx/bots.conf;

# Rate limiting — własne strefy (cda_*), żeby nie kolidować z p3.enduhub.com
# limit_req_status 429 jest ustawione globalnie w p3.enduhub.com (tylko raz w http {})
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

    location / {
        limit_req zone=cda_general_limit burst=20 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8502;

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

    location /robots.txt {
        alias /var/www/enduhub/robots.txt;
        access_log off;
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
