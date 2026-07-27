"""
backend/summariser.py
=====================
Compress long conversation histories via LLM summarisation.

When a session accumulates more than THRESHOLD messages the oldest
messages (all but the most recent KEEP_RECENT) are summarised into a
single system message.  The summary is cached in kv_store and is only
regenerated when the older portion grows (i.e. new older messages
accumulate beyond the current cache).
"""
from __future__ import annotations

_THRESHOLD   = 20   # start compressing when total messages exceed this
_KEEP_RECENT = 8    # always keep this many recent messages verbatim
_NS          = "chat_summary"

_PROMPT_BM = (
    "Anda ialah pembantu ringkasan perbualan. "
    "Tulis ringkasan PADAT (maksimum 200 patah perkataan) tentang perbualan di bawah. "
    "Sertakan: topik utama, data/fakta penting, keputusan yang dibuat, dan konteks kritikal. "
    "Balas HANYA dengan teks ringkasan — tiada pengenalan atau penutup."
)
_PROMPT_EN = (
    "You are a conversation summariser. Write a COMPACT summary (max 200 words) of the "
    "conversation below.  Include: main topics, key facts/data, decisions made, and critical "
    "context.  Reply ONLY with the summary text — no introduction or closing."
)


def compress_history(
    session_id: str,
    messages: list[dict],
    lang: str = "bm",
) -> list[dict]:
    """Return a history list compressed for injection into agent prompts.

    If len(messages) <= THRESHOLD the list is returned unchanged.
    Otherwise the older portion is summarised and the result is:
        [{"role": "system", "content": "[SUMMARY] ..."}] + last_KEEP_RECENT messages
    """
    if len(messages) <= _THRESHOLD:
        return messages

    recent = messages[-_KEEP_RECENT:]
    older  = messages[:-_KEEP_RECENT]

    from backend.session_store import get_store
    store = get_store()

    cached_text  = store.get(session_id, _NS, "text")
    cached_count = int(store.get(session_id, _NS, "count") or 0)

    if cached_text and cached_count == len(older):
        summary = cached_text
    else:
        summary = _summarise(older, lang)
        if not summary:
            return messages          # fallback: return uncompressed
        try:
            store.set(session_id, _NS, "text",  summary)
            store.set(session_id, _NS, "count", len(older))
        except Exception:
            pass

    EN = lang == "en"
    header = "SUMMARY OF EARLIER CONVERSATION" if EN else "RINGKASAN PERBUALAN TERDAHULU"
    sys_msg = {"role": "system", "content": f"[{header}]\n{summary}"}
    return [sys_msg] + list(recent)


def invalidate(session_id: str) -> None:
    """Drop the cached summary for *session_id* (call on session clear)."""
    try:
        from backend.session_store import get_store
        get_store().delete_ns(session_id, _NS)
    except Exception:
        pass


# ── Internal ──────────────────────────────────────────────────────────────────

def _summarise(messages: list[dict], lang: str) -> str | None:
    from backend.deepseek_client import chat_completion
    EN = lang == "en"
    turns = "\n".join(
        f"{m['role'].upper()}: {m['content'][:400]}"
        for m in messages
        if m.get("role") in ("user", "assistant")
    )
    if not turns.strip():
        return None
    try:
        return chat_completion(
            messages=[
                {"role": "system", "content": _PROMPT_EN if EN else _PROMPT_BM},
                {"role": "user",   "content": turns},
            ],
            temperature=0.0,
            max_tokens=350,
        )
    except Exception:
        return None
