# Stage 1: Build dependencies using uv base image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

WORKDIR /app

# Install git (needed for git dependencies like py-jama-rest-client)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-editable

# Stage 2: Final runtime image
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Add installed package executables to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set the default command to run the server script
# This script is defined in pyproject.toml
ENTRYPOINT ["jama-mcp-server"]