# syntax=docker/dockerfile:1.7

#############################################################
# Stage 1: build a wheel cache from pyproject.toml
#############################################################
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip setuptools wheel \
    && pip wheel --wheel-dir /wheels .


#############################################################
# Stage 2: runtime — slim image, non-root user, no toolchain
#############################################################
FROM python:3.12-slim AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system bot && useradd --system --gid bot --create-home bot

COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links /wheels event-flats-bot \
    && rm -rf /wheels

USER bot
WORKDIR /home/bot

# No fixed ENTRYPOINT — the same image runs either bot. Pick one with
# `command: ["python", "-m", "event_flats_bot.admin"]` or `.client` in
# your compose file / k8s manifest.
CMD ["python", "-m", "event_flats_bot.client"]
