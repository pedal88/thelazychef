"""
media_hub/video_engine.py — Multi-Modal Video Renderer

Uses MoviePy to compose social media videos:
  Scene 1 (The Hook):      Ken Burns zoom-in on Recipe Hero Image (5s)
  Scene 2 (The Breakdown):  2×2 collage of top 4 ingredient images (5s)

Overlays:
  - Subtitles: White text, black stroke, bottom-center (TikTok style)
  - Audio:     Background music track from static/audio/

Platform durations:
  - TikTok:    ~10-15s total
  - Instagram: ~15-30s total
"""

import io
import os
import logging
import tempfile
from typing import Optional

import requests
from PIL import Image as PilImage

logger = logging.getLogger(__name__)

# Attempt moviepy import — graceful degradation if not installed locally
try:
    from moviepy import (
        ImageClip,
        CompositeVideoClip,
        AudioFileClip,
        TextClip,
        concatenate_videoclips,
        vfx,
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    logger.warning("[VideoEngine] moviepy not installed — video rendering disabled")
    MOVIEPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PLATFORM_CONFIG = {
    "tiktok": {
        "resolution": (1080, 1920),   # 9:16 portrait
        "scene1_duration": 5,
        "scene2_duration": 5,
        "max_duration": 15,
        "fps": 24,
    },
    "instagram": {
        "resolution": (1080, 1920),   # 9:16 portrait
        "scene1_duration": 8,
        "scene2_duration": 7,
        "max_duration": 30,
        "fps": 24,
    },
}

AUDIO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "audio", "standard_kitchen_vibe.mp3")

# Subtitle styling
SUBTITLE_FONT_SIZE = 48
SUBTITLE_COLOR = "white"
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 3


# ---------------------------------------------------------------------------
# Image Fetching
# ---------------------------------------------------------------------------

