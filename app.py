"""
AI Presentation Coach — app.py

STAGE 2 + 3: real transcription (Whisper) and real AI feedback (LLM),
wired into the same recording UI from Stage 1.

Flow:
  1. Selection screen (unchanged from Stage 1)
  2. Recording screen (unchanged from Stage 1)
  3. Loading screen (NEW) — shows progressive status messages
  4. Results screen (NEW) — renders the structured feedback report

Run with:  python app.py
"""

import os

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from services.feedback import generate_feedback
from services.transcription import transcribe
from utils.exceptions import PresentationCoachError
from utils.formatting import format_feedback_markdown
from utils.text_analysis import count_filler_words

#load_dotenv()  # reads OPENAI_API_KEY (and anything else) from .env         -deleted manually

PRESENTATION_TYPES = [
    "Academic Presentation",
    "Business / Pitch",
    "Interview Response",
    "General Speech",
]


def go_to_recording(presentation_type, mode):
    if not presentation_type or not mode:
        gr.Warning("Please select a presentation type and a practice mode.")
        return (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=(mode == "Camera + Audio")),
            gr.update(visible=(mode == "Audio Only")),
        )

    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=(mode == "Camera + Audio")),
        gr.update(visible=(mode == "Audio Only")),
    )


def back_to_start():
    return (
        gr.update(visible=True),   # selection_screen
        gr.update(visible=False),  # recording_screen
        gr.update(visible=False),  # loading_screen
        gr.update(visible=False),  # results_screen
    )


def _fail(message: str):
    """
    Shared helper for every error exit: pop a toast warning, hide the
    loading screen, and send the user back to the recording screen so they
    can just retry without losing their type/mode selection.
    """
    gr.Warning(message)
    return (
        gr.update(visible=True),   # recording_screen
        gr.update(visible=False),  # loading_screen
        gr.update(visible=False),  # results_screen
        gr.update(),               # loading_text (unused here)
        gr.update(),               # results_markdown (unused here)
    )


def process_recording(video_path, audio_path, presentation_type, mode):
    """
    This is a GENERATOR function (uses `yield` instead of `return`).
    Gradio supports generators for exactly this purpose: each `yield`
    pushes an incremental UI update to the browser, which is how we show
    "Listening... -> Analyzing... -> Preparing..." instead of one long
    silent wait.

    Every `yield` / final `return` sends a 5-tuple matching, in order, the
    outputs=[...] list wired up below:
      (recording_screen, loading_screen, results_screen, loading_text, results_markdown)
    """
    recording_path = video_path if mode == "Camera + Audio" else audio_path

    # ---- Move to loading screen ----
    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        "🎧 Listening to your presentation...",
        gr.update(),
    )

    # ---- Step 1: Transcription ----
    try:
        transcript, duration_seconds = transcribe(recording_path)
    except PresentationCoachError as exc:
        yield _fail(str(exc))
        return
    except Exception:
        yield _fail("Something unexpected happened while processing your recording. Please try again.")
        return

    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        "🔎 Analyzing structure and delivery...",
        gr.update(),
    )

    # ---- Step 2: Deterministic filler-word counting (no API call) ----
    filler_word_counts = count_filler_words(transcript)

    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        "📝 Preparing your feedback...",
        gr.update(),
    )

    # ---- Step 3: LLM feedback generation ----
    try:
        feedback = generate_feedback(transcript, filler_word_counts, duration_seconds, presentation_type)
    except PresentationCoachError as exc:
        yield _fail(str(exc))
        return
    except Exception:
        yield _fail("Something unexpected happened while generating feedback. Please try again.")
        return

    # Note: `transcript` is a local variable that is never displayed,
    # written to disk, or returned to the UI. It only ever lives in memory
    # for the duration of this function call, satisfying the
    # "hidden transcript" requirement.
    results_markdown = format_feedback_markdown(feedback, filler_word_counts)

    yield (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(),
        results_markdown,
    )


with gr.Blocks(title="AI Presentation Coach") as demo:
    gr.Markdown("# AI Presentation Coach")
    gr.Markdown("*Practice your presentation. Get actionable feedback.*")

    if not os.getenv("OPENAI_API_KEY"):
        gr.Markdown(
            "⚠️ **OPENAI_API_KEY is not set.** Copy `.env.example` to `.env` and add your key, "
            "then restart the app."
        )

    # ----- Screen 1: selection -----
    with gr.Column(visible=True) as selection_screen:
        presentation_type = gr.Radio(
            choices=PRESENTATION_TYPES,
            label="What type of presentation are you practicing?",
        )
        mode = gr.Radio(
            choices=["Camera + Audio", "Audio Only"],
            label="How would you like to practice?",
        )
        continue_btn = gr.Button("Continue", variant="primary")

    # ----- Screen 2: recording (unchanged from Stage 1) -----
    with gr.Column(visible=False) as recording_screen:
        gr.Markdown("### Record your presentation")
        video_recorder = gr.Video(
            sources=["webcam"], visible=False, label="Camera + Audio"
        )
        audio_recorder = gr.Audio(
            sources=["microphone"], visible=False, label="Audio Only", type="filepath"
        )
        gr.Markdown(
            "Record, review the playback, and re-record as many times as you like "
            "before submitting."
        )
        submit_btn = gr.Button("Analyze Presentation", variant="primary")

    # ----- Screen 3: loading (NEW) -----
    with gr.Column(visible=False) as loading_screen:
        loading_text = gr.Markdown("🎧 Listening to your presentation...")

    # ----- Screen 4: results (NEW) -----
    with gr.Column(visible=False) as results_screen:
        results_markdown = gr.Markdown()
        start_over_btn = gr.Button("Practice Again")

    continue_btn.click(
        fn=go_to_recording,
        inputs=[presentation_type, mode],
        outputs=[selection_screen, recording_screen, video_recorder, audio_recorder],
    )

    submit_btn.click(
        fn=process_recording,
        inputs=[video_recorder, audio_recorder, presentation_type, mode],
        outputs=[recording_screen, loading_screen, results_screen, loading_text, results_markdown],
    )

    start_over_btn.click(
        fn=back_to_start,
        outputs=[selection_screen, recording_screen, loading_screen, results_screen],
    )

if __name__ == "__main__":
    demo.launch()
