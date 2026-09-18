"""
services/feedback.py

Sends the (hidden) transcript + metadata to an LLM and gets back a
structured feedback report as a Python dict.
"""

import json

from openai import OpenAI

from prompts.presentation_feedback import build_system_prompt, build_user_prompt
from utils.exceptions import FeedbackGenerationError

_client = OpenAI()

# gpt-4o-mini is fast and inexpensive, which matters for an MVP you'll be
# demoing repeatedly. Swap this constant to upgrade the model quality later.
FEEDBACK_MODEL = "gpt-4o-mini"

REQUIRED_KEYS = {
    "overall_score",
    "what_you_did_well",
    "structure_and_organization",
    "clarity_and_conciseness",
    "communication_style",
    "filler_word_commentary",
    "speech_clarity",
    "actionable_improvements",
    "example_improvement",
}


def generate_feedback(
    transcript: str,
    filler_word_counts: dict,
    duration_seconds: float,
    presentation_type: str,
) -> dict:
    """
    Returns a dict matching the schema described in
    prompts/presentation_feedback.py. Raises FeedbackGenerationError on any
    failure (API error, malformed JSON, or missing expected fields).
    """
    system_prompt = build_system_prompt(presentation_type)
    user_prompt = build_user_prompt(transcript, filler_word_counts, duration_seconds, presentation_type)

    try:
        response = _client.chat.completions.create(
            model=FEEDBACK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # This forces the model to return valid JSON — removes an entire
            # class of "it wrapped the JSON in markdown fences" bugs.
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        raw_content = response.choices[0].message.content
    except Exception as exc:
        raise FeedbackGenerationError(
            "We couldn't generate feedback right now. Please try again in a moment."
        ) from exc

    try:
        feedback_data = json.loads(raw_content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise FeedbackGenerationError(
            "The AI response was in an unexpected format. Please try again."
        ) from exc

    missing_keys = REQUIRED_KEYS - feedback_data.keys()
    if missing_keys:
        raise FeedbackGenerationError(
            "The AI response was incomplete. Please try again."
        )

    return feedback_data
