# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "genaiclass",
#     "langchain==1.4.2",
#     "langchain-openai==1.6.2",
#     "langgraph==1.2.11",
# ]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 09 - One agent (LangChain)
#
# | | |
# |---|---|
# | **Pattern** | single agent: model + tools + middleware |
# | **Communication** | request/response; state is a dict of `messages` you pass in and get back |
# | **Use when** | you are in the LangChain ecosystem, or want its middleware and 1000+ integrations |
# | **Watch out** | `create_agent` replaced `create_react_agent` in LangChain 1.0 - most tutorials still show the old one |
#
# The twin of sample 01, in the other big ecosystem. Same loop underneath; the
# difference is style. MAF gives you an `Agent` object with a session. LangChain
# gives you a compiled graph that takes a state dict and returns a new one.
#
# There is no C# twin: LangChain has Python and JavaScript SDKs only.
#
# ```bash
# uv run 09_langchain_agent.py --profile mock
# ```

# %%
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from genaiclass import banner, get_profile, langchain_model

profile = get_profile()
print(banner(profile))
# `langchain_model` = ChatOpenAI(model=..., base_url=..., api_key=...).
model = langchain_model(profile)


# %% [markdown]
# ## Tools: the docstring is the description

# %%
@tool
def get_route(origin: str, destination: str) -> dict:
    """How far it is and how long it takes to drive between two places."""
    return {"origin": origin, "destination": destination, "distance_km": 42.0, "duration_min": 35}


@tool
def get_current_weather(location: str) -> dict:
    """Current weather conditions for one place."""
    return {"location": location, "temperature_c": 18, "conditions": "light rain"}


# %% [markdown]
# ## Middleware: policy around the loop
#
# LangChain 1.x's extension point. A middleware sees every model call and can
# log, redact, cap, summarise or ask a human. Prebuilt ones include
# `PIIMiddleware`, `SummarizationMiddleware` and `HumanInTheLoopMiddleware`.
# This one just counts model calls - enough to make the loop visible.

# %%
class CountModelCalls(AgentMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def before_model(self, state, runtime):
        self.calls += 1
        print(f"  (model call #{self.calls}, {len(state['messages'])} messages in state)")
        return None


counter = CountModelCalls()

# %% [markdown]
# ## Memory is a checkpointer plus a thread id
#
# Where MAF has `agent.create_session()`, LangGraph has a **checkpointer** that
# saves the state after every step, keyed by `thread_id`. `InMemorySaver` for
# demos; Postgres/SQLite/Redis savers for real use - and a checkpoint is also
# what lets a run pause and resume (sample 11).

# %%
agent = create_agent(
    model,
    tools=[get_route, get_current_weather],
    system_prompt="You are a travel assistant. Use the tools; never guess numbers. Be brief.",
    middleware=[counter],
    checkpointer=InMemorySaver(),
    name="travel",
)

thread = {"configurable": {"thread_id": "ada"}}

result = agent.invoke(
    {"messages": [{"role": "user", "content": "How far is Bellevue to Redmond, and the weather there?"}]},
    thread,
)
for message in result["messages"]:
    kind = type(message).__name__.replace("Message", "")
    text = message.content if isinstance(message.content, str) else ""
    calls = [c["name"] for c in getattr(message, "tool_calls", []) or []]
    print(f"  {kind:<6} {text[:80] or calls}")

# %%
follow_up = agent.invoke({"messages": [{"role": "user", "content": "Thanks! Which city was that?"}]},
                         thread)
print(f"\nsame thread -> {follow_up['messages'][-1].content}")
