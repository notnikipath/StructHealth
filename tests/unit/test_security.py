from shared.structhealth_common import decrypt_text, encrypt_text, has_permission, sign_token, verify_token


def test_encrypt_roundtrip() -> None:
    secret = "demo-key"
    value = "critical bridge inspection data"
    encrypted = encrypt_text(value, secret)
    assert encrypted != value
    assert decrypt_text(encrypted, secret) == value


def test_token_roundtrip() -> None:
    token = sign_token({"sub": "ENG-001", "role": "engineer"}, "jwt-secret", exp_minutes=5)
    payload = verify_token(token, "jwt-secret")
    assert payload is not None
    assert payload["sub"] == "ENG-001"


def test_permissions() -> None:
    assert has_permission("engineer", "analysis:run")
    assert not has_permission("inspector", "analysis:run")
