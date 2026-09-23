"""Resolve a provider profile from providers.json + environment."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` (or this file) until providers.json shows up."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "providers.json").is_file():
            return candidate
    raise FileNotFoundError("providers.json not found - run from inside the samples repo")


def _expand(value: str) -> str:
    """Substitute ${VAR} and ${VAR:-default} from the environment."""

    def sub(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        return os.environ.get(name) or (default if default is not None else "")

    return _PLACEHOLDER.sub(sub, value)


@dataclass(frozen=True)
class Profile:
    name: str
    label: str
    base_url: str
    api_key: str
    key_header: str
    model: str
    embed_model: str

    @property
    def headers(self) -> dict[str, str]:
        """Extra headers for this endpoint: Azure/APIM want `api-key`, everyone else Bearer."""
        return {"api-key": self.api_key} if self.key_header == "api-key" else {}

    def missing(self) -> list[str]:
        gaps = []
        if not self.base_url or "<" in self.base_url:
            gaps.append("base_url")
        if not self.api_key:
            gaps.append("api_key")
        return gaps


def _load_env_files(root: Path) -> None:
    """Load every .env from the repo folder upward, then from the current folder upward.

    Nearest file wins (override=False; real environment variables win over all of them), so
    demos/.env, one .env at the root of a cloned repo, or both work - whatever folder you start in.
    """
    seen: set[Path] = set()
    for folder in [root, *root.parents, Path.cwd(), *Path.cwd().parents]:
        env = folder / ".env"
        if env.is_file() and env not in seen:
            seen.add(env)
            load_dotenv(env, override=False)


def _load_config(root: Path | None = None) -> tuple[Path, dict]:
    root = root or repo_root()
    _load_env_files(root)
    return root, json.loads((root / "providers.json").read_text(encoding="utf-8"))


def list_profiles(root: Path | None = None) -> dict[str, str]:
    _, cfg = _load_config(root)
    return {name: entry.get("label", "") for name, entry in cfg["profiles"].items()}


def get_profile(name: str | None = None, root: Path | None = None) -> Profile:
    """Resolve a profile: explicit name > --profile > GENAI_PROFILE > default."""
    root, cfg = _load_config(root)
    name = name or _profile_from_argv() or os.environ.get("GENAI_PROFILE") or cfg["default"]
    if name not in cfg["profiles"]:
        known = ", ".join(cfg["profiles"])
        raise SystemExit(f"Unknown profile {name!r}. Known profiles: {known}")
    entry = cfg["profiles"][name]
    return Profile(
        name=name,
        label=entry.get("label", name),
        base_url=_expand(entry["base_url"]).rstrip("/"),
        api_key=_expand(entry["api_key"]),
        key_header=entry.get("key_header", "authorization").lower(),
        model=_expand(entry.get("model", "")),
        embed_model=_expand(entry.get("embed_model", "")),
    )


def _profile_from_argv() -> str | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--profile")
    known, _ = parser.parse_known_args(sys.argv[1:])
    return known.profile


def make_client(profile: Profile | None = None, **kwargs):
    """An `openai.OpenAI` pointed at the profile's endpoint.

    Azure/APIM want the key in an `api-key` header; OpenAI and the local runners
    want `Authorization: Bearer`. The OpenAI SDK sends the latter, so for the
    former we simply add the extra header - same client either way.
    """
    from openai import OpenAI

    profile = profile or get_profile()
    gaps = profile.missing()
    if gaps:
        raise SystemExit(
            f"Profile {profile.name!r} is missing {', '.join(gaps)}. "
            f"Fill it in .env (see .env.example) or pick another --profile."
        )
    return OpenAI(
        base_url=profile.base_url,
        api_key=profile.api_key,
        default_headers=profile.headers or None,
        **kwargs,
    )


def banner(profile: Profile) -> str:
    return f"[{profile.name}] {profile.model} @ {profile.base_url}"
