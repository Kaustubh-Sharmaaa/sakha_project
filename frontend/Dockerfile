FROM nginx:alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/config.js  /usr/share/nginx/html/config.js
COPY index.html          /usr/share/nginx/html/index.html
COPY app.js              /usr/share/nginx/html/app.js
COPY style.css           /usr/share/nginx/html/style.css

EXPOSE 80
