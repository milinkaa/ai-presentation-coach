"""
services/transcription.py

Turns a recorded file (video OR audio) into English text.

Key design decision: we do NOT manually extract the audio track from video
files ourselves. OpenAI's Whisper API accepts video containers like .mp4
and .webm directly and extracts the audio server-side. This keeps our code
much simpler — one function handles both the "Camera + Audio" and
"Audio Only" recording paths identically.

We DO use `pydub` (which relies on the `ffmpeg` command-line tool) to peek
at the recording's duration locally, before spending an API call, so we can
reject obviously-too-short recordings immediately with a clear error.
"""

import os

from openai import OpenAI
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from utils.exceptions import (
    AudioTooShortError,
    EmptyTranscriptError,
    NoRecordingError,
    TranscriptionError,
    UnsupportedFileError,
)

MIN_DURATION_SECONDS = 2.0
SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".oga", ".ogg", ".flac"}

# The OpenAI client automatically reads the OPENAI_API_KEY environment
# variable — we never hardcode or pass the key directly in code.
_client = OpenAI()


def _validate_file(file_path: str) -> None:
    """Cheap checks we can do before touching any external API."""
    if not file_path or not os.path.exists(file_path):
        raise NoRecordingError("No recording was found. Please record before submitting.")

    extension = os.path.splitext(file_path)[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(f"'{extension}' isn't a supported recording format.")

    if os.path.getsize(file_path) == 0:
        raise AudioTooShortError("Your recording appears to be empty. Please try again.")


def _get_duration_seconds(file_path: str) -> float:
    """
    Uses pydub (backed by ffmpeg) to load the file just enough to read its
    length. This requires ffmpeg to be installed on the system — see README.
    """
    try:
        audio_segment = AudioSegment.from_file(file_path)
    except CouldntDecodeError as exc:
        raise TranscriptionError(
            "We couldn't read your recording. Please try recording again."
        ) from exc
    return len(audio_segment) / 1000.0  # pydub gives length in milliseconds


def transcribe(file_path: str) -> tuple[str, float]:
    """
    Main entry point. Returns (transcript_text, duration_seconds).

    Raises one of the exceptions in utils/exceptions.py on any expected
    failure — app.py is responsible for catching those and showing a
    friendly message.
    """
    _validate_file(file_path)
    duration_seconds = _get_duration_seconds(file_path)

    if duration_seconds < MIN_DURATION_SECONDS:
        raise AudioTooShortError(
            f"Your recording is only {duration_seconds:.1f} seconds long. "
            f"Please record at least {MIN_DURATION_SECONDS:.0f} seconds."
        )

    try:
        with open(file_path, "rb") as recording_file:
            transcript_text = _client.audio.transcriptions.create(
                model="whisper-1",
                file=recording_file,
                # Telling Whisper the spoken language is English keeps this a
                # pure transcription task, not a translation task — it will
                # not attempt to translate other languages into English.
                language="en",
                response_format="text",
            )
    except Exception as exc:
        print("TRANSCRIPTION ERROR:", repr(exc))
        raise TranscriptionError(
            "The transcription service failed. Please check your connection and try again."
        ) from exc

    transcript_text = (transcript_text or "").strip()
    if not transcript_text:
        raise EmptyTranscriptError(
            "We couldn't detect any speech in your recording. Please try again in a quieter environment."
        )

    return transcript_text, duration_seconds
