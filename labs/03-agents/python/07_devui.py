"""Lab 3 · stretch — Agent Framework DevUI: chat with your agents and workflows in the browser and inspect every step.

pip install -r ../../../requirements-extras.txt     (agent-framework-devui, beta)
python 07_devui.py                                  -> http://127.0.0.1:8090  (Ctrl+C to stop)
"""
import asyncio
import json

from agent_framework import Agent, tool
from agent_framework.devui import serve
from agent_framework.orchestrations import SequentialBuilder

from lab3_common import OPTIONS, chat_client


@tool
def get_weather(city: str) -> str:
    """Current weather for a city."""
    return json.dumps({"city": city, "temp_c": 22, "sky": "sunny"})


client = chat_client()
weather = Agent(client=client, name="WeatherAgent", tools=[get_weather], default_options=OPTIONS,
                instructions="Use the tool. Be brief.")
poet = Agent(client=client, name="poet", default_options=OPTIONS, instructions="Turn the previous answer into a haiku.")
pipeline = SequentialBuilder(participants=[weather, poet]).build()

# auth_enabled=False is fine on localhost; with auth on, the token is only printed at INFO log level
serve(entities=[weather, pipeline], port=8090, auto_open=True, auth_enabled=False)
