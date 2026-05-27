# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
WORKDIR /app/dashboard/frontend
COPY dashboard/frontend/package.json dashboard/frontend/pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile 2>/dev/null || pnpm install
COPY dashboard/frontend/ ./
RUN pnpm build

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN pip install --no-cache-dir uv

# Install core package
COPY pyproject.toml README.md ./
COPY src/ src/
COPY examples/ examples/
RUN uv pip install --system .

# Install dashboard backend
COPY dashboard/backend/pyproject.toml dashboard/backend/
COPY dashboard/backend/src/ dashboard/backend/src/
RUN uv pip install --system ./dashboard/backend

# Copy pre-built frontend assets
COPY --from=frontend-build /app/dashboard/frontend/dist /app/dashboard/frontend/dist

EXPOSE 8091

CMD ["uvicorn", "mirrorlens_dashboard.server:app", "--host", "0.0.0.0", "--port", "8091"]
