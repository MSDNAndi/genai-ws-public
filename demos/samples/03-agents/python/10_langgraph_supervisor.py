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
# # 10 - Supervisor graph (LangGraph)
#
# | | |
# |---|---|
# | **Pattern** | supervisor: an LLM router decides which worker runs next, until it says FINISH |
# | **Communication** | **shared graph state** - every node reads the state and returns an update to it |
# | **Use when** | the order of steps depends on the content, and you want the routing inspectable |
# | **Watch out** | an LLM router can loop. Never let the model own termination alone - cap it in code |
#
# Compare three ways to coordinate the same kind of team:
#
# * sample 04 (handoff) - agents pass control to each other, no centre;
# * sample 06 (agent-as-tool) - a centre calls workers as functions, inside one agent loop;
# * this one - a centre routes between workers as **graph nodes**, so every step
#   is a checkpointed state transition you can inspect, replay or pause.
#
# ```bash
# uv run 10_langgraph_supervisor.py --profile mock
# ```

# %%
from typing import Literal

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command
from pydantic import BaseModel

from genaiclass import banner, get_profile, langchain_model

profile = get_profile()
print(banner(profile))
model = langchain_model(profile)

WORKERS = ("researcher", "writer")
MAX_STEPS = 4


# %% [markdown]
# ## The shared state
#
# `MessagesState` gives a `messages` list that nodes *append* to. We add the
# bookkeeping the supervisor needs. This dict is the only channel between nodes -
# nothing is passed any other way, which is why it can be checkpointed.

# %%
class TeamState(MessagesState):
    done: list[str]
    steps: int


# %% [markdown]
# ## Workers are ordinary LangChain agents
#
# Each becomes a node: read the state, run, append the answer (tagged with its
# name so the supervisor can see who said what).

# %%
researcher = create_agent(model, tools=[], name="researcher",
                          system_prompt="You are a researcher. List three key facts, one line each.")
writer = create_agent(model, tools=[], name="writer",
                      system_prompt="You are a writer. Turn the facts above into one short paragraph.")


def worker_node(name: str, agent):
    def run(state: TeamState) -> dict:
        result = agent.invoke({"messages": state["messages"]})
        answer = result["messages"][-1]
        answer.name = name
        return {"messages": [answer], "done": state["done"] + [name]}
    return run


# %% [markdown]
# ## The supervisor: model proposes, code disposes
#
# The model picks the next worker via structured output (a `Literal`, so it can
# only name a real node). Then plain code enforces the rules the model must not
# be trusted with: no worker twice, and a hard step limit. `Command(goto=...)`
# is how a node chooses the next edge at runtime.

# %%
class Route(BaseModel):
    next: Literal["researcher", "writer", "FINISH"]


router = model.with_structured_output(Route)


def supervisor(state: TeamState) -> Command[Literal["researcher", "writer", "__end__"]]:
    if state["steps"] >= MAX_STEPS or set(state["done"]) >= set(WORKERS):
        print("  supervisor -> FINISH (all done / step limit)")
        return Command(goto=END)

    proposal = router.invoke([
        {"role": "system", "content": f"You manage {', '.join(WORKERS)}. Research first, then write. "
                                      f"Already done: {state['done'] or 'nothing'}. Pick who acts next, "
                                      "or FINISH."},
        *state["messages"],
    ]).next

    choice = proposal
    if choice == "FINISH" or choice in state["done"]:  # guard: no repeats, no early exit
        choice = next(w for w in WORKERS if w not in state["done"])
    print(f"  supervisor: model proposed {proposal!r} -> routing to {choice!r}")
    return Command(goto=choice, update={"steps": state["steps"] + 1})


# %% [markdown]
# ## Wire it up
#
# Workers always report back to the supervisor. The supervisor's `Command`
# decides everything else - so the graph has no fixed path through it.

# %%
graph = StateGraph(TeamState)
graph.add_node("supervisor", supervisor)
for name, agent in (("researcher", researcher), ("writer", writer)):
    graph.add_node(name, worker_node(name, agent))
    graph.add_edge(name, "supervisor")
graph.add_edge(START, "supervisor")
app = graph.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "brief-1"}}
final = app.invoke(
    {"messages": [{"role": "user", "content": "Brief me on the Lisbon tram network."}],
     "done": [], "steps": 0},
    config,
)
print()
for message in final["messages"][1:]:
    print(f"[{message.name}] {message.content[:110]}")

# %% [markdown]
# ## Every step was saved
#
# The checkpointer kept a snapshot after each node. That history is what makes
# LangGraph graphs debuggable - and resumable, which sample 11 uses.

# %%
history = list(app.get_state_history(config))
print(f"\n{len(history)} checkpoints for thread 'brief-1':")
for snapshot in reversed(history):
    print(f"  after {str(snapshot.metadata.get('source')):<6} next={list(snapshot.next)}")
