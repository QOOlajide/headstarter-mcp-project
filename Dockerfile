# Transcript / scheduling FastAPI hub (always-on webhook for Meet captions).
# MCP scheduling still runs via Cursor locally — this image is the HTTP inbox.

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Do not bake secrets into the image — pass via host env / .env at runtime.
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
