# -------------------------
# Stage 1: Build
# Needs node plus the whole dev toolchain (typescript, sass).
# -------------------------
FROM node:24-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY build.js ./
RUN npm run build

# -------------------------
# Stage 2: Production
# Only the built dist/ folder is carried over. No node, no npm, no toolchain.
# -------------------------
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
