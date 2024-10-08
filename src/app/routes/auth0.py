from urllib.parse import quote_plus, urlencode

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.authentication import get_user_by_email
from app.core.config_manager import config
from app.core.database import get_db
from app.core.utils import setup_logger
from app.services.user import create_user

# Set up API router
router = APIRouter(tags=["Auth0"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

# Initialize OAuth client
oauth = OAuth()
oauth.register(
    "auth0",
    client_id=config.auth0_client_id,
    client_secret=config.auth0_client_secret,
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{config.auth0_domain}/.well-known/openid-configuration',
)


# Auth0-related routes


@router.get("/auth0/login")
async def login(request: Request) -> RedirectResponse:
    """
    Initiate the Auth0 login process.

    Args:
        request (Request): The incoming request object.

    Returns:
        RedirectResponse: Redirect to Auth0 login page.
    """
    try:
        redirect_uri = request.url_for("auth0_callback")
        logger.info(f"Initiating Auth0 login for redirect URI: {redirect_uri}")
        return await oauth.auth0.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Error initiating Auth0 login: {str(e)}")
        return {"error": "Authorization failed"}


@router.get("/auth0/callback")
async def auth0_callback(request: Request, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    """
    Handle the Auth0 callback after successful authentication.

    Args:
        request (Request): The incoming request object.
        db (AsyncSession): The database session.

    Returns:
        RedirectResponse: Redirect to the logged-in page or login page on failure.
    """
    token = await oauth.auth0.authorize_access_token(request)
    user_info = token.get('userinfo')

    if not user_info:
        logger.warning("No user info found in Auth0 token")
        return RedirectResponse(url=request.url_for("login"))

    email = user_info['email']
    name = user_info['name']
    auth0_user_id = user_info['sub']
    email_verified = user_info['email_verified']


    # Check if user exists, if not, create a new user
    db_user = await get_user_by_email(db, email)
    if not db_user:
        logger.info(f"Creating new user with email: {email}")
        db_user = await create_user(db, name, email, auth0_user_id, email_verified)
    else:
        # Update email verification status if it has changed
        if db_user.email_verified != email_verified:
            db_user.email_verified = email_verified
            await db.commit()
            logger.info(f"Updated email verification status for user: {email}")
        logger.info(f"Existing user logged in with email: {email}")

    # Store user information in the session
    request.session['user'] = {
        'id': str(db_user.id),
        'email': db_user.email,
        'name': db_user.name
    }

    logger.info(f"User {email} successfully authenticated")
    return RedirectResponse(url=config.ui_url if not config.use_api_ui else request.base_url)


@router.get("/auth0/logout")
async def logout(request: Request, response: Response) -> RedirectResponse:
    """
    Log out the user from the application and Auth0.

    Args:
        request (Request): The incoming request object.
        response (Response): The response object.

    Returns:
        RedirectResponse: Redirect to Auth0 logout URL.
    """
    logger.info("Logging out user")
    request.session.pop('user', None)
    response.delete_cookie("session")

    logout_url = f"https://{config.auth0_domain}/v2/logout?" + urlencode(
        {
            "returnTo": config.ui_url if not config.use_api_ui else request.base_url,
            "client_id": config.auth0_client_id,
        },
        quote_via=quote_plus,
    )
    logger.info(f"Redirecting to Auth0 logout URL: {logout_url}")
    return RedirectResponse(url=logout_url)
