import datetime
import os
from uuid import UUID

from fastapi import UploadFile
from app.config_manager import config
from gcloud.aio.storage import Storage
from aiohttp import ClientSession, ClientResponseError
from app.utils import setup_logger
from app.core.exceptions import ServerError

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

# The bucket name to use for file storage
GCS_BUCKET = config.gcs_bucket


def handle_gcs_error(e: ClientResponseError, file_path: str) -> None:
    """
    Handle Google Cloud Storage errors.

    Args:
        e (ClientResponseError): The error response.
        file_path (str): The path of the file that caused the error.
    Raises:
        ServerError: If it's an authentication error.
        ClientResponseError: For all other errors.
    """
    if e.status == 404:
        # Don't raise an error if the file is not found, just log a warning, as the file is already deleted
        logger.warning(f"File not found in Google Cloud Storage: {file_path}")
    elif e.status == 400 and "invalid_grant" in e.message:
        # If you see this error, you need to authenticate with Google Cloud SDK
        # Run 'gcloud auth application-default login' to authenticate or check the authentication credentials
        raise ServerError("Authentication error: Are you authenticated with Google Cloud SDK?", logger)
    else:
        # Re-raise the error for all other cases
        raise e


def prefix_filename_with_datetime(filename: str) -> str:
    """
    Prefix a filename with the current datetime in the format: YYYYMMDDHHMMSS_filename.

    Args:
        filename (str): The original filename.
    Returns:
        str: The new filename with the datetime prefix.
    """
    # Get the current datetime
    current_datetime = datetime.datetime.now()

    # Format the datetime as a string
    datetime_str = current_datetime.strftime("%Y%m%d%H%M%S")

    # Concatenate the datetime string with the filename
    new_filename = f"{datetime_str}_{filename}"

    return new_filename


async def upload_file(path: str, file: UploadFile, user_id: UUID) -> str:
    """
    Upload a file to Google Cloud Storage asynchronously using gcloud-aio-storage.

    Args:
        path (str): The path to store the file in storage.
        file (UploadFile): The file to upload.
        user_id (UUID): The ID of the user uploading the file to use in the file path.
    Returns:
        str: The name of the uploaded file.
    """
    # Create the file path
    file_name = prefix_filename_with_datetime(file.filename)
    file_path = os.path.join(path, str(user_id), file_name)

    # Read the file contents
    contents = await file.read()

    # Upload the file to storage
    async with ClientSession() as session:
        storage = Storage(session=session)
        try:
            await storage.upload(
                bucket=GCS_BUCKET,
                object_name=file_path,
                file_data=contents,
                content_type=file.content_type
            )
        except ClientResponseError as e:
            # Handle the error
            handle_gcs_error(e, file_path)

    # Log and return the file name
    logger.info(f"Successfully uploaded file: {file_path} for user: {user_id}")
    return file_name


async def delete_file(path: str, file_name: str, user_id: UUID) -> None:
    """
    Delete a file from Google Cloud Storage asynchronously.

    Args:
        path (str): The path where the file is stored in storage.
        file_name (str): The name of the file to delete.
        user_id (UUID): The user ID to use in the file path.

    Raises:
        StorageError: If there's an error deleting the file from Google Cloud Storage.
    """
    # Create the file path
    file_path = os.path.join(path, str(user_id), file_name)

    # Delete the file from storage
    async with ClientSession() as session:
        storage = Storage(session=session)
        try:
            await storage.delete(
                bucket=GCS_BUCKET,
                object_name=file_path
            )
        except ClientResponseError as e:
            # Handle the error
            handle_gcs_error(e, file_path)

    logger.info(f"Successfully deleted file: {file_path} for user: {user_id}")
