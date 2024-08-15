import os
from fastapi import UploadFile
from app.config_manager import config
from typing import AsyncGenerator
from gcloud.aio.storage import Storage
from aiohttp import ClientSession, ClientResponseError
from app.utils import setup_logger
from app.core.exceptions import StorageError

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

GCS_BUCKET = config.gcs_bucket_datasets


async def upload_file(file: UploadFile, path: str) -> str:
    """
    Upload a file to Google Cloud Storage asynchronously using gcloud-aio-storage.

    Args:
        file (UploadFile): The file to upload.
        path (str): The path to save the file to.

    Returns:
        str: The URL of the uploaded file.

    Raises:
        StorageError: If there's an error uploading the file to Google Cloud Storage.
    """
    file_path = os.path.join(path, file.filename)

    try:
        contents = await file.read()

        async with ClientSession() as session:
            storage = Storage(session=session)

            await storage.upload(
                bucket=GCS_BUCKET,
                object_name=file_path,
                file_data=contents,
                content_type=file.content_type
            )

        logger.info(f"Successfully uploaded file: {file_path}")
        return f"https://storage.googleapis.com/{GCS_BUCKET}/{file_path}"
    except Exception as e:
        logger.error(f"Error uploading file to Google Cloud Storage: {e}")
        logger.error("Are you authenticated with Google Cloud SDK? Run 'gcloud auth application-default login'")
        raise StorageError(f"Failed to upload file: {e.detail}")


async def delete_file(file_url: str) -> None:
    """
    Delete a file from Google Cloud Storage asynchronously.

    Args:
        file_url (str): The URL of the file to delete.

    Raises:
        StorageError: If there's an error deleting the file from Google Cloud Storage.
    """
    file_path = file_url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]

    try:
        async with ClientSession() as session:
            storage = Storage(session=session)

            await storage.delete(
                bucket=GCS_BUCKET,
                object_name=file_path
            )
        logger.info(f"Successfully deleted file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file from Google Cloud Storage: {e}")
        raise StorageError(f"Failed to delete file: {e.detail}")


async def generate_signed_url(file_url: str, expiration: int = 3600) -> str:
    """
    Generate a signed URL for a file in Google Cloud Storage asynchronously.

    Args:
        file_url (str): The URL of the file.
        expiration (int): The expiration time of the signed URL in seconds (default is 1 hour).

    Returns:
        str: The signed URL.

    Raises:
        StorageError: If there's an error generating the signed URL.
    """
    file_path = file_url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]

    try:
        async with ClientSession() as session:
            storage = Storage(session=session)

            signed_url = await storage.get_signed_url(
                bucket=GCS_BUCKET,
                object_name=file_path,
                expiration=expiration
            )
        logger.info(f"Successfully generated signed URL for file: {file_path}")
        return signed_url
    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        raise StorageError(f"Failed to generate signed URL: {e.detail}")