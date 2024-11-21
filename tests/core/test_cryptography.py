from app.core.cryptography import verify_password, get_password_hash, generate_api_key


def test_password_hashing_and_verification():
    """Test password hashing and verification flow."""
    # Test with a typical password
    password = "MySecurePassword123"
    hashed = get_password_hash(password)

    # Verify correct password
    assert verify_password(password, hashed)

    # Verify incorrect password
    assert not verify_password("WrongPassword123", hashed)

    # Test with special characters
    password_special = "My@#$%^&*Pass"
    hashed_special = get_password_hash(password_special)
    assert verify_password(password_special, hashed_special)


def test_password_hash_consistency():
    """Test that password hashing is consistent but unique."""
    password = "TestPassword123"

    # Generate multiple hashes for the same password
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Hashes should be different (due to salt)
    assert hash1 != hash2

    # But both should verify correctly
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)


def test_password_hash_length():
    """Test that password hashes have consistent length."""
    # Test with different length passwords
    short_pass = "short"
    long_pass = "averyverylongpasswordthatiswaytoolongtobeuseful"

    short_hash = get_password_hash(short_pass)
    long_hash = get_password_hash(long_pass)

    # Hash lengths should be the same regardless of password length
    assert len(short_hash) == len(long_hash)


def test_generate_api_key():
    """Test API key generation."""
    # Generate multiple API keys
    key1, hash1 = generate_api_key()
    key2, hash2 = generate_api_key()

    # Keys should be different
    assert key1 != key2
    assert hash1 != hash2

    # Keys should be properly formatted
    assert len(key1) > 32  # At least 32 bytes of randomness
    assert isinstance(key1, str)
    assert isinstance(hash1, str)

    # Hashes should verify against their keys
    assert verify_password(key1, hash1)
    assert verify_password(key2, hash2)

    # Hashes should not verify against wrong keys
    assert not verify_password(key1, hash2)
    assert not verify_password(key2, hash1)


def test_password_verification_edge_cases():
    """Test password verification with edge cases."""
    # Test empty password
    empty_hash = get_password_hash("")
    assert verify_password("", empty_hash)
    assert not verify_password("notempty", empty_hash)

    # Test whitespace
    space_password = "   spaces   "
    space_hash = get_password_hash(space_password)
    assert verify_password(space_password, space_hash)
    assert not verify_password("spaces", space_hash)

    # Test Unicode
    unicode_password = "пароль123"
    unicode_hash = get_password_hash(unicode_password)
    assert verify_password(unicode_password, unicode_hash)
    assert not verify_password("password123", unicode_hash)


def test_api_key_format():
    """Test API key format and properties."""
    key, hash = generate_api_key()

    # Key should be URL safe
    assert all(c.isalnum() or c in '-_' for c in key)

    # Key should be of reasonable length
    assert 32 <= len(key) <= 64  # typical range for secure tokens

    # Hash should be in standard bcrypt format
    assert len(hash) > 50  # bcrypt hashes are typically longer than 50 chars
    assert '$' in hash  # bcrypt hashes contain $ separators
