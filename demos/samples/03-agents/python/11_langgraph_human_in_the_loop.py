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
# # 11 - Human in the loop (LangGraph interrupt / resume)
#
# | | |
# |---|---|
# | **Pattern** | approval gate: the agent pauses before an irreversible action and waits for a person |
# | **Communication** | **pause and resume through a checkpoint** - the run stops, state is saved, a human answers later, the run continues |
# | **Use when** | sending, paying, deleting, publishing - anything you cannot take back |
# | **Watch out** | the pause can last hours: state must be in a durable checkpointer, not in memory, in production |
#
# The key idea is that "waiting for a human" is not a blocking `input()` call.
# The graph **returns** with an interrupt, the process can exit, and a completely
# different process can resume it later from the checkpoint - that is what makes
# approvals work behind a web UI or a Teams card.
#
# ```bash
# uv run 11_langgraph_human_in_the_loop.py --profile mock
# ```

# %%
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, interrupt

from genaiclass import banner, get_profile, langchain_model

profile = get_profile()
print(banner(profile))
model = langchain_model(profile)


# %% [markdown]
# ## Three nodes: draft, approve, send
#
# `interrupt(payload)` inside a node stops the run and hands `payload` to the
# caller. When the run is resumed, the same `interrupt` call *returns* the
# human's answer and the node carries on from there.

# %%
class EmailState(MessagesState):
    draft: str
    sent: bool


def draft(state: EmailState) -> dict:
    reply = model.invoke([
        {"role": "system", "content": "You are an assistant. Draft a two-sentence email."},
        *state["messages"],
    ])
    return {"draft": reply.content}


def approve(state: EmailState) -> Command:
    decision = interrupt({"action": "send_email", "draft": state["draft"],
                          "question": "Send this? Answer 'yes', 'no', or an edited text."})
    if decision == "yes":
        return Command(goto="send")
    if decision == "no":
        return Command(goto=END, update={"sent": False})
    return Command(goto="send", update={"draft": decision})  # human edited it


def send(state: EmailState) -> dict:
    print(f"  >>> SENDING: {state['draft'][:80]}")  # the irreversible side effect
    return {"sent": True}


graph = StateGraph(EmailState)
graph.add_node("draft", draft)
graph.add_node("approve", approve)
graph.add_node("send", send)
graph.add_edge(START, "draft")
graph.add_edge("draft", "approve")
graph.add_edge("send", END)
app = graph.compile(checkpointer=InMemorySaver())

# %% [markdown]
# ## Part 1: run until the gate
#
# `invoke` comes back early. `__interrupt__` holds what the human needs to see.
# At this point the process could exit - the thread id is all that is needed to
# pick this up again.

# %%
config = {"configurable": {"thread_id": "email-42"}}
paused = app.invoke(
    {"messages": [{"role": "user", "content": "Tell the team the release moves to Friday."}],
     "draft": "", "sent": False},
    config,
)
request = paused["__interrupt__"][0].value
print(f"PAUSED at {app.get_state(config).next}: {request['question']}")
print(f"  draft: {request['draft'][:90]}")

# %% [markdown]
# ## Part 2: the human answers - maybe much later
#
# `Command(resume=...)` delivers the answer to the waiting `interrupt`. Try
# `"no"` (nothing is sent) or any other text (the edited draft is sent instead).

# %%
human_answer = "Team - the release moves to Friday. Details in the channel."
done = app.invoke(Command(resume=human_answer), config)
print(f"resumed -> sent={done['sent']}, final draft: {done['draft']!r}")

# %% [markdown]
# ## In production
#
# * Swap `InMemorySaver` for a durable checkpointer (Postgres, SQLite, Redis, or
#   the Foundry hosted-agent state store) - an approval can sit for a day.
# * `create_agent(..., middleware=[HumanInTheLoopMiddleware(...)])` gives the same
#   gate for tool calls without writing the graph yourself.
# * MAF's equivalent is `approval_mode="always_require"` on a tool, surfacing as a
#   `request_info` event - the same shape you handled in sample 04.
