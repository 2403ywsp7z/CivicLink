from app.core.security import hash_password, verify_password


def test_password_hash_not_plaintext():
    h = hash_password("Demo@CivicLink2026")
    assert h != "Demo@CivicLink2026"
    assert verify_password("Demo@CivicLink2026", h)
    assert not verify_password("wrong", h)
