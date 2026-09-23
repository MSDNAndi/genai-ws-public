# Mirrors microsoft-foundry/foundry-samples .../langgraph/responses/01-langgraph-chat
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt main.py langgraph.json ./
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m compileall -q .

EXPOSE 8088
CMD ["python", "-m", "langchain_azure_ai.agents.hosting.run", "--protocol", "responses"]
