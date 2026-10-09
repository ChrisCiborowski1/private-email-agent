from __future__ import annotations

import re

QUESTION_WORDS = {
    "a", "an", "and", "are", "been", "did", "do", "does", "for", "from", "has", "have",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "order", "the", "to", "was",
    "what", "when", "where", "which", "who", "why", "with", "your",
}


def broad_search_query(question: str) -> str:
    """Build a conservative discovery query without model-generated Gmail syntax."""
    spans = re.findall(r"\b(?:[A-Z][\w&'.-]*)(?:\s+[A-Z][\w&'.-]*)*", question)
    candidates = []
    for span in spans:
        words = [word for word in span.split() if word.lower() not in QUESTION_WORDS]
        if words:
            candidates.append(" ".join(words))
    if candidates:
        best = max(candidates, key=lambda value: (len(value.split()), len(value)))
        return f'"{best}"' if " " in best else best
    words = re.findall(r"[\w&'.-]+", question)
    useful = [word for word in words if word.lower() not in QUESTION_WORDS and len(word) > 2]
    return " ".join(useful[:6]) or question

