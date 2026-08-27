from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path


BRAND_NAME = "BizVision AI"
BRAND_TAGLINE = "Business performance ko analyze karne wali intelligent vision"
BRAND_SHORT_DESCRIPTION = (
    "Upload business data, uncover AI-powered insights, visualize performance, "
    "forecast trends, detect anomalies, and generate governed reports."
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
BRAND_LOGO_PATH = ASSETS_DIR / "logo_full.png"
BRAND_ICON_PATH = ASSETS_DIR / "logo_icon.png"
BRAND_FAVICON_PATH = ASSETS_DIR / "favicon.png"


@lru_cache(maxsize=8)
def get_base64_image(path: str | Path) -> str:
    image_path = Path(path)
    if not image_path.is_absolute():
        image_path = PROJECT_ROOT / image_path
    return base64.b64encode(image_path.read_bytes()).decode("ascii")


@lru_cache(maxsize=8)
def image_data_uri(path: str | Path, mime_type: str = "image/png") -> str:
    return f"data:{mime_type};base64,{get_base64_image(path)}"


@lru_cache(maxsize=1)
def brand_logo_data_uri() -> str:
    return image_data_uri(BRAND_LOGO_PATH)


@lru_cache(maxsize=1)
def brand_icon_data_uri() -> str:
    return image_data_uri(BRAND_ICON_PATH)


@lru_cache(maxsize=1)
def brand_favicon_data_uri() -> str:
    return image_data_uri(BRAND_FAVICON_PATH)
