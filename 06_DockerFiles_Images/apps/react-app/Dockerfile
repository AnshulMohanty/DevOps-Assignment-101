# Stage 1: install React + esbuild and bundle the app
FROM node:24-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY src ./src
RUN npm run build

# Stage 2: serve the built bundle only
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY --from=builder /app/dist/bundle.js /usr/share/nginx/html/bundle.js
EXPOSE 80
