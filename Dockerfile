FROM python:3.14-slim

# Links the published image to the repository, so it shares its access.
LABEL org.opencontainers.image.source=https://github.com/altoquepay/altoquepay-backend
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini .
COPY alembic alembic
COPY app app

USER nobody
EXPOSE 8000
# Migrates before serving, which is safe while a single API container runs.
CMD ["sh", "-c", "alembic upgrade head && exec fastapi run app/main.py --port 8000"]
