# The frontend is a static bundle. Node builds it; nginx serves it. Node is
# not in the final image at all - there is nothing for it to do at runtime,
# and leaving it out removes an entire class of dependency vulnerability from
# the thing that faces the internet.
FROM node:22-alpine AS builder

WORKDIR /app

# Dependencies first, so a source-only change does not reinstall them.
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Vite inlines env at build time, so the API address is a build argument
# rather than a runtime one. A different backend means a rebuild; that is
# how a static bundle works.
ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ARG VITE_SITE_URL=http://localhost:8080
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_SITE_URL=$VITE_SITE_URL

RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1
