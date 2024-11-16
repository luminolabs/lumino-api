import pytest
from bcrypt import hashpw

from app.core.cryptography import verify_password, get_password_hash, generate_api_key


def test_password_hash_and_verify():
    """Test that password hashing and verification work correctly."""
    password = "test_password123"
    hashed = get_password_hash(password)

    # Verify the hash is not the plain password
    assert hashed != password

    # Verify the correct password
    assert verify_password(password, hashed) is True

    # Verify an incorrect password
    assert verify_password("wrong_password", hashed) is False


def test_password_hash_different_for_same_password():
    """Test that the same password generates different hashes."""
    password = "test_password123"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Hashes should be different due to random salt
    assert hash1 != hash2

    # But both should verify
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_verify_password_with_empty_strings():
    """Test password verification with empty strings."""
    # Hash an empty password
    empty_hash = get_password_hash("")

    # Verify empty string against empty string hash
    assert verify_password("", empty_hash) is True

    # Verify non-empty string against empty string hash
    assert verify_password("some_password", empty_hash) is False


def test_password_hash_encoding():
    """Test that password hashing handles encoding correctly."""
    # Test with special characters
    password = "test_пароль_🔑"
    hashed = get_password_hash(password)

    # Verify the password
    assert verify_password(password, hashed) is True


def test_verify_password_with_invalid_hash():
    """Test password verification with invalid hash formats."""
    password = "test_password"

    # Test with non-hashed password (should raise ValueError)
    with pytest.raises(ValueError):
        verify_password(password, password)

    # Test with invalid hash format
    with pytest.raises(ValueError):
        verify_password(password, "invalid_hash")

    # Test with empty hash
    with pytest.raises(ValueError):
        verify_password(password, "")


def test_generate_api_key():
    """Test API key generation."""
    # Generate an API key
    key, key_hash = generate_api_key()

    # Check that key and hash are not empty
    assert key != ""
    assert key_hash != ""

    # Check that key and hash are different
    assert key != key_hash

    # Verify the key against its hash
    assert verify_password(key, key_hash) is True


def test_generate_api_key_uniqueness():
    """Test that generated API keys are unique."""
    # Generate multiple API keys
    num_keys = 10
    keys = set()
    hashes = set()

    for _ in range(num_keys):
        key, hash_value = generate_api_key()
        keys.add(key)
        hashes.add(hash_value)

    # Check that all keys and hashes are unique
    assert len(keys) == num_keys
    assert len(hashes) == num_keys


def test_api_key_length():
    """Test that generated API keys have sufficient length for security."""
    key, _ = generate_api_key()

    # Key should be at least 32 bytes when base64 decoded
    # This ensures sufficient entropy
    assert len(key) >= 43  # ~32 bytes in base64url encoding


def test_hash_password_with_long_password():
    """Test hashing of long passwords."""
    # Create a very long password
    long_password = "a" * 1000

    # Hash should work and still verify
    hashed = get_password_hash(long_password)
    assert verify_password(long_password, hashed) is True


def test_generate_api_key_format():
    """Test that generated API keys are in the expected format."""
    key, _ = generate_api_key()

    # Check that the key contains only valid characters
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert all(c in valid_chars for c in key)

    # Check that the key doesn't contain padding
    assert not key.endswith('=')


def test_password_hash_is_valid_bcrypt():
    """Test that generated password hashes are valid bcrypt hashes."""
    password = "test_password"
    hashed = get_password_hash(password)

    # Bcrypt hashes should:
    # 1. Start with $2b$ (bcrypt identifier)
    # 2. Be 60 characters long
    assert hashed.startswith('$2b$')
    assert len(hashed) == 60

    # Should be usable with bcrypt directly
    assert hashpw(password.encode('utf-8'), hashed.encode('utf-8')).decode('utf-8') == hashed
