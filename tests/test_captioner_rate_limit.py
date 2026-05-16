from nexis.miner.captioner import rate_limit_wait_sec


def test_rate_limit_wait_prefers_tpm_cooldown() -> None:
    exc = Exception(
        "429 Rate limit: Please try again in 243ms. tokens per min (TPM)"
    )
    assert rate_limit_wait_sec(exc, tpm_cooldown_sec=60.0) == 60.0


def test_rate_limit_wait_honors_longer_api_hint() -> None:
    exc = Exception("Please try again in 90 seconds")
    assert rate_limit_wait_sec(exc, tpm_cooldown_sec=60.0) == 90.0
