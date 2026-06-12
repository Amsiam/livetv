FROM node:22-alpine AS web-build

WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
ENV VITE_API_BASE_URL=/v1
RUN npm run build

FROM nginx:1.27-alpine

COPY deploy/nginx/livetv.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /web/dist /var/www/livetv-web
