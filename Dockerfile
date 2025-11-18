# ---
# Builder stage
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

WORKDIR /app

# Copy dependency files first for better layer caching
COPY uv.lock pyproject.toml .python-version ./

RUN uv python install

# Install dependencies before copying source code
# This layer is cached unless dependencies change
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy source code last - changes most frequently
COPY . .

# ---
# Final stage
FROM debian:bookworm-slim AS final

# Build-time arguments for configuration
ARG FAST_API_PORT=8080
ARG HOST=0.0.0.0

# Metadata labels
LABEL org.opencontainers.image.title=" ... "
LABEL org.opencontainers.image.description=" ... "
LABEL org.opencontainers.image.vendor=" ... "

# Copy only necessary files from builder
COPY --from=builder /python /python
COPY --from=builder /app /app

# Install runtime-only dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -m appuser

RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

USER appuser

WORKDIR /app

ENV PATH="/python/bin:/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV HOST=${HOST}
ENV FAST_API_PORT=${FAST_API_PORT}

EXPOSE ${FAST_API_PORT}

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
