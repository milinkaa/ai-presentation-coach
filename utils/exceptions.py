"""
Custom exceptions for AI Presentation Coach.

Why bother with custom exception classes instead of just raising
generic Exception / ValueError everywhere? Two reasons:

1. app.py can catch *specific* problems and show the user a tailored,
   friendly message (e.g. "your recording was too short" vs.
   "the AI service is down") instead of one scary generic error.
2. It documents, right here in one file, every "expected" way this
   pipeline can fail — useful to point to in an interview.
"""


class PresentationCoachError(Exception):
    """Base class for every error we intentionally anticipate and handle."""


class NoRecordingError(PresentationCoachError):
    """Raised when the user clicked submit without recording anything."""


class UnsupportedFileError(PresentationCoachError):
    """Raised when the recorded file has an extension we can't process."""


class AudioTooShortError(PresentationCoachError):
    """Raised when the recording is too short to meaningfully transcribe."""


class TranscriptionError(PresentationCoachError):
    """Raised when the speech-to-text API call fails or the file is unreadable."""


class EmptyTranscriptError(PresentationCoachError):
    """Raised when transcription succeeds but returns no detected speech."""


class FeedbackGenerationError(PresentationCoachError):
    """Raised when the LLM feedback call fails or returns unusable output."""
