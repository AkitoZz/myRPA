### Build stage ###
FROM node:18-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY package.json package-lock.json* ./

# Install all dependencies (including devDependencies needed for build)
RUN npm ci --prefer-offline 2>/dev/null || npm install

# Copy the rest of the source code
COPY . .

# Build for production
RUN npm run build

### Production stage ###
FROM nginx:1.25-alpine

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy built Vue3 SPA from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy a minimal fallback nginx config (will be overridden by docker-compose volume mount)
RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

# Nginx runs as the main process
CMD ["nginx", "-g", "daemon off;"]
