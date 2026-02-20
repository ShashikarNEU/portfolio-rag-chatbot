FROM python:3.13-slim

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (cached layer — only rebuilds when lockfile changes)
COPY pyproject.toml uv.lock ./
RUN touch README.md && uv sync --frozen --no-dev

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
