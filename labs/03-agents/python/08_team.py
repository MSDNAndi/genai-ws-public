# STARTER - complete the TODO block(s). The finished version is in solution/08_team.py
"""Lab 3 · stretch — a team of four agents on four vendors' models, one endpoint.

    lead (plans) --> policy analyst --+--> fact-checker --> lead (merges the incident review)
                     comms writer ----+   (in parallel)

The job: a fresh incident from this morning's ops log. The policy analyst looks up the rules in the Kestrel docs (the
Lab 2 MCP server), the comms writer drafts the customer message *at the same time* (no tool - on purpose), the
fact-checker holds the draft against the docs, and the lead merges everything into one incident review.

Every agent runs on a different vendor's model (OpenAI, DeepSeek, Meta, xAI) - same client class, same endpoint,
only the model name changes. Swap any of them with an environment variable, e.g. TEAM_COMMS_MODEL=gpt-4o-mini.
At the end: who did what, on which model, how long it took and how many tokens it used.

Team = specialists with different jobs (and models); policy and comms run in PARALLEL, the rest one after another.
What to notice: agreement is not correctness - check the 09:05 arrival against the docs yourself.
"""
import asyncio
import os
import time

from agent_framework import Agent, AgentContext, agent_middleware
from agent_framework.orchestrations import ConcurrentBuilder

from lab3_common import chat_client, kestrel_docs_tool

MODELS = {   # defaults - every one can be overridden from the environment
    "lead": os.getenv("TEAM_LEAD_MODEL", "gpt-5-nano"),
    "policy": os.getenv("TEAM_POLICY_MODEL", "DeepSeek-V4.1-Flash-1017"),
    "comms": os.getenv("TEAM_COMMS_MODEL", "Llama-4-Maverick-17B-128E-Instruct-FP8"),
    "checker": os.getenv("TEAM_CHECKER_MODEL", "grok-4-1-fast-non-reasoning"),
}

INCIDENT = """Ops log, 16 Nov 2026, 07:10, Heidelberg. A K-7 Heron took off in light rain with a 5.1 kg parcel
(Standard delivery, window 06:00-08:00). Shortly after take-off it reported low lift, aborted and made an emergency
landing in a field. Nobody was hurt; the parcel was damaged. A replacement parcel arrived at 09:05.
The customer (Ms. Weber) has complained on social media."""


def options_for(model: str) -> dict:
    """reasoning_effort only means something for reasoning models, so only they get it (the gateway drops it anyway)."""
    if model.startswith(("gpt-5", "gpt-oss", "o3", "o4")):
        return {"reasoning_effort": os.getenv("GENAI_REASONING_EFFORT") or "low"}
    return {}


LEDGER = []   # one row per agent run: (agent, model, seconds, input tokens, output tokens)


@agent_middleware
async def meter(context: AgentContext, call_next):
    """Agent middleware (runs around every agent run): time it and read its token usage - inside workflows too."""
    started = time.perf_counter()

    def record(response):
        usage = response.usage_details or {}
        LEDGER.append((context.agent.name, MODELS[context.agent.name.split("_")[0]], time.perf_counter() - started,
                       usage.get("input_token_count") or 0, usage.get("output_token_count") or 0))
        return response

    if context.stream:                      # streamed runs: read the usage once the stream is finished
        context.stream_result_hooks.append(record)
        await call_next()
    else:
        await call_next()
        record(context.result)


def member(name: str, instructions: str, tools=None) -> Agent:
    """One team member: its own model (lead_plan/lead_merge both use MODELS['lead']) + the meter middleware."""
    model = MODELS[name.split("_")[0]]
    return Agent(client=chat_client(model), name=name, instructions=instructions, tools=tools or [],
                 default_options=options_for(model), middleware=[meter])


async def main() -> None:
    print("Team:", ", ".join(f"{role}={model}" for role, model in MODELS.items()), "\n")
    t0 = time.perf_counter()
    async with kestrel_docs_tool() as docs:
        setup = time.perf_counter() - t0   # starting the MCP server (it loads the Lab 2 index)
        lead_plan = member("lead_plan", "You lead an incident review at Kestrel Drone Logistics. Split the job for "
                           "your team: write ONE short task line each for the POLICY ANALYST (which rules, incident "
                           "code, escalation and customer entitlements to look up) and the COMMS WRITER (the message "
                           "to the customer). Max 60 words. No answers yourself.")
        policy = member("policy", "You are the policy analyst. Use search_docs (2-3 searches). Return at most 6 "
                        "bullets: which rule was broken, the incident code, who must be told within what time, what "
                        "the customer is entitled to. Each bullet ends with its chunk id. No prose.", tools=[docs])
        comms = member("comms", "You are the comms writer. Write the message to the customer about the incident: "
                       "apologetic, honest, plain language, at most 90 words. You have no documents - do not invent "
                       "numbers or compensation you were not given. Reply with the message only.")
        # TODO 1: the fact-checker - holds the comms draft against the docs (search_docs) and lists what is wrong or missing
        raise NotImplementedError("TODO 1: the fact-checker - holds the comms draft against the docs (search_docs) and lists what is wrong or missing")
        lead_merge = member("lead_merge", "You lead the incident review. Merge your team's work into the final "
                            "review in markdown: 1) what happened (2 lines), 2) rules broken and incident code, "
                            "3) escalation and deadlines, 4) the customer message, rewritten in full (max 90 words) "
                            "with the fact-checker's corrections. Max 250 words. Use only facts from the team.")

        # 1 · the lead splits the job
        plan = (await lead_plan.run(f"Incident:\n{INCIDENT}")).text.strip()
        print(f"[lead] plan:\n{plan}\n")

        # 2 · the two specialists work at the same time
        # ConcurrentBuilder = send the same input to several agents at once; the aggregator merges their replies.
        # TODO 2: run policy and comms CONCURRENTLY on the same input (ConcurrentBuilder) and collect {agent name: reply text}
        raise NotImplementedError("TODO 2: run policy and comms CONCURRENTLY on the same input (ConcurrentBuilder) and collect {agent name: reply text}")
        print(f"[policy] notes:\n{work['policy']}\n\n[comms] draft:\n{work['comms']}\n")

        # 3 · the fact-checker reviews the draft, 4 · the lead merges everything (plain agent.run calls, in order)
        check = (await checker.run(f"Policy notes:\n{work['policy']}\n\nCustomer message draft:\n{work['comms']}"))
        print(f"[checker] findings:\n{check.text.strip()}\n")
        review = await lead_merge.run(f"Incident:\n{INCIDENT}\n\nPolicy notes:\n{work['policy']}\n\nCustomer "
                                      f"message draft:\n{work['comms']}\n\nFact-checker:\n{check.text}")
        print("=" * 80 + f"\nINCIDENT REVIEW\n{review.text.strip()}\n" + "=" * 80)

    print(f"\n{'agent':<11} {'model':<40} {'sec':>6} {'tok in':>7} {'tok out':>8}")
    for name, model, sec, tin, tout in LEDGER:
        print(f"{name:<11} {model:<40} {sec:6.1f} {tin:7} {tout:8}")
    print(f"{'(setup)':<11} {'MCP server start':<40} {setup:6.1f}")
    print(f"{'total':<11} {'(wall clock - policy+comms ran in parallel)':<40} {time.perf_counter() - t0:6.1f} "
          f"{sum(r[3] for r in LEDGER):7} {sum(r[4] for r in LEDGER):8}")


asyncio.run(main())
