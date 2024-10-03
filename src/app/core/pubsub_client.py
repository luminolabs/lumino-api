import asyncio
import json
from typing import Callable
from uuid import UUID

from google.cloud import pubsub_v1
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.database import AsyncSessionLocal
from app.core.utils import setup_logger
from app.services.fine_tuned_model import create_fine_tuned_model

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def _handle_job_artifacts(db: AsyncSession, job_id: str, user_id: str, data: dict) -> bool:
    """Handle job artifacts received from Pub/Sub."""
    artifacts = {
        "base_url": data["base_url"],
        "weight_files": data["weight_files"],
        "other_files": data["other_files"]
    }
    model = await create_fine_tuned_model(db, UUID(job_id), UUID(user_id), artifacts)
    return model is not None


class PubSubClient:
    """Manages Google Cloud Pub/Sub operations."""

    # Message callback function
    message_callback: Callable = None

    def __init__(self, project_id: str):
        """
        Initialize the PubSubClient with a project ID.

        Args:
            project_id (str): The Google Cloud project ID.
        """
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.messages_queue = asyncio.Queue()
        self.running = False
        logger.info(f"PubSubClient initialized with project_id: {project_id}")

    async def start(self) -> None:
        """Start PubSub processes."""
        self.running = True
        logger.info("PubSub processes started")
        await asyncio.gather(
            self._process_messages(),
        )

    async def stop(self) -> None:
        """Stop PubSub processes."""
        self.running = False
        logger.info("PubSub processes stopped")

    async def _process_messages(self):
        """Process incoming messages using the message callback function."""
        while True:
            if not self.running:
                break
            message = await self.messages_queue.get()

            data = json.loads(message.data.decode("utf-8"))
            job_id = data["job_id"]
            user_id = data["user_id"]
            action = data["action"]

            ack = False
            async with AsyncSessionLocal() as db:
                if action == 'job_artifacts':
                    logger.info(f"Received action: job_artifacts for job: {job_id}, user: {user_id}")
                    ack = await _handle_job_artifacts(db, job_id, user_id, data)
                    logger.info(f"Processed action: job_artifacts, ack: {int(ack)}, for job: {job_id}, user: {user_id}")
                else:
                    logger.warning(f"Received unexpected action: {action}")

            if ack:
                message.ack()

    async def listen_for_messages(self, subscription_name: str) -> None:
        """
        Listen for messages on a specified Pub/Sub subscription.

        Args:
            subscription_name (str): The Pub/Sub subscription.
        """
        logger.info(f"Listening for messages on subscription: {subscription_name}")
        subscription_path = self.subscriber.subscription_path(self.project_id, subscription_name)

        def callback_wrapper(message):
            asyncio.run(self.messages_queue.put(message))

        streaming_pull_future = self.subscriber.subscribe(subscription_path, callback=callback_wrapper)
        with self.subscriber:
            while self.running:
                try:
                    # Wait for messages to be received, with a timeout of 1 second
                    await asyncio.to_thread(streaming_pull_future.result, timeout=1)
                except TimeoutError:
                    # No messages were received during the last second, so re-loop
                    pass
                except Exception as e:
                    streaming_pull_future.cancel()
                    logger.error(f"Listening for messages failed: {str(e)}")
