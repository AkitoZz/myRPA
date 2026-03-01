FROM node:18-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY package.json package-lock.json* ./

# Install all dependencies (including devDependencies for potential build steps)
RUN npm ci --prefer-offline 2>/dev/null || npm install

# ---- Production stage ----
FROM node:18-alpine

WORKDIR /app

# Add a non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy dependency manifests
COPY package.json package-lock.json* ./

# Install production dependencies only
RUN npm ci --omit=dev --prefer-offline 2>/dev/null || npm install --production \
    && npm cache clean --force

# Copy application source
COPY app.js ./
COPY server.js ./
COPY config/ ./config/
COPY controllers/ ./controllers/
COPY database/ ./database/
COPY middlewares/ ./middlewares/
COPY models/ ./models/
COPY routes/ ./routes/
COPY services/ ./services/
COPY websocket/ ./websocket/

# Create logs directory
RUN mkdir -p /app/logs && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "server.js"]