def _fetch_image(url: str) -> Optional[PilImage.Image]:
    """Downloads an image from a URL and returns a PIL Image."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return PilImage.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception as e:
        logger.warning(f"[VideoEngine] Failed to fetch image {url}: {e}")
        return None


def _create_placeholder(width: int, height: int, color: tuple = (40, 40, 40)) -> PilImage.Image:
    """Creates a solid-color placeholder image."""
    return PilImage.new("RGB", (width, height), color)


# ---------------------------------------------------------------------------
# Scene 1: Ken Burns Zoom-In on Hero Image
# ---------------------------------------------------------------------------

def _build_scene1_hook(hero_image: PilImage.Image, config: dict) -> "ImageClip":
    """
    Applies a Ken Burns 'zoom-in' effect to the recipe hero image.

    The image starts at 100% scale and ends at ~120% scale over the scene duration,
    creating a slow cinematic zoom.
    """
    w, h = config["resolution"]
    duration = config["scene1_duration"]

    # Resize hero image to fill the frame (cover crop)
    hero_resized = _cover_crop(hero_image, w, h)

    # Save to temp file for MoviePy
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        hero_resized.save(tmp, format="JPEG", quality=95)
        tmp_path = tmp.name

    # Create clip with Ken Burns zoom effect
    clip = ImageClip(tmp_path, duration=duration)

    # Ken Burns: zoom from 1.0x to 1.2x over the duration
    zoom_start = 1.0
    zoom_end = 1.2

    def zoom_effect(get_frame, t):
        """Apply progressive zoom by resizing and center-cropping each frame."""
        import numpy as np

        frame = get_frame(t)
        progress = t / duration
        scale = zoom_start + (zoom_end - zoom_start) * progress

        fh, fw = frame.shape[:2]
        new_w = int(fw * scale)
        new_h = int(fh * scale)

        # Resize using PIL for quality
        img = PilImage.fromarray(frame)
        img_zoomed = img.resize((new_w, new_h), PilImage.LANCZOS)

        # Center crop back to original size
        left = (new_w - fw) // 2
        top = (new_h - fh) // 2
        img_cropped = img_zoomed.crop((left, top, left + fw, top + fh))

        return np.array(img_cropped)

    clip = clip.transform(zoom_effect)

    # Clean up temp file reference (MoviePy reads it on demand)
    return clip


# ---------------------------------------------------------------------------
# Scene 2: 2×2 Ingredient Collage
# ---------------------------------------------------------------------------

def _build_scene2_collage(ingredients: list[dict], config: dict) -> "ImageClip":
    """
    Creates a 2×2 collage from the top 4 ingredient images.
    Each quadrant gets one ingredient image, resized to fit.
    """
    w, h = config["resolution"]
    duration = config["scene2_duration"]

    half_w, half_h = w // 2, h // 2
    canvas = PilImage.new("RGB", (w, h), (20, 20, 20))

    positions = [(0, 0), (half_w, 0), (0, half_h), (half_w, half_h)]

    for i, pos in enumerate(positions):
        if i < len(ingredients) and ingredients[i].get("image_url"):
            img = _fetch_image(ingredients[i]["image_url"])
        else:
            img = None

        if img is None:
            img = _create_placeholder(half_w, half_h, (30 + i * 15, 30 + i * 10, 40))

        img_resized = _cover_crop(img, half_w, half_h)
        canvas.paste(img_resized, pos)

    # Save collage
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        canvas.save(tmp, format="JPEG", quality=95)
        tmp_path = tmp.name

    return ImageClip(tmp_path, duration=duration)


# ---------------------------------------------------------------------------
# Subtitles — TikTok Style
# ---------------------------------------------------------------------------

def _build_subtitle_clips(subtitle_segments: list[dict], config: dict) -> list:
    """
    Renders each subtitle segment as a TextClip positioned at bottom-center.
    White text with black stroke — the TikTok standard.
    """
    w, h = config["resolution"]
    clips = []

    for seg in subtitle_segments:
        text = seg.get("text", "")
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 2))

        if not text:
            continue

        try:
            txt_clip = TextClip(
                text=text,
                font_size=SUBTITLE_FONT_SIZE,
                color=SUBTITLE_COLOR,
                stroke_color=SUBTITLE_STROKE_COLOR,
                stroke_width=SUBTITLE_STROKE_WIDTH,
                size=(w - 80, None),  # Wrap within frame with padding
                method="caption",
                text_align="center",
            )
            txt_clip = (
                txt_clip
                .with_position(("center", h - 200))
                .with_start(start)
                .with_duration(end - start)
            )
            clips.append(txt_clip)
        except Exception as e:
            logger.warning(f"[VideoEngine] Subtitle render failed for '{text[:30]}': {e}")

    return clips


# ---------------------------------------------------------------------------
# Image Utilities
# ---------------------------------------------------------------------------

def _cover_crop(img: PilImage.Image, target_w: int, target_h: int) -> PilImage.Image:
    """
    Resizes and center-crops an image to exactly fill target_w × target_h
    (like CSS 'object-fit: cover').
    """
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    img_resized = img.resize((new_w, new_h), PilImage.LANCZOS)

    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img_resized.crop((left, top, left + target_w, top + target_h))


# ---------------------------------------------------------------------------
# Main Render Pipeline
# ---------------------------------------------------------------------------

def render_video(
    recipe: "Recipe",
    script_data: dict,
    platform: str,
    storage_provider,
) -> bytes:
    """
    Renders a complete social media video for the given recipe.

    Pipeline:
      1. Build Scene 1 (Ken Burns hero zoom)
      2. Build Scene 2 (2×2 ingredient collage)
      3. Concatenate scenes
      4. Overlay subtitles
      5. Layer background audio (if available)
      6. Export to MP4 bytes

    Args:
        recipe: Recipe ORM object.
        script_data: Parsed Gemini JSON with subtitle_segments and voiceover_script.
        platform: 'tiktok' or 'instagram'.
        storage_provider: For resolving image URLs.

    Returns:
        MP4 file bytes ready for upload.
    """
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("moviepy is not installed. Run: pip install moviepy")

    config = PLATFORM_CONFIG.get(platform)
    if not config:
        raise ValueError(f"Unknown platform: {platform}")

    logger.info(f"[VideoEngine] Rendering {platform} video for '{recipe.title}'")

    # --- Resolve hero image URL ---
    hero_url = None
    if recipe.image_filename:
        if hasattr(storage_provider, 'bucket_name'):
            hero_url = f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{recipe.image_filename}"
        else:
            hero_url = None  # Local — would need file path resolution

    hero_img = _fetch_image(hero_url) if hero_url else None
    if hero_img is None:
        hero_img = _create_placeholder(*config["resolution"])

    # --- Build ingredient list from orchestrator context ---
    ingredients = []
    sorted_ings = sorted(recipe.ingredients, key=lambda ri: ri.gram_weight or 0, reverse=True)[:4]
    for ri in sorted_ings:
        ing = ri.ingredient
        img_url = ing.image_url
        if img_url and hasattr(storage_provider, 'bucket_name') and not img_url.startswith("http"):
            img_url = f"https://storage.googleapis.com/{storage_provider.bucket_name}/pantry/{img_url}"
        ingredients.append({"name": ing.name, "image_url": img_url})

    # --- Build scenes ---
    scene1 = _build_scene1_hook(hero_img, config)
    scene2 = _build_scene2_collage(ingredients, config)

    # --- Concatenate ---
    video = concatenate_videoclips([scene1, scene2], method="compose")

    # --- Trim to max duration ---
    if video.duration > config["max_duration"]:
        video = video.subclipped(0, config["max_duration"])

    # --- Add subtitles ---
    subtitle_segments = script_data.get("subtitle_segments", [])
    if subtitle_segments:
        subtitle_clips = _build_subtitle_clips(subtitle_segments, config)
        if subtitle_clips:
            video = CompositeVideoClip([video] + subtitle_clips)

    # --- Layer background audio ---
    if os.path.exists(AUDIO_PATH):
        try:
            audio = AudioFileClip(AUDIO_PATH)
            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)
            # Reduce volume to not overpower potential voiceover
            audio = audio.with_volume_scaled(0.3)
            video = video.with_audio(audio)
        except Exception as e:
            logger.warning(f"[VideoEngine] Audio layering failed: {e}")

    # --- Export to bytes ---
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    video.write_videofile(
        tmp_path,
        fps=config["fps"],
        codec="libx264",
        audio_codec="aac",
        logger=None,  # Suppress moviepy progress bars
    )

    with open(tmp_path, "rb") as f:
        video_bytes = f.read()

    # Cleanup
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    video.close()

    logger.info(f"[VideoEngine] Rendered {len(video_bytes)} bytes for '{recipe.title}'")
    return video_bytes
