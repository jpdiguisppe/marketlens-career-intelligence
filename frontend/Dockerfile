FROM node:24.16.0-alpine3.23 AS build

WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.31.3-alpine3.24

# Railway-provided build variables are available to Dockerfiles only when
# declared as ARG. Baking the source SHA into a static no-store response gives
# the production verifier a live frontend revision signal instead of inferring
# it from deployment history.
ARG RAILWAY_GIT_COMMIT_SHA=unknown

COPY nginx.conf /etc/nginx/nginx.conf.template
COPY docker-entrypoint.sh /usr/local/bin/marketlens-entrypoint.sh
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

RUN printf '%s\n' "$RAILWAY_GIT_COMMIT_SHA" > /usr/share/nginx/html/deployment-revision.txt \
    && chmod 0444 /usr/share/nginx/html/deployment-revision.txt \
    && chmod 0555 /usr/local/bin/marketlens-entrypoint.sh \
    && chown -R nginx:nginx /usr/share/nginx/html

USER nginx

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/marketlens-entrypoint.sh"]
