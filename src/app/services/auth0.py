from typing import Dict, Tuple
from urllib.parse import quote_plus, urlencode

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config_manager import config
from app.core.constants import BillingTransactionType
from app.core.utils import setup_logger
from app.models.user import User
from app.queries import users as user_queries
from app.services.billing import add_credits_to_user

logger = setup_logger(__name__)

class Auth0Service:
    """Service for handling Auth0 authentication."""

    def __init__(self, oauth):
        self.oauth = oauth
        self.client_id = config.auth0_client_id
        self.domain = config.auth0_domain
        self.ui_url = config.ui_url
        self.use_api_ui = config.use_api_ui
        self.new_user_credits = float(config.new_user_credits)

    async def get_login_url(self, request: Request) -> str:
        """
        Generate Auth0 login URL.

        Args:
            request: The incoming request

        Returns:
            URL to redirect user for Auth0 login
        """
        try:
            redirect_uri = request.url_for("auth0_callback")
            logger.info(f"Generated Auth0 login URL with redirect URI: {redirect_uri}")
            result = await self.oauth.auth0.authorize_redirect(request, redirect_uri)
            return result.headers["location"]
        except Exception as e:
            logger.error(f"Failed to generate Auth0 login URL: {str(e)}")
            raise

    def get_logout_url(self, request: Request) -> str:
        """
        Generate Auth0 logout URL.

        Args:
            request: The incoming request

        Returns:
            URL to redirect user for Auth0 logout
        """
        return_to = self.ui_url if not self.use_api_ui else str(request.base_url)

        return f"https://{self.domain}/v2/logout?" + urlencode(
            {
                "returnTo": return_to,
                "client_id": self.client_id,
            },
            quote_via=quote_plus,
        )

    async def handle_callback(
            self,
            request: Request,
            db: AsyncSession
    ) -> Tuple[Dict[str, str], User]:
        """
        Handle Auth0 callback and create/update user.

        Args:
            request: The incoming request
            db: Database session

        Returns:
            Tuple of session data and user object

        Raises:
            ValueError: If required user info is missing
        """
        # Get token and user info from Auth0
        token = await self.oauth.auth0.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            logger.warning("No user info found in Auth0 token")
            raise ValueError("No user info found in Auth0 token")

        # Extract user info
        email = user_info['email']
        name = user_info['name']
        auth0_user_id = user_info['sub']
        email_verified = user_info['email_verified']

        # Get or create user
        user = await self._get_or_create_user(
            db, name, email, auth0_user_id, email_verified
        )

        # Create session data
        session_data = {
            'id': str(user.id),
            'email': user.email,
            'name': user.name
        }

        logger.info(f"Successfully authenticated user: {email}")
        return session_data, user

    async def _get_or_create_user(
            self,
            db: AsyncSession,
            name: str,
            email: str,
            auth0_user_id: str,
            email_verified: bool
    ) -> User:
        """
        Get existing user or create new one.

        Args:
            db: Database session
            name: User's name
            email: User's email
            auth0_user_id: Auth0 user ID
            email_verified: Whether email is verified

        Returns:
            User object
        """
        # Check if user exists
        user = await user_queries.get_user_by_email(db, email)

        try:
            if user:
                # Update existing user if needed
                if user.email_verified != email_verified:
                    user.email_verified = email_verified
                    await db.commit()
                    logger.info(f"Updated email verification status for user: {email}")
            else:
                # Create new user
                user = User(
                    email=email,
                    name=name,
                    auth0_user_id=auth0_user_id,
                    email_verified=email_verified
                )
                db.add(user)
                await db.commit()

                # Add new user credits if configured
                if self.new_user_credits > 0:
                    await add_credits_to_user(
                        db,
                        user.id,
                        self.new_user_credits,
                        "NEW_USER_CREDIT",
                        BillingTransactionType.NEW_USER_CREDIT
                    )

                logger.info(f"Created new user: {email}")

            return user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in user creation/update: {str(e)}")
            raise
