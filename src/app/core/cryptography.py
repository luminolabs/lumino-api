import secrets

from bcrypt import hashpw, checkpw, gensalt

from app.core.config_manager import config
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
