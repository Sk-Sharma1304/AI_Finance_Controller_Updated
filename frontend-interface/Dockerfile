# AI Finance Controller — Next.js frontend
#
# Build:  docker build -t finance-controller-frontend .
# Run:    docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://api:8000 finance-controller-frontend
#
# NEXT_PUBLIC_API_URL is inlined into the client JS bundle at BUILD
# time (Next.js convention for NEXT_PUBLIC_* vars), so it must be
# passed as a build arg, not just a runtime env var, if it differs
# per environment.

FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

FROM node:20-slim AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

ENV NODE_ENV=production
ENV PORT=3000

# Standalone output: a pruned node_modules + server.js, no need to
# copy the full dependency tree into the final image.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', r => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
