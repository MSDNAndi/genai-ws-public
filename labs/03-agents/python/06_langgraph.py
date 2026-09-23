"""Lab 3 · stretch — the same researcher -> writer idea as an explicit LangGraph graph, with a checkpointer (memory per
thread) and a human approval step (interrupt / resume). Compare: in MAF you *declare* a pattern, here you *draw* the graph.

python 06_langgraph.py            # asks you to approve in the terminal
python 06_langgraph.py --auto     # approves automatically (used by the test runner)
"""
import os
import sys
from pathlib import Path
from typing import TypedDict

from dotenv import find_dotenv, load_dotenv
from pathlib import Path as _Path
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

_here = _Path(globals().get("__file__", ".")).resolve()   # no __file__ in a notebook: start at the cwd
for _folder in [*_here.parents, _Path.cwd(), *_Path.cwd().parents]:
    if (_folder / ".env").is_file():   # every .env from this file upward: the nearest one wins,
        load_dotenv(_folder / ".env")  # so labs/.env or one .env at the repo root both work
LABS = next(p for p in Path(__file__).resolve().parents if (p / "_tools" / "make_starters.py").exists())
sys.path.insert(0, str(LABS / "02-rag-mcp" / "python" / "solution"))
from kestrel_search import Index  # noqa: E402  (Lab 2 retrieval, called directly instead of via MCP)

KEY = os.environ["GENAI_API_KEY"]
HEADERS = {"api-key": KEY} if os.getenv("GENAI_KEY_HEADER", "api-key") == "api-key" else None
EXTRA = {"reasoning_effort": os.environ["GENAI_REASONING_EFFORT"]} if os.getenv("GENAI_REASONING_EFFORT") else {}
llm = ChatOpenAI(model=os.environ["GENAI_MODEL"], base_url=os.environ["GENAI_BASE_URL"], api_key=KEY,
                 default_headers=HEADERS, **EXTRA)
index = Index()


class State(TypedDict, total=False):
    question: str
    notes: str
    draft: str
    feedback: str


def research(state: State) -> State:
    hits = index.search(state["question"], k=4)
    notes = llm.invoke("Summarise the facts that answer the question as bullets with chunk ids.\n"
                       f"Question: {state['question']}\n\n" + "\n\n".join(f"({h['id']}) {h['text']}" for h in hits))
    return {"notes": notes.content}


def write(state: State) -> State:
    fix = f"\nApply this feedback: {state['feedback']}" if state.get("feedback") else ""
    draft = llm.invoke(f"Write a friendly reply (max 80 words) to: {state['question']}\nFacts:\n{state['notes']}{fix}")
    return {"draft": draft.content}


def human_review(state: State) -> Command:
    decision = interrupt({"draft": state["draft"]})       # pauses the graph; state is saved by the checkpointer
    if str(decision).strip().lower() in ("", "approve", "ok", "y", "yes"):
        return Command(goto=END)
    return Command(goto="write", update={"feedback": str(decision)})


graph = StateGraph(State)
graph.add_node("research", research)
graph.add_node("write", write)
graph.add_node("human_review", human_review)
graph.add_edge(START, "research")
graph.add_edge("research", "write")
graph.add_edge("write", "human_review")
app = graph.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "customer-4711"}}  # same thread id = same saved state
out = app.invoke({"question": "Can I send a 150 Wh power bank?"}, config)
auto = "--auto" in sys.argv or not sys.stdin.isatty()
while "__interrupt__" in out:
    print("\nDRAFT:\n" + out["__interrupt__"][0].value["draft"])
    answer = "approve" if auto else input("\n'approve' or type feedback > ")
    out = app.invoke(Command(resume=answer), config)
print("\nFINAL:\n" + app.get_state(config).values["draft"])
print(f"checkpoints saved for this thread: {len(list(app.get_state_history(config)))}")
