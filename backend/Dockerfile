FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/deploy.txt
COPY --chown=app:app . .
USER app
EXPOSE 8000
# Deliberately no automatic migration, seeding, reset, or grant provisioning.
CMD ["sh", "scripts/start_web.sh"]
