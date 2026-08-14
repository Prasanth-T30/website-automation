FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Dependency layer first so code edits don't invalidate the install cache.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY . .

RUN useradd --create-home --uid 1000 app && chown -R app:app /srv
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"

# Firestore is schemaless — there is no migration step to run before serving.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
