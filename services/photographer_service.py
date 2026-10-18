from io import BytesIO

from PIL import Image

from services.image_generation import generate_image


def generate_actual_image(visual_prompt: str, number_of_images: int = 1) -> list[Image.Image]:
    """Generate images for a prompt with the Gemini image model.

    The Gemini image models return one image per call, so several images
    means several calls. Returns a list of PIL images.
    """
    images = []
    for _ in range(number_of_images):
        data, _meta = generate_image(visual_prompt)
        images.append(Image.open(BytesIO(data)))
    return images
