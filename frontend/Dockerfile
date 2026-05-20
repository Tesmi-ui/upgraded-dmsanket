# ============================================================================
# FRONTEND DOCKERFILE
# ============================================================================
# Multi-stage build: Node (build) → Nginx (serve)
# ============================================================================

FROM node:18-alpine AS build

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy app code
COPY . .

# Build for production
RUN npm run build

# ── Production image with nginx ──────────────────────────────────────────

FROM nginx:alpine

# Install wget for health checks
RUN apk add --no-cache wget

# Copy built files to nginx
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --spider -q http://localhost:3000/ || exit 1

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
