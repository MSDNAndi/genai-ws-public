# A2A Bazaar. No secrets in this image: GENAI_API_KEY is injected at runtime (Container Apps secret).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py client.py orchestrator.py ./
RUN useradd -r -u 10001 bazaar
USER bazaar
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz',timeout=3)"
CMD ["python", "app.py"]
