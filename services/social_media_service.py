
import os
import shutil
import uuid
import yt_dlp
import glob

class SocialMediaExtractor:
    TEMP_DIR = "temp_video"

    @classmethod
    def download_video(cls, url: str) -> dict:
        """
        Downloads a video from a social media URL using yt-dlp.
        Returns a dictionary with the local file path and the video caption/description.
        """
        if not os.path.exists(cls.TEMP_DIR):
            os.makedirs(cls.TEMP_DIR)

        # Generate a unique ID for this download to avoid collisions
        unique_id = str(uuid.uuid4())
        output_template = f"{cls.TEMP_DIR}/{unique_id}.%(ext)s"

        ydl_opts = {
            'format': 'best[ext=mp4]',  # Prefer MP4 for Gemini compatibility
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'writethumbnail': True,  # Ask yt-dlp to also grab the cover image
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Handling filename scenarios (sometimes yt-dlp might change extensions)
                expected_filename = ydl.prepare_filename(info)
                
                if not os.path.exists(expected_filename):
                    raise FileNotFoundError(f"Expected file {expected_filename} not found.")

                caption = info.get('description') or info.get('title') or "No caption provided."
                
                # The thumbnail is typically saved with the same base name but a different extension (.jpg, .webp)
                base_path = os.path.splitext(expected_filename)[0]
                possible_thumbs = glob.glob(f"{base_path}.*")
                thumbnail_path = None
                for t in possible_thumbs:
                    if not t.endswith('.mp4'):
                        thumbnail_path = t
                        break
                        
                return {
                    "video_path": expected_filename,
                    "caption": caption,
                    "thumbnail_path": thumbnail_path
                }

        except Exception as e:
            # Cleanup if partially failed?
            raise ValueError(f"Failed to download video: {str(e)}")

    @classmethod
    def extract_metadata(cls, url: str) -> dict:
        """
        Extracts metadata (caption/description) without downloading media.
        Perfect for fast triage!
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                caption = info.get('description') or info.get('title') or "No caption provided."
                return {
                    "caption": caption
                }
        except Exception as e:
            raise ValueError(f"Failed to extract metadata: {str(e)}")

    @classmethod
    def cleanup(cls, video_path: str, thumbnail_path: str = None):
        """Removes the temporary video and thumbnail files."""
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
