# Nginx site config for cda.enduhub.com (Streamlit CdA Kalkulator)
# Szczegóły wdrożenia: README.md (sekcja Deploy)

include /etc/nginx/bots.conf;

# Rate limiting — własne strefy (cda_*), żeby nie kolidować z p3.enduhub.com
limit_req_zone $binary_remote_addr zone=cda_general_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=cda_api_limit:10m rate=5r/s;
limit_req_status 429;

server {
    server_name cda.enduhub.com;

    charset utf8;
    client_max_body_size 50M;
    add_header Strict-Transport-Security max-age=15768000 always;

    # BLOKOWANIE SPAMERSKICH IP
    deny 207.46.13.210;
    deny 149.115.239.38;

    # BLOKOWANIE BOTÓW (zmienna $block_ua)
    if ($block_ua) {
        return 444;
    }

    # Blokowanie spamerskich krajów
    if ($allowed_country = no) {
        return 444;
    }

    error_page 502 /50x.html;

    location / {
        limit_req zone=cda_general_limit burst=20 nodelay;
        limit_req_status 429;

        # Streamlit — dedykowany port (8502, żeby nie kolidować z dev na 8501)
        proxy_pass http://127.0.0.1:8502;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Streamlit WebSocket / długie sesje
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

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/cda.enduhub.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/cda.enduhub.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if ($host = cda.enduhub.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    server_name cda.enduhub.com;
    listen 80;
    return 404; # managed by Certbot
}
