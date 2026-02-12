import re

def _get_safe_filename(name: str) -> str:
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')
    return f"{safe_name}.png"

name = "Beef T-Bone And Porterhouse"
print(f"Original: {name}")
print(f"Safe: {_get_safe_filename(name)}")
