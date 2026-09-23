"""One-liners that point an agent framework at the active provider profile.

Every framework needs the same three things - base URL, key, model - and each
spells them slightly differently. These helpers keep that noise out of the
samples. Imports are lazy, so `genaiclass` never depends on a framework: a
sample that uses LangChain only needs LangChain installed.

Both return a **Chat Completions** client on purpose. It is the one dialect that
every provider, gateway and local runner speaks, so `--profile ollama` keeps
working. (Trap worth knowing: in Microsoft Agent Framework 1.x,
`OpenAIChatClient` is the *Responses* API client; the Chat Completions one is
`OpenAIChatCompletionClient`.)
"""

from __future__ import annotations

from typing import Any

from .providers import Profile, get_profile


def _checked(profile: Profile | None) -> Profile:
    profile = profile or get_profile()
    if profile.missing():
        raise SystemExit(
            f"Profile {profile.name!r} is missing {', '.join(profile.missing())}. "
            "Fill it in .env (see .env.example) or pick another --profile."
        )
    return profile


def maf_client(profile: Profile | None = None) -> Any:
    """Microsoft Agent Framework chat client for the profile."""
    from agent_framework.openai import OpenAIChatCompletionClient

    profile = _checked(profile)
    return OpenAIChatCompletionClient(
        model=profile.model,
        base_url=profile.base_url,
        api_key=profile.api_key,
        default_headers=profile.headers or None,
    )


def langchain_model(profile: Profile | None = None, **kwargs: Any) -> Any:
    """LangChain chat model for the profile."""
    from langchain_openai import ChatOpenAI

    profile = _checked(profile)
    return ChatOpenAI(
        model=profile.model,
        base_url=profile.base_url,
        api_key=profile.api_key,
        default_headers=profile.headers or None,
        **kwargs,
    )
