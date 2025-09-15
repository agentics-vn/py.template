# ---
# Builder stage
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

WORKDIR /app

COPY uv.lock pyproject.toml .python-version ./

RUN uv python install

# Cache uv dependencies install
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

COPY . .

# Sync prod dependencies without dev packages
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---
# Final stage
FROM debian:bookworm-slim AS final

# Copy only necessary files from builder
COPY --from=builder /python /python
COPY --from=builder /app /app

# Install runtime-only dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl && \
        ca-certificates \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=0.0.0.0
ENV FAST_API_PORT=8080

EXPOSE 8080

ENTRYPOINT ["python", "main.py"]
