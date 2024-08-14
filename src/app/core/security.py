import secrets
from datetime import datetime, timedelta

from bcrypt import hashpw, checkpw, gensalt
from jose import jwt, JWTError

from app.config_manager import config
from app.core.exceptions import InvalidTokenError
from app.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

SECRET_KEY = config.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    """
    return checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    Generate a hash for a password.
    """
    return hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Created access token for user: {data.get('sub')}")
    return encoded_jwt


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and its hash.
    """
    api_key = secrets.token_urlsafe(32)
    hashed_key = get_password_hash(api_key)
    logger.info("Generated new API key")
    return api_key, hashed_key


def verify_api_key_hash(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.
    """
    return verify_password(api_key, hashed_key)


def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token.
    """
    delta = timedelta(hours=24)
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    logger.info(f"Generated password reset token for email: {email}")
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    """
    Verify a password reset token.
    """
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token["sub"]
    except JWTError:
        logger.warning(f"Invalid password reset token: {token[:10]}...")
        raise InvalidTokenError("Invalid password reset token")
