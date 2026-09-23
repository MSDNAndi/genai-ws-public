"""Shared helpers for the BuildingStuffGenAI samples.

The only thing that varies between the workshop endpoint, OpenAI, OpenRouter,
Ollama and LM Studio is a base URL, a key and a model name. This package turns
`providers.json` + your `.env` into a ready-to-use OpenAI-compatible client, so
every sample can stay about the API and not about configuration.
"""

import sys

# Windows consoles default to cp1252; one non-ASCII print (a check mark, an arrow)
# kills a demo mid-run. Switch this process's console streams to UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass

from .frameworks import langchain_model, maf_client
from .inspect import dump, inspect, raw_json, to_plain
from .providers import Profile, banner, get_profile, list_profiles, make_client

__all__ = [
    "Profile",
    "banner",
    "dump",
    "get_profile",
    "inspect",
    "langchain_model",
    "list_profiles",
    "maf_client",
    "make_client",
    "raw_json",
    "to_plain",
]
