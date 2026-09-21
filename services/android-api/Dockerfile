# Strlix android-api — chat/voice/a11y BFF (no ADB)
# Build from repo root:
#   docker build -f services/android-api/Dockerfile -t android-api:local .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY packages/common /app/packages/common
COPY services/android-api /app/services/android-api

RUN pip install --upgrade pip \
 && pip install /app/packages/common \
 && pip install --no-deps /app/services/android-api \
 && pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0" "openai>=1.55.0" \
      "httpx>=0.27.0" "python-dotenv>=1.0.0" "pydantic>=2.0.0" "pydantic-settings>=2.0.0" "PyJWT[crypto]>=2.8.0"

WORKDIR /app/services/android-api
ENV PYTHONPATH=/app/packages/common:/app/services/android-api

# Optional empty .env so load_dotenv doesn't warn; secrets from env vars
RUN touch /app/.env && ln -sf /app/.env /app/services/android-api/../../.env 2>/dev/null || true
# Ensure ROOT (.parents[3] from android_api/main.py) resolves: 
# main.py -> android_api/ -> services/android-api/ -> services/ -> /app  == parents[3]
# Wait: Path(__file__).parents[0]=android_api, [1]=services/android-api, [2]=services, [3]=/app
# So ROOT=/app — put .env at /app/.env
RUN touch /app/.env

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)" || exit 1

CMD ["uvicorn", "android_api.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
