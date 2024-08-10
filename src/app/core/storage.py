import os
from fastapi import UploadFile
from app.config_manager import config
from typing import AsyncGenerator
from gcloud.aio.storage import Storage
from google.auth.exceptions import DefaultCredentialsError
import asyncio
from aiohttp import ClientSession

GCS_BUCKET = config.gcs_bucket_datasets


async def upload_file(file: UploadFile, path: str) -> str:
    """
    Upload a file to Google Cloud Storage asynchronously using gcloud-aio-storage.

    :param file: The file to upload
    :param path: The path to save the file to
    :return: The URL of the uploaded file
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

        return f"https://storage.googleapis.com/{GCS_BUCKET}/{file_path}"

    except Exception as e:
        print(f"Error uploading file to Google Cloud Storage: {e}")
        raise


async def delete_file(file_url: str) -> None:
    """
    Delete a file from Google Cloud Storage asynchronously.

    :param file_url: The URL of the file to delete
    """
    file_path = file_url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]

    try:
        async with ClientSession() as session:
            storage = Storage(session=session, credentials=credentials)

            await storage.delete(
                bucket=GCS_BUCKET,
                object_name=file_path
            )
    except Exception as e:
        print(f"Error deleting file from Google Cloud Storage: {e}")
        raise


async def get_file_stream(file_url: str) -> AsyncGenerator[bytes, None]:
    """
    Get a file stream from Google Cloud Storage asynchronously.

    :param file_url: The URL of the file to stream
    :return: An async generator that yields file chunks
    """
    file_path = file_url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]

    try:
        async with ClientSession() as session:
            storage = Storage(session=session, credentials=credentials)

            async for chunk in storage.download(
                    bucket=GCS_BUCKET,
                    object_name=file_path,
                    chunk_size=8192  # 8KB chunks
            ):
                yield chunk
    except Exception as e:
        print(f"Error streaming file from Google Cloud Storage: {e}")
        raise


async def generate_signed_url(file_url: str, expiration: int = 3600) -> str:
    """
    Generate a signed URL for a file in Google Cloud Storage asynchronously.

    :param file_url: The URL of the file
    :param expiration: The expiration time of the signed URL in seconds (default is 1 hour)
    :return: The signed URL
    """
    file_path = file_url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]

    try:
        async with ClientSession() as session:
            storage = Storage(session=session, credentials=credentials)

            signed_url = await storage.get_signed_url(
                bucket=GCS_BUCKET,
                object_name=file_path,
                expiration=expiration
            )
            return signed_url
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        raise
