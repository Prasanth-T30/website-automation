FROM node:22-alpine AS build

# Baked in at build time by Vite. Point it at the API origin the public form
# should talk to; the default assumes a reverse proxy putting the API on the
# same host under /api/v1.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

WORKDIR /srv
RUN corepack enable

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

COPY . .
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=build /srv/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
