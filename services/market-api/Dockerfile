FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8080
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY services/market-api /app/services/market-api
COPY web-market /app/web-market
COPY static/legal /app/static/legal
RUN pip install --upgrade pip && pip install /app/services/market-api \
 && mkdir -p /workspace && ln -sfn /app /workspace/zevi-cloudphone
WORKDIR /app/services/market-api
ENV PYTHONPATH=/app/services/market-api
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)" || exit 1
CMD ["uvicorn", "market_api.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
