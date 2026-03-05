"""
services/podcast_service.py — Text-to-Speech Podcast Generator

Uses Google Cloud TTS (Journey voices) to synthesize dialogue scripts.
Audio segments are properly merged using pydub with silence gaps between speakers.

Graceful fallback: If TTS credentials are unavailable, the service
reports its status and skips audio rendering without crashing.
"""

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Attempt to import TTS — graceful fallback if missing/unconfigured
_TTS_AVAILABLE = False
try:
    from google.cloud import texttospeech
    _TTS_AVAILABLE = True
except ImportError:
    logger.warning("[PodcastService] google-cloud-texttospeech not installed. TTS disabled.")

# Attempt to import pydub — graceful fallback
_PYDUB_AVAILABLE = False
try:
    from pydub import AudioSegment
    _PYDUB_AVAILABLE = True
except ImportError:
    logger.warning("[PodcastService] pydub not installed. Audio merging will use raw concat.")


class PodcastGenerator:
    """
    Synthesizes multi-speaker dialogue scripts into MP3 audio.

    Usage:
        gen = PodcastGenerator(storage_provider=storage)
        if gen.is_available:
            audio_bytes = gen.generate_audio(script_json)
    """

    # Configurable silence gap between speaker turns (milliseconds)
    SPEAKER_GAP_MS = 400
    # Short pause within same speaker (for dramatic effect)
    SAME_SPEAKER_GAP_MS = 150

    def __init__(self, storage_provider=None):
        """Initialize the TTS client. Logs a warning if credentials are missing."""
        self.storage = storage_provider
        self.client = None
        self.is_available = False

        if not _TTS_AVAILABLE:
            logger.info("[PodcastService] TTS library not available. Audio rendering disabled.")
            return

        try:
            self.client = texttospeech.TextToSpeechClient()
            self.is_available = True
            logger.info("[PodcastService] TTS client initialized successfully.")
        except Exception as e:
            logger.warning(f"[PodcastService] TTS client init failed (credentials?): {e}")
            self.is_available = False

    def generate_audio(self, script_json: list) -> bytes:
        """
        Synthesizes audio for the given dialogue script.

        Args:
            script_json: List of dicts with 'speaker' and 'text' keys.
                         e.g. [{"speaker": "A", "text": "Hello!"}, ...]

        Returns:
            MP3 bytes of the full podcast episode.

        Raises:
            RuntimeError if TTS is not available.
        """
        if not self.is_available or not self.client:
            raise RuntimeError(
                "TTS is not available. Check that google-cloud-texttospeech is installed "
                "and GOOGLE_APPLICATION_CREDENTIALS is set."
            )

        # Voice configuration — Journey voices are high-quality conversational neural voices
        voices = {
            "A": texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Journey-D",  # Male-sounding, conversational
            ),
            "B": texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Journey-F",  # Female-sounding, conversational
            ),
        }

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.1,  # Slightly faster for podcast energy
            pitch=0.0,
        )

        # Synthesize each line
        audio_segments: list[tuple[str, bytes]] = []  # (speaker, mp3_bytes)
        prev_speaker = None

        for i, line in enumerate(script_json):
            speaker = line.get("speaker", "A")
            text = line.get("text", "").strip()
            if not text:
                continue

            voice = voices.get(speaker, voices["A"])
            synthesis_input = texttospeech.SynthesisInput(text=text)

            try:
                response = self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config,
                )
                audio_segments.append((speaker, response.audio_content))
                logger.debug(f"[PodcastService] Synthesized line {i+1}/{len(script_json)} ({speaker})")
            except Exception as e:
                logger.error(f"[PodcastService] TTS error on line {i+1}: {e}")
                continue

            prev_speaker = speaker

        if not audio_segments:
            raise RuntimeError("No audio segments were successfully synthesized.")

        # Merge segments with pydub (proper gaps) or raw concat (fallback)
        if _PYDUB_AVAILABLE:
            return self._merge_with_pydub(audio_segments)
        else:
            return self._merge_raw(audio_segments)

    def _merge_with_pydub(self, segments: list[tuple[str, bytes]]) -> bytes:
        """Merge audio segments using pydub with silence gaps between speakers."""
        combined = AudioSegment.empty()
        prev_speaker = None

        for speaker, mp3_bytes in segments:
            segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))

            if prev_speaker is not None:
                # Add silence gap — longer between different speakers
                gap_ms = (
                    self.SPEAKER_GAP_MS if speaker != prev_speaker
                    else self.SAME_SPEAKER_GAP_MS
                )
                silence = AudioSegment.silent(duration=gap_ms)
                combined += silence

            combined += segment
            prev_speaker = speaker

        # Export as MP3
        output = io.BytesIO()
        combined.export(output, format="mp3", bitrate="128k")
        output.seek(0)

        logger.info(
            f"[PodcastService] Audio merged: {len(segments)} segments, "
            f"{len(combined) / 1000:.1f}s duration, {len(output.getvalue()) / 1024:.0f} KB"
        )
        return output.getvalue()

    def _merge_raw(self, segments: list[tuple[str, bytes]]) -> bytes:
        """Fallback: raw MP3 concatenation (no gaps, lower quality)."""
        logger.warning("[PodcastService] Using raw MP3 concat (pydub not available)")
        combined = io.BytesIO()
        for _, mp3_bytes in segments:
            combined.write(mp3_bytes)
        return combined.getvalue()

    def generate_and_save(self, script_json: list, filename: str, folder: str = "podcasts") -> str:
        """
        Generate audio and upload to storage.

        Returns:
            The public URL of the uploaded MP3.
        """
        audio_bytes = self.generate_audio(script_json)
        if not self.storage:
            raise RuntimeError("Storage provider not configured in PodcastGenerator.")
        return self.storage.save(audio_bytes, filename, folder)
