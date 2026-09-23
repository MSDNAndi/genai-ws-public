"""Lab 3 · step 5 — see what the agent actually did: OpenTelemetry spans (the GenAI semantic conventions).

configure_otel_providers(enable_console_exporters=True) prints ~1,500 lines per run. For the lab we plug in a tiny
exporter that prints one line per span instead. In production you point the same spans at Application Insights,
Aspire, Jaeger or Langfuse (OTEL_EXPORTER_OTLP_ENDPOINT) — no code change.
"""
import asyncio
import json

from agent_framework import Agent, tool
from agent_framework.observability import configure_otel_providers
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from lab3_common import OPTIONS, chat_client


class OneLinePerSpan(SpanExporter):
    def export(self, spans):
        for s in spans:
            a = dict(s.attributes or {})
            tokens = (f"  tokens in={a.get('gen_ai.usage.input_tokens')} out={a.get('gen_ai.usage.output_tokens')}"
                      if "gen_ai.usage.input_tokens" in a else "")
            tool_args = f"  args={a.get('gen_ai.tool.call.arguments')}" if "gen_ai.tool.call.arguments" in a else ""
            print(f"  span {s.name:<34} {(s.end_time - s.start_time) / 1e6:8.0f} ms{tokens}{tool_args}")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


# >>> TODO 3: switch tracing on with our exporter (and sensitive data, so tool arguments show up)
configure_otel_providers(exporters=[OneLinePerSpan()], enable_sensitive_data=True, service_name="bsgai-lab3")
# <<< TODO


@tool
def get_weather(city: str) -> str:
    """Current weather for a city."""
    return json.dumps({"city": city, "temp_c": 22, "sky": "sunny"})


async def main() -> None:
    agent = Agent(client=chat_client(), name="WeatherAgent", tools=[get_weather], default_options=OPTIONS,
                  instructions="Use the tool. One sentence.")
    print((await agent.run("Weather in Mannheim?")).text.strip())


asyncio.run(main())
trace.get_tracer_provider().force_flush()                 # spans are exported in batches - flush before exit
