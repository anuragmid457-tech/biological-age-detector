"""Small helpers shared by the detector, chatbot and learning modules."""

from __future__ import annotations

import re

SECTIONS = ("personal", "heart", "medical", "nutrition", "psychological", "security")

_NUM = r"(-?\d+(?:\.\d+)?)"
_FLAGS = re.IGNORECASE | re.MULTILINE
_HEADER = re.compile(r"^\s*(BIOLOGICAL_AGE|LIFE_EXPECTANCY|HEALTH_SCORE|SCORES)\s*:", re.IGNORECASE)


def as_text(message) -> str:
    """
    Flatten a LangChain message's .content to a plain string.

    Newer Gemini models return content as a list of blocks rather than a string.
    Anything that is not a text block (reasoning, tool calls) is dropped, so the
    BIOLOGICAL_AGE line reliably lands first.
    """
    content = getattr(message, "content", message)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)

    return str(content)


def _number(label: str, text: str):
    match = re.search(rf"^\s*{label}\s*:\s*{_NUM}", text, _FLAGS)
    return float(match.group(1)) if match else None


def parse_reading(raw: str) -> dict:
    """
    Pull the header lines out of a model reply into a dict.

    Missing or malformed fields come back as None instead of raising, so the
    assessment is still stored and an expert can still correct it.
    """
    text = raw or ""
    reading = {
        "biological_age": _number("BIOLOGICAL_AGE", text),
        "life_expectancy": _number("LIFE_EXPECTANCY", text),
        "health_score": _number("HEALTH_SCORE", text),
        "scores": {},
    }

    match = re.search(r"^\s*SCORES\s*:\s*(.+)$", text, _FLAGS)
    if match:
        for name, value in re.findall(rf"(\w+)\s*=\s*{_NUM}", match.group(1)):
            if name.lower() in SECTIONS:
                reading["scores"][name.lower()] = float(value)

    # The explanation is everything after the last header line near the top.
    lines = text.splitlines()
    last = -1
    for i, line in enumerate(lines[:10]):
        if _HEADER.match(line):
            last = i
    reading["explanation"] = "\n".join(lines[last + 1:]).strip()

    return reading


def format_reading(reading: dict) -> str:
    """One-line summary of whichever fields are present, for the expert examples."""
    parts = []
    for key, label in (("biological_age", "biological age"),
                       ("life_expectancy", "life expectancy"),
                       ("health_score", "health score")):
        if reading.get(key) is not None:
            parts.append(f"{label} {reading[key]:g}")

    scores = reading.get("scores") or {}
    if scores:
        parts.append("section scores " + ", ".join(f"{k} {v:+g}" for k, v in scores.items()))

    return "; ".join(parts) or "no values"