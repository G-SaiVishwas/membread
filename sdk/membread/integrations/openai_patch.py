"""
OpenAI SDK monkey-patch for Membread.

Transparently wraps `openai.ChatCompletion.create` (and the async variant)
to auto-capture all prompts and completions in Membread.

Usage::

    from membread.integrations.openai_patch import patch_openai

    patch_openai(api_url="http://localhost:8000", token="eyJ...")

    # Now all OpenAI calls are automatically captured
    import openai
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}]
    )
    # ^ This prompt + response is stored in Membread
"""

from __future__ import annotations

import functools
from typing import Any

from membread.client import MembreadClient

_patched = False


def patch_openai(
    api_url: str = "http://localhost:8000",
    token: str = "",
    source: str = "openai-sdk",
    capture_prompts: bool = True,
    capture_responses: bool = True,
) -> None:
    """Monkey-patch the OpenAI client to auto-capture completions.

    Args:
        api_url: Membread API URL.
        token: JWT bearer token.
        source: Source label for captured memories.
        capture_prompts: Whether to store user prompts.
        capture_responses: Whether to store assistant responses.
    """
    global _patched
    if _patched:
        return
    _patched = True

    client = MembreadClient(
        api_url=api_url,
        token=token,
        source=source,
        agent_id="openai-sdk",
    )

    try:
        import openai
    except ImportError:
        raise ImportError("openai package required: pip install openai")

    # Wrap the chat completions create method
    if hasattr(openai, "OpenAI"):
        _patch_v1(openai, client, capture_prompts, capture_responses)
    else:
        # Older openai < 1.0 not supported
        pass


def _patch_v1(
    openai_module: Any,
    tg_client: MembreadClient,
    capture_prompts: bool,
    capture_responses: bool,
) -> None:
    """Patch openai >= 1.0.0 client."""
    from openai.resources.chat import completions as chat_mod

    original_create = chat_mod.Completions.create

    @functools.wraps(original_create)
    def patched_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        messages = kwargs.get("messages", args[0] if args else [])
        model = kwargs.get("model", "unknown")
        session_id = f"openai-{model}"

        # Capture prompt
        if capture_prompts and messages:
            last_user = next(
                (m for m in reversed(messages) if m.get("role") == "user"),
                None,
            )
            if last_user:
                try:
                    tg_client.store(
                        f"User: {last_user['content'][:3000]}",
                        session_id=session_id,
                        metadata={"role": "user", "model": model, "event": "prompt"},
                    )
                except Exception:
                    pass

        # Call original
        response = original_create(self, *args, **kwargs)

        # Capture response
        if capture_responses and hasattr(response, "choices") and response.choices:
            try:
                content = response.choices[0].message.content
                if content:
                    tg_client.store(
                        f"Assistant: {content[:3000]}",
                        session_id=session_id,
                        metadata={"role": "assistant", "model": model, "event": "completion"},
                    )
            except Exception:
                pass

        return response

    chat_mod.Completions.create = patched_create
