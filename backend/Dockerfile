FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --system --uid 10001 app \
    && mkdir -p /app/uploads/logos \
    && chown -R app /app/uploads
USER app

EXPOSE 8000

# One worker only: the warmup scheduler runs in-process, so extra workers would
# each run the hourly job and send duplicate emails.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
