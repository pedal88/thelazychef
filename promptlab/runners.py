"""Call a model with one prompt. Each runner returns (output, meta).

Image runners return PNG bytes; text runners return a string. meta holds
whatever the API reports (tokens, finish reason) for the run log.
"""


def run_image(model: str, prompt: str) -> tuple[bytes, dict]:
    from services.image_generation import generate_image

    return generate_image(prompt, model=model, attempts=1)


def run_text(model: str, prompt: str) -> tuple[str, dict]:
    raise NotImplementedError("Text tasks get a Claude runner in step 5 (fase 0b).")


RUNNERS = {'image': run_image, 'text': run_text}
