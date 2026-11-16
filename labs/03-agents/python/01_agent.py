"""Lab 3 · step 1 — an agent is the Lab 1 tool loop + a runtime: instructions, tools, memory (a session), a budget.

Agent = model + instructions + tools, run in a loop: the model asks for a tool, the framework calls it, the model
reads the result - until it can answer. What to notice: "And what is that in Fahrenheit?" only works because the
session remembers Mannheim. The last call has no session, so the agent cannot know what "that" is.
"""
import asyncio
import json

from agent_framework import Agent, tool

from lab3_common import OPTIONS, chat_client

FAKE_WEATHER = {"paris": (19, "light rain"), "mannheim": (22, "sunny"), "jacksonville": (31, "thunderstorms")}


# @tool = a Python function the model may call. Name, type hints and docstring become the tool description.
@tool
def get_weather(city: str) -> str:
    """Current weather for a city (temperature in Celsius and sky)."""
    temp, sky = FAKE_WEATHER.get(city.lower(), (20, "unknown"))
    return json.dumps({"city": city, "temp_c": temp, "sky": sky})


@tool
def to_fahrenheit(celsius: float) -> str:
    """Convert Celsius to Fahrenheit."""
    return json.dumps({"fahrenheit": round(celsius * 9 / 5 + 32, 1)})


async def main() -> None:
    # Agent = model connection + job description (instructions) + tools. It runs the tool loop for us.
    agent = Agent(client=chat_client(), name="WeatherAgent", default_options=OPTIONS,
                  instructions="You are a travel assistant. Use the tools for facts; answer in one or two sentences.",
                  tools=[get_weather, to_fahrenheit])
    session = agent.create_session()                      # the conversation memory lives here
    for question in ["What's the weather in Mannheim?", "And what is that in Fahrenheit?", "Which city did I ask about?"]:
        response = await agent.run(question, session=session)   # one whole loop: tool calls + final answer
        print(f"> {question}\n  {response.text.strip()}")
    # No session -> no memory: the agent cannot know what "that" refers to.
    print("\nWithout the session:", (await agent.run("And what is that in Fahrenheit?")).text.strip()[:160])


asyncio.run(main())
