"""
utils/formatting.py

Converts the structured feedback dict (see prompts/presentation_feedback.py
for the schema) into a Markdown string for display in Gradio's gr.Markdown
component. Kept separate from services/feedback.py so "how we call the AI"
and "how we display the result" don't get tangled together.
"""


def format_feedback_markdown(feedback: dict, filler_word_counts: dict) -> str:
    well_done = "\n".join(f"- {point}" for point in feedback["what_you_did_well"])
    improvements = "\n".join(f"- {point}" for point in feedback["actionable_improvements"])
    fillers = ", ".join(f"**{word}**: {count}" for word, count in filler_word_counts.items())
    example = feedback["example_improvement"]

    return f"""
## Overall Score: {feedback['overall_score']} / 100

### ✅ What You Did Well
{well_done}

### 🧭 Structure & Organization
{feedback['structure_and_organization']}

### 🎯 Clarity & Conciseness
{feedback['clarity_and_conciseness']}

### 🗣️ Communication Style
{feedback['communication_style']}

### 🔁 Filler Words & Verbal Habits
{fillers}

{feedback['filler_word_commentary']}

### 🔊 Speech Clarity
{feedback['speech_clarity']}

### 🚀 Actionable Improvements
{improvements}

### ✏️ Example Improvement
**Original:** "{example['original']}"

**Improved:** "{example['improved']}"

*Why:* {example['why']}
"""
