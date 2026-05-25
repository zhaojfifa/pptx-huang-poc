import base64
import json
import logging
import time

from openai import OpenAI

from config.settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


def _encode_image(image_path: str) -> str:
    """Encode image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _strip_json_fences(raw: str) -> str:
    """Strip markdown code fences and surrounding prose from an LLM JSON response.

    Q3d: models occasionally wrap JSON in ```json … ``` or add a sentence before the
    object. We unwrap a fenced block if present, else slice from the first { or [ to the
    matching last } or ]. Returns the best-effort JSON substring (caller still json.loads)."""
    if not isinstance(raw, str):
        return raw
    s = raw.strip()
    if s.startswith("```"):
        # drop the opening fence line (``` or ```json) and the trailing fence
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
        s = s.strip()
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    # If still not starting with a JSON token, slice to the outermost object/array.
    if s and s[0] not in "{[":
        starts = [p for p in (s.find("{"), s.find("[")) if p != -1]
        ends = [p for p in (s.rfind("}"), s.rfind("]")) if p != -1]
        if starts and ends and max(ends) > min(starts):
            s = s[min(starts):max(ends) + 1]
    return s


class LLMSkill:
    """Unified LLM client for OpenAI-compatible APIs. Supports text and vision."""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self._api_key = api_key or LLM_API_KEY
        self._base_url = base_url or LLM_BASE_URL
        self.model = model or LLM_MODEL
        self.temperature = LLM_TEMPERATURE
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "LLM API key not configured. Please set LLM_API_KEY environment variable."
                )
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=300,
                max_retries=2,
            )
        return self._client

    def chat(self, prompt: str, system: str = None, temperature: float = None, json_mode: bool = False, enable_thinking: bool = True) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Auto-set temperature based on thinking mode:
        # - thinking disabled (fast generation): 0.6
        # - thinking enabled (reasoning mode): 1.0
        if enable_thinking:
            temp = 1.0
        else:
            temp = 0.6

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if not enable_thinking:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

        logger.info(f"LLM request with model={self.model}, temp={temp}, json_mode={json_mode}, thinking={enable_thinking}")
        
        last_error = None
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                logger.info("LLM response received.")
                return content
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                # Temperature errors: do NOT auto-retry with hardcoded values.
                # Different models require different temperatures (e.g. kimi-k2.6 only accepts 0.6).
                # Blindly retrying with 1.0 causes "only 0.6 is allowed" failures.
                # Fix the temperature via LLM_TEMPERATURE env var instead.
                if "temperature" in error_msg:
                    raise
                if "connection" in error_msg and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(f"Connection error on attempt {attempt + 1}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"LLM API error: {e}")
                raise
        raise last_error

    def chat_with_image(self, prompt: str, image_path: str, system: str = None, temperature: float = None, json_mode: bool = False, enable_thinking: bool = True) -> str:
        """Send a chat request with an image (vision mode)."""
        base64_image = _encode_image(image_path)

        content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                },
            },
        ]

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})

        # Auto-set temperature based on thinking mode
        if enable_thinking:
            temp = 1.0
        else:
            temp = 0.6

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if not enable_thinking:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

        logger.info(f"LLM vision request with model={self.model}, image={image_path}, thinking={enable_thinking}")

        last_error = None
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                result = resp.choices[0].message.content
                logger.info("LLM vision response received.")
                return result
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                if "temperature" in error_msg:
                    raise
                if "connection" in error_msg and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(f"Connection error on attempt {attempt + 1}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"LLM vision API error: {e}")
                raise
        raise last_error

    def chat_structured(self, prompt: str, system: str = None, temperature: float = None, enable_thinking: bool = True) -> dict:
        raw = self.chat(prompt, system=system, temperature=temperature, json_mode=True, enable_thinking=enable_thinking)
        # Q3d robustness: tolerate fenced/prose-wrapped JSON; one bounded re-ask on failure.
        try:
            return json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            logger.warning("LLM JSON parse failed; retrying once with a stricter instruction.")
            try:
                raw2 = self.chat(prompt + "\n\n只输出合法 JSON，不要任何解释或代码块标记。",
                                 system=system, temperature=temperature, json_mode=True,
                                 enable_thinking=enable_thinking)
                return json.loads(_strip_json_fences(raw2))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response after retry: {raw[:500]}")
                raise ValueError(f"LLM 返回的不是合法 JSON：{e}") from e
