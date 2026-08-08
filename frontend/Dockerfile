FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/nginx.conf.template
COPY docker-entrypoint.sh /usr/local/bin/marketlens-entrypoint.sh
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

RUN chmod 0555 /usr/local/bin/marketlens-entrypoint.sh \
    && chown -R nginx:nginx /usr/share/nginx/html

USER nginx

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/marketlens-entrypoint.sh"]
