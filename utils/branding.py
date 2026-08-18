from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote


BRAND_NAME = "BizVision AI"
BRAND_TAGLINE = "Business performance ko analyze karne wali intelligent vision"
BRAND_SHORT_DESCRIPTION = (
    "Upload business data, uncover AI-powered insights, visualize performance, "
    "forecast trends, detect anomalies, and generate governed reports."
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRAND_LOGO_PATH = PROJECT_ROOT / "assets" / "bizvision-logo.svg"
BRAND_FAVICON_PATH = PROJECT_ROOT / "assets" / "bizvision-favicon.svg"

BRAND_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 150" role="img" aria-labelledby="title desc">
  <title>BizVision AI</title>
  <desc>Abstract eye and rising chart mark with BizVision AI wordmark.</desc>
  <defs>
    <linearGradient id="markGradient" x1="18" y1="125" x2="130" y2="20" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#7c3cff"/>
      <stop offset="0.48" stop-color="#00d4ff"/>
      <stop offset="1" stop-color="#2f6bff"/>
    </linearGradient>
    <linearGradient id="wordGradient" x1="220" y1="42" x2="582" y2="110" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#f7fbff"/>
      <stop offset="0.55" stop-color="#8fdfff"/>
      <stop offset="1" stop-color="#8a55ff"/>
    </linearGradient>
    <filter id="softGlow" x="-35%" y="-35%" width="170%" height="170%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feColorMatrix in="blur" type="matrix" values="0 0 0 0 0.18 0 0 0 0 0.43 0 0 0 0 1 0 0 0 .58 0"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <g filter="url(#softGlow)">
    <path d="M18 78C42 37 79 24 124 52c-26 52-72 72-124 49 4-8 10-16 18-23Z" fill="none" stroke="url(#markGradient)" stroke-width="10" stroke-linecap="round"/>
    <path d="M25 91c26-28 62-42 107-44" fill="none" stroke="url(#markGradient)" stroke-width="10" stroke-linecap="round"/>
    <circle cx="80" cy="73" r="19" fill="#081126" stroke="url(#markGradient)" stroke-width="8"/>
    <path d="M51 114V89M78 114V76M105 114V62" stroke="url(#markGradient)" stroke-width="11" stroke-linecap="round"/>
    <path d="M97 60l24-24 5 34" fill="none" stroke="#00d4ff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <rect x="164" y="30" width="2.5" height="90" rx="1.25" fill="#2942ff" opacity=".75"/>
  <text x="196" y="94" fill="url(#wordGradient)" font-family="Inter, Poppins, Segoe UI, Arial, sans-serif" font-size="58" font-weight="850" letter-spacing="-1">BizVision</text>
  <text x="505" y="94" fill="#8a55ff" font-family="Inter, Poppins, Segoe UI, Arial, sans-serif" font-size="58" font-weight="900" letter-spacing="-1">AI</text>
</svg>"""

BRAND_FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="g" x1="20" y1="108" x2="106" y2="18" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#7c3cff"/>
      <stop offset=".5" stop-color="#00d4ff"/>
      <stop offset="1" stop-color="#2f6bff"/>
    </linearGradient>
  </defs>
  <rect x="8" y="8" width="112" height="112" rx="30" fill="#080d1f"/>
  <path d="M20 68c21-31 55-39 88-15-20 35-53 48-88 29 3-5 6-10 10-14Z" fill="none" stroke="url(#g)" stroke-width="8" stroke-linecap="round"/>
  <circle cx="62" cy="62" r="13" fill="#080d1f" stroke="url(#g)" stroke-width="7"/>
  <path d="M39 98V78M61 98V64M83 98V53" stroke="url(#g)" stroke-width="8" stroke-linecap="round"/>
  <path d="M80 52l19-19 4 27" fill="none" stroke="#00d4ff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


def _ensure_brand_svgs() -> None:
    BRAND_LOGO_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BRAND_LOGO_PATH.exists() or BRAND_LOGO_PATH.read_text(encoding="utf-8") != BRAND_LOGO_SVG:
        BRAND_LOGO_PATH.write_text(BRAND_LOGO_SVG, encoding="utf-8")
    if not BRAND_FAVICON_PATH.exists() or BRAND_FAVICON_PATH.read_text(encoding="utf-8") != BRAND_FAVICON_SVG:
        BRAND_FAVICON_PATH.write_text(BRAND_FAVICON_SVG, encoding="utf-8")


@lru_cache(maxsize=1)
def brand_logo_data_uri() -> str:
    _ensure_brand_svgs()
    return f"data:image/svg+xml;charset=utf-8,{quote(BRAND_LOGO_SVG)}"


@lru_cache(maxsize=1)
def brand_favicon_data_uri() -> str:
    _ensure_brand_svgs()
    return f"data:image/svg+xml;charset=utf-8,{quote(BRAND_FAVICON_SVG)}"
