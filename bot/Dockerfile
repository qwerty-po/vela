FROM python:3.13-slim AS builder

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

WORKDIR /app

# Copy dependency file(s) first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies in a separate layer
RUN uv sync --frozen

# Copy application source code
COPY . .

FROM python:3.13-slim AS runtime

RUN useradd --create-home appuser
USER appuser

WORKDIR /app

COPY --from=builder /app /app/

CMD [".venv/bin/python", "main.py"]