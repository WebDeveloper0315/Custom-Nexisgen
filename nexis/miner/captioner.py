"""Per-clip captioning for the miner pipeline.

The captioner takes the first frame of each clip and asks an OpenAI-compatible
vision model for a short prompt-style description. Captions feed into the
trainer manifest's `prompt` field; if no API key is configured the captioner
returns an empty string and the trainer falls back to its default prompt.
"""

from __future__ import annotations

import base64
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


_PROMPT = (
    "Describe this video frame in one short sentence (≤ 20 words) that would "
    "work as a text-to-video generation prompt. Focus on subject, setting, and "
    "motion cues. Do not add commentary."
)

_RATE_LIMIT_HINT_RE = re.compile(
    r"try again in (\d+(?:\.\d+)?)\s*(ms|seconds?|s)\b",
    re.IGNORECASE,
)


def _b64_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "rate_limit" in msg


def rate_limit_wait_sec(exc: Exception, *, tpm_cooldown_sec: float) -> float:
    """Seconds to wait after a TPM/RPM 429 before retrying."""
    match = _RATE_LIMIT_HINT_RE.search(str(exc))
    if match:
        amount = float(match.group(1))
        unit = match.group(2).lower()
        hinted = amount / 1000.0 if unit == "ms" else amount
    else:
        hinted = 0.0
    return max(tpm_cooldown_sec, hinted)


@dataclass
class Captioner:
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str | None = None
    timeout_sec: int = 30
    delay_sec: float = 1.0
    max_retries: int = 8
    tpm_cooldown_sec: float = 60.0

    def __post_init__(self) -> None:
        self._client = None
        if not self.api_key.strip():
            logger.info("captioner disabled: no API key configured")
            return
        try:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or None,
                timeout=float(self.timeout_sec),
                max_retries=0,
            )
        except Exception as exc:
            logger.warning("captioner init failed err=%s; will return empty captions", exc)
            self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def caption_frame(self, frame_path: Path) -> str:
        if self._client is None or not frame_path.exists():
            return ""
        data_url = f"data:image/jpeg;base64,{_b64_image(frame_path)}"
        last_exc: Exception | None = None
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _PROMPT},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_tokens=80,
            )
            text = (resp.choices[0].message.content or "").strip()
            logger.info("Returned Result From GPT:%s -- %s", text, frame_path)
            # Removed the delay
            return text[:300]
        except Exception as exc:
            last_exc = exc
            logger.error("caption call failed frame=%s err=%s", frame_path, exc)
            return ""
