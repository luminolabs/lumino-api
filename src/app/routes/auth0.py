from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config_manager import config
from app.core.database import get_db
from app.core.utils import setup_logger
from app.services.auth0 import Auth0Service

router = APIRouter(tags=["Auth0"])
logger = setup_logger(__name__)

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

# Initialize Auth0 service
auth0_service = Auth0Service(oauth)


@router.get("/auth0/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate Auth0 login process."""
    try:
        login_url = await auth0_service.get_login_url(request)
        return RedirectResponse(url=login_url)
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return RedirectResponse(url=request.url_for("login"))


@router.get("/auth0/callback")
async def auth0_callback(
        request: Request,
        db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    """Handle Auth0 callback after successful authentication."""
    try:
        # Process callback and get user
        session_data, _ = await auth0_service.handle_callback(request, db)

        # Store user information in session
        request.session['user'] = session_data

        # Redirect to appropriate URL
        return RedirectResponse(
            url=config.ui_url if not config.use_api_ui else request.base_url
        )
    except Exception as e:
        logger.error(f"Callback failed: {str(e)}")
        return RedirectResponse(url=request.url_for("login"))


@router.get("/auth0/logout")
async def logout(request: Request, response: Response) -> RedirectResponse:
    """Log out user from application and Auth0."""
    # Clear session
    request.session.pop('user', None)
    response.delete_cookie("session")

    # Get logout URL and redirect
    logout_url = auth0_service.get_logout_url(request)
    logger.info(f"Logging out user, redirecting to: {logout_url}")
    return RedirectResponse(url=logout_url)
