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

# Cloud Run injects PORT (8080 by default) and sends traffic there. A container
# listening anywhere else never passes its readiness check and the revision is
# rolled back. PORT is unset locally, so this default keeps compose working.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://localhost:%s/health' % os.environ.get('PORT','8000'))"

# Shell form, so ${PORT} is expanded at run time instead of being passed as a
# literal string. `exec` keeps uvicorn as PID 1 so it receives SIGTERM and
# drains cleanly when Cloud Run scales the instance down.
# Firestore is schemaless — there is no migration step to run before serving.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
