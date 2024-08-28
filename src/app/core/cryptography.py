import secrets
from datetime import datetime, timedelta

from bcrypt import hashpw, checkpw, gensalt
from jose import jwt, JWTError

from app.core.config_manager import config
from app.core.exceptions import InvalidBearerTokenError
from app.core.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password (str): The plain text password.
        hashed_password (str): The hashed password.
    Returns:
        bool: Whether the password is correct.
    """
    return checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    Generate a hash for a password.

    Args:
        password (str): The password to hash.
    Returns:
        str: The hashed password.
    """
    return hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')


def create_bearer_token(data: dict, expires_delta: timedelta = config.bearer_token_expire_minutes) -> str:
    """
    Create a JWT access token.

    Args:
        data (dict): The data to encode in the token.
        expires_delta (timedelta): The time delta for the token expiration.
    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.bearer_token_secret_key, algorithm=config.bearer_token_algorithm)
    logger.info(f"Created access token for user: {data.get('sub')}")
    return encoded_jwt


def decode_bearer_token(token: str) -> dict:
    """
    Decode a bearer token.

    Args:
        token (str): The token to decode.
    Returns:
        dict: The decoded token data.
    """
    try:
        return jwt.decode(token, config.bearer_token_secret_key, algorithms=[config.bearer_token_algorithm])
    except JWTError:
        raise InvalidBearerTokenError(f"Invalid bearer token: {token[:8]}...", logger)


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and its hash.

    Returns:
        tuple[str, str]: The API key and its hashed value.
    """
    api_key = secrets.token_urlsafe(32)
    key_hash = get_password_hash(api_key)
    logger.info("Generated new API key")
    return api_key, key_hash
