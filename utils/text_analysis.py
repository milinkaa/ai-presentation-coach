"""
Lightweight, deterministic text analysis run on the transcript BEFORE it
goes to the LLM.

Why count filler words with regex instead of just asking the LLM to count
them? LLMs are unreliable counters over long text. Regex gives us exact,
reproducible numbers we can trust and display, and we hand those numbers
to the LLM as context so it can comment on them intelligently instead of
guessing at them itself.
"""

import re

# Each pattern uses \b (word boundary) so "like" doesn't match inside
# "likely", and is case-insensitive because we lowercase the transcript first.
FILLER_PATTERNS = {
    "um": r"\bum+\b",
    "uh": r"\buh+\b",
    "like": r"\blike\b",
    "you know": r"\byou know\b",
}


def count_filler_words(transcript: str) -> dict:
    """
    Returns a dict like {"um": 3, "uh": 1, "like": 5, "you know": 2}.

    Known limitation (worth mentioning in an interview): "like" is also a
    normal verb ("I like this idea"), so this will overcount slightly.
    That's fine for an MVP signal, but a production version would need a
    smarter filler-word detector.
    """
    text = transcript.lower()
    return {label: len(re.findall(pattern, text)) for label, pattern in FILLER_PATTERNS.items()}


def word_count(transcript: str) -> int:
    return len(transcript.split())
