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
BRAND_LOGO_PATH = PROJECT_ROOT / "assets" / "bizvision-logo.png"
BRAND_FAVICON_PATH = PROJECT_ROOT / "assets" / "bizvision-favicon.png"


@lru_cache(maxsize=1)
def brand_logo_data_uri() -> str:
    encoded = base64.b64encode(BRAND_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
