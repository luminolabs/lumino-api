import datetime
import os
from uuid import UUID

from aiohttp import ClientSession, ClientResponseError
from fastapi import UploadFile
from gcloud.aio.storage import Storage

from app.core.config_manager import config
from app.core.exceptions import ServerError, StorageError
from app.core.utils import setup_logger

logger = setup_logger(__name__)

GCS_BUCKET = config.gcs_bucket


def handle_gcs_error(e: ClientResponseError, file_path: str) -> None:
    """Handle Google Cloud Storage errors."""
    if e.status == 404:
        logger.warning(f"File not found in GCS: {file_path}")
    elif e.status == 400 and "invalid_grant" in e.message:
        raise ServerError(
            "Authentication error: Are you authenticated with Google Cloud SDK?",
            logger
        )
    else:
        raise StorageError(f"GCS operation failed: {str(e)}", logger)


async def upload_file(path: str, file: UploadFile, user_id: UUID) -> str:
    """
    Upload file to Google Cloud Storage.

    Args:
        path: Storage path
        file: File to upload
        user_id: User ID for file path

    Returns:
        Uploaded file name

    Raises:
        StorageError: If upload fails
    """
    # Create file path with timestamp prefix
    current_datetime = datetime.datetime.now()
    datetime_str = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"{datetime_str}_{file.filename}"
    file_path = os.path.join(path, str(user_id), file_name)

    try:
        # Read file contents
        contents = await file.read()

        # Upload to GCS
        async with ClientSession() as session:
            storage = Storage(session=session)
            await storage.upload(
                bucket=GCS_BUCKET,
                object_name=file_path,
                file_data=contents,
                content_type=file.content_type
            )

        logger.info(f"Uploaded file: {file_path} for user: {user_id}")
        return file_name

    except ClientResponseError as e:
        handle_gcs_error(e, file_path)
        return file_name  # Only reached for 404 errors
    except Exception as e:
        raise StorageError(f"Failed to upload file: {str(e)}", logger)


async def delete_file(path: str, file_name: str, user_id: UUID) -> None:
    """
    Delete file from Google Cloud Storage.

    Args:
        path: Storage path
        file_name: File name to delete
        user_id: User ID for file path

    Raises:
        StorageError: If deletion fails
    """
    file_path = os.path.join(path, str(user_id), file_name)

    try:
        async with ClientSession() as session:
            storage = Storage(session=session)
            await storage.delete(
                bucket=GCS_BUCKET,
                object_name=file_path
            )

        logger.info(f"Deleted file: {file_path} for user: {user_id}")

    except ClientResponseError as e:
        handle_gcs_error(e, file_path)
    except Exception as e:
        raise StorageError(f"Failed to delete file: {str(e)}", logger)
