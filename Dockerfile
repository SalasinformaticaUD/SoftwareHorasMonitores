FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /build/requirements.txt

RUN pip install --upgrade pip wheel \
    && pip wheel --wheel-dir /wheels -r /build/requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app \
    && adduser --system --ingroup app app

COPY requirements.txt /tmp/requirements.txt
COPY --from=builder /wheels /wheels

RUN pip install --upgrade pip \
    && pip install --no-index --find-links=/wheels -r /tmp/requirements.txt \
    && rm -rf /wheels /tmp/requirements.txt

COPY . /app

RUN mkdir -p /app/dropzone /app/media /app/staticfiles \
    && chmod +x /app/docker/entrypoint.sh \
    && chown -R app:app /app

USER app

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
