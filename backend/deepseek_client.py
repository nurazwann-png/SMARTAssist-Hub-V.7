import os
import time
import logging
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.deepseek.com"
_MODEL = "deepseek-chat"
_TIMEOUT_SECONDS = 30
_client = None

# ── Retry config ─────────────────────────────────────────────────────────────
_MAX_RETRIES = 3        # bilangan maksimum percubaan semula
_BACKOFF_BASE = 2       # asas untuk exponential backoff (2^attempt saat)
_BACKOFF_MAX = 16       # had maksimum masa tunggu (saat)
_JITTER = 0.5           # tambah sedikit rawak agar panggilan serentak tidak bertembung

# ── Circuit Breaker config ────────────────────────────────────────────────────
_CB_FAILURE_THRESHOLD = 3   # bilangan kegagalan berturut-turut sebelum litar terbuka
_CB_RESET_TIMEOUT = 60      # saat sebelum cuba semula selepas litar terbuka


class _CircuitBreaker:
    """
    Tiga keadaan:
      CLOSED  — berfungsi normal, panggilan dibenarkan.
      OPEN    — terlalu banyak kegagalan, panggilan ditolak serta-merta.
      HALF    — tempoh tunggu tamat, satu percubaan dibenarkan untuk uji semula.
    """

    CLOSED = "CLOSED"
    OPEN   = "OPEN"
    HALF   = "HALF"

    def __init__(self, threshold: int, reset_timeout: int):
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = self.CLOSED
        self._opened_at: float = 0.0

    def _current_state(self) -> str:
        if self.state == self.OPEN:
            if time.time() - self._opened_at >= self.reset_timeout:
                self.state = self.HALF
                logger.info("[CircuitBreaker] Keadaan: OPEN → HALF (cubaan semula dibenarkan)")
        return self.state

    def allow_request(self) -> bool:
        return self._current_state() in (self.CLOSED, self.HALF)

    def record_success(self):
        if self.state != self.CLOSED:
            logger.info("[CircuitBreaker] Keadaan: %s → CLOSED (berjaya)", self.state)
        self.failures = 0
        self.state = self.CLOSED

    def record_failure(self):
        self.failures += 1
        logger.warning("[CircuitBreaker] Kegagalan %d/%d", self.failures, self.threshold)
        if self.failures >= self.threshold:
            self.state = self.OPEN
            self._opened_at = time.time()
            logger.error(
                "[CircuitBreaker] Keadaan: OPEN — DeepSeek API tidak responsif. "
                "Cuba semula dalam %ds.", self.reset_timeout
            )

    @property
    def status(self) -> dict:
        return {
            "state": self._current_state(),
            "failures": self.failures,
            "threshold": self.threshold,
            "seconds_until_retry": max(
                0, self.reset_timeout - (time.time() - self._opened_at)
            ) if self.state == self.OPEN else 0,
        }


_circuit_breaker = _CircuitBreaker(_CB_FAILURE_THRESHOLD, _CB_RESET_TIMEOUT)


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


def get_circuit_breaker_status() -> dict:
    """Kembalikan status circuit breaker semasa — berguna untuk endpoint /api/health."""
    return _circuit_breaker.status


def chat_completion(
    messages: list[dict],
    model: str = _MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    **kwargs,
) -> str:
    """Panggil DeepSeek dengan retry exponential backoff + circuit breaker.

    Aliran:
      1. Semak circuit breaker — jika OPEN, tolak serta-merta (elak menunggu timeout).
      2. Cuba sehingga _MAX_RETRIES kali dengan backoff 2^attempt saat (max 16s).
      3. Ralat 4xx (bad request) tidak diretry — terus gagal.
      4. Kegagalan berturut-turut akan membuka litar (_CB_FAILURE_THRESHOLD kali).
      5. Litar akan tutup semula selepas _CB_RESET_TIMEOUT saat.

    Mengembalikan kandungan teks respons AI.
    Menaikkan RuntimeError dengan mesej mesra pengguna jika gagal sepenuhnya.
    """
    # ── Semak circuit breaker dahulu ─────────────────────────────────────────
    if not _circuit_breaker.allow_request():
        cb = _circuit_breaker.status
        wait = int(cb["seconds_until_retry"])
        raise RuntimeError(
            f"Perkhidmatan AI sedang tidak tersedia (terlalu banyak kegagalan berturut-turut). "
            f"Sila cuba lagi dalam {wait} saat."
        )

    client = get_client()
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.debug("[DeepSeek] Percubaan %d/%d", attempt, _MAX_RETRIES)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            _circuit_breaker.record_success()
            return response.choices[0].message.content

        except APITimeoutError as e:
            last_error = e
            logger.warning("[DeepSeek] Timeout pada percubaan %d: %s", attempt, e)

        except APIConnectionError as e:
            last_error = e
            logger.warning("[DeepSeek] Sambungan gagal pada percubaan %d: %s", attempt, e)

        except APIError as e:
            last_error = e
            # Ralat 4xx bermakna permintaan tidak sah — retry tidak akan membantu
            if e.status_code and 400 <= e.status_code < 500:
                logger.error("[DeepSeek] Ralat %d (tidak diretry): %s", e.status_code, e)
                _circuit_breaker.record_failure()
                raise RuntimeError(
                    f"Permintaan tidak sah (ralat {e.status_code}). "
                    "Sila semak kunci API atau format permintaan anda."
                )
            logger.warning("[DeepSeek] Ralat API pada percubaan %d: %s", attempt, e)

        # ── Exponential backoff dengan jitter ─────────────────────────────────
        if attempt < _MAX_RETRIES:
            import random
            delay = min(_BACKOFF_BASE ** attempt, _BACKOFF_MAX)
            delay += random.uniform(0, _JITTER)
            logger.info("[DeepSeek] Tunggu %.1fs sebelum percubaan %d...", delay, attempt + 1)
            time.sleep(delay)

    # Semua percubaan gagal — rekod ke circuit breaker
    _circuit_breaker.record_failure()
    raise RuntimeError(
        "Tidak dapat menghubungi DeepSeek API selepas beberapa percubaan. "
        "Sila semak sambungan internet anda dan cuba lagi.\n"
        f"Ralat terakhir: {last_error}"
    )
