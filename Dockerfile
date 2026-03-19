FROM python:3.12-slim-bookworm

ARG SIMPPLR_TOKEN

# Install curl, git (for private repo deps), and ensure CA certificates are present (fixes SSL "UnknownIssuer" in some environments)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

COPY ./src/ ./src
COPY master_config.yaml pyproject.toml uv.lock ./

# Create a project virtualenv that inherits system site-packages (for preinstalled deps)
RUN python3 -m venv /app/.venv --system-site-packages

# Use the project virtualenv
ENV PATH="/app/.venv/bin:${PATH}"

# Optional: set UV_SSL_NO_VERIFY=1 when building behind a corporate proxy with SSL inspection
# e.g. docker build --build-arg UV_SSL_NO_VERIFY=1 -t ai-infra-example-agent:latest .
# ARG UV_SSL_NO_VERIFY=
# ENV UV_SSL_NO_VERIFY=${UV_SSL_NO_VERIFY}

RUN git config --global url."https://${SIMPPLR_TOKEN}@github.com/".insteadOf "https://github.com/" && \
    uv sync --frozen --no-cache --no-dev

# Expose the port
EXPOSE 5000

RUN mkdir -p \
    /app/.local \
    /app/.cache \
    /app/.config && \
    chmod -R 777 /app/.local /app/.cache /app/.config

# Set environment variables to redirect data storage to writable locations
ENV HOME=/app
ENV XDG_DATA_HOME=/app/.local/share
ENV XDG_CACHE_HOME=/app/.cache
ENV XDG_CONFIG_HOME=/app/.config
# Set TMPDIR to /tmp (will be mounted as writable volume in Kubernetes)
# CrewAI and Python tempfile module need this for temporary files
ENV TMPDIR=/tmp
ENV TMP=/tmp
ENV TEMP=/tmp

# Health check
# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:5000/health || exit 1

CMD ["uvicorn", "agent.api:app", "--host", "0.0.0.0", "--port", "5000"]
