import os
import time
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = "https://api.deepseek.com"
_MODEL = "deepseek-chat"
_MAX_RETRIES = 3
_TIMEOUT_SECONDS = 30
_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY tidak ditemui dalam .env. "
                "Sila tetapkan kunci API DeepSeek anda."
            )
        _client = OpenAI(
            api_key=api_key,
            base_url=_BASE_URL,
            timeout=_TIMEOUT_SECONDS,
        )
    return _client


def chat_completion(
    messages: list[dict],
    model: str = _MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    **kwargs,
) -> str:
    """Call DeepSeek chat completion with retry and error handling.

    Returns the assistant message content string.
    Raises RuntimeError with a user-facing message on persistent failure.
    """
    client = get_client()
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content
        except APITimeoutError as e:
            last_error = e
        except APIConnectionError as e:
            last_error = e
        except APIError as e:
            last_error = e
            if e.status_code and 400 <= e.status_code < 500:
                break

        if attempt < _MAX_RETRIES:
            time.sleep(2 ** attempt)

    raise RuntimeError(
        "Tidak dapat menghubungi DeepSeek API selepas beberapa percubaan. "
        "Sila semak sambungan internet anda dan cuba lagi.\n"
        f"Ralat terakhir: {last_error}"
    )
