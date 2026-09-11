"""Small helpers shared by the detector and chatbot modules."""


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