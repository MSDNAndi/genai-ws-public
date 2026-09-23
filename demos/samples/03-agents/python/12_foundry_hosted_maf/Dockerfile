# Mirrors microsoft-foundry/foundry-samples .../agent-framework/responses/01-basic
# The platform requires linux/amd64 and serves the container on port 8088.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt main.py ./
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m compileall -q .

EXPOSE 8088
CMD ["python", "main.py"]
