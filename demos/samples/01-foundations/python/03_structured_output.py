# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass"]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 03 - Structured output
#
# "Answer in JSON" is a wish. A JSON *schema* is a contract: the provider
# constrains decoding so only tokens that keep the output valid can be sampled.
# This is what turns a chat model into a component you can call from code.
#
# ```bash
# uv run 03_structured_output.py --profile mock
# ```

# %%
from pydantic import BaseModel, Field

from genaiclass import banner, get_profile, make_client

profile = get_profile()
client = make_client(profile)
print(banner(profile))


# %% [markdown]
# ## Describe the shape you want as a type
#
# Pydantic model -> JSON schema -> constrained decoding. You never write the
# schema by hand, and you get a typed object back instead of a string to parse.

# %%
class Step(BaseModel):
    explanation: str = Field(description="What happens in this step and why")
    output: str = Field(description="The equation after this step")


class MathSolution(BaseModel):
    steps: list[Step]
    final_answer: str


# %% [markdown]
# ## `parse` instead of `create`
#
# Same endpoint, but the SDK sends the schema and hands back an instance of your
# class. A refusal or a truncated answer surfaces as an exception rather than as
# malformed JSON three layers down.

# %%
completion = client.chat.completions.parse(
    model=profile.model,
    messages=[
        {"role": "system", "content": "You are a maths tutor. Show your working."},
        {"role": "user", "content": "How can I solve 8x + 7 = -23?"},
    ],
    response_format=MathSolution,
)

solution = completion.choices[0].message.parsed
assert solution is not None

for index, step in enumerate(solution.steps, start=1):
    print(f"{index}. {step.explanation}\n   -> {step.output}")
print(f"\nanswer: {solution.final_answer}")

# %% [markdown]
# ## Why this matters more than it looks
#
# Structured output is the same machinery as tool calling (next sample): the
# model emits arguments that satisfy a schema. Once you trust the shape, you can
# route on it - classify, extract, grade, dispatch - without a parser full of
# regexes.
#
# Caveats worth saying out loud:
#
# * `strict` schemas forbid a few JSON Schema features (no `minimum`,
#   `anyOf` restrictions, every property required). Optional fields become
#   `Optional[T]` with an explicit `None`.
# * Constrained decoding guarantees the *shape*, never the *truth*. A perfectly
#   valid JSON object can still be wrong.
# * Not every endpoint supports it. Local runners often accept
#   `response_format={"type": "json_object"}` but not a full schema.
