# Frontend served by FastAPI - simple nginx for production
FROM nginx:alpine

# Copy HTML files (served by backend, this is just for caching/static)
COPY index.html /usr/share/nginx/html/
COPY dashboard.html /usr/share/nginx/html/
COPY route.html /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]