import os
from fastapi import UploadFile
from app.config_manager import config
from typing import AsyncGenerator
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from google.auth.exceptions import DefaultCredentialsError
import asyncio

# Initialize Google Cloud Storage client
try:
    storage_client = storage.Client()
except DefaultCredentialsError:
    print("Error initializing Google Cloud Storage client. Make sure GOOGLE_APPLICATION_CREDENTIALS is set.")
    raise

GCS_BUCKET = config.gcs_bucket
bucket = storage_client.bucket(GCS_BUCKET)


async def upload_file(file: UploadFile, path: str) -> str:
    """
    Upload a file to Google Cloud Storage.

    :param file: The file to upload
    :param path: The path to save the file to
    :return: The URL of the uploaded file
    """
    file_path = os.path.join(path, file.filename)
    blob = bucket.blob(file_path)

    try:
        contents = await file.read()
        await asyncio.to_thread(blob.upload_from_string, contents, content_type=file.content_type)
        return f"https://storage.googleapis.com/{GCS_BUCKET}/{file_path}"
    except GoogleCloudError as e:
        print(f"Error uploading file to Google Cloud Storage: {e}")
        raise


async def delete_file(file_url: str) -> None:
    """
    Delete a file from Google Cloud Storage.

    :param file_url: The URL of the file to delete
    """
    file_path = file_url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]
    blob = bucket.blob(file_path)

    try:
        await asyncio.to_thread(blob.delete)
    except GoogleCloudError as e:
        print(f"Error deleting file from Google Cloud Storage: {e}")
        raise


async def get_file_stream(file_url: str) -> AsyncGenerator[bytes, None]:
    """
    Get a file stream from Google Cloud Storage.

    :param file_url: The URL of the file to stream
    :return: An async generator that yields file chunks
    """
    file_path = file_url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]
    blob = bucket.blob(file_path)

    try:
        async def stream_generator():
            buffer = await asyncio.to_thread(blob.download_as_bytes)
            chunk_size = 8192
            for i in range(0, len(buffer), chunk_size):
                yield buffer[i:i+chunk_size]

        return stream_generator()
    except GoogleCloudError as e:
        print(f"Error streaming file from Google Cloud Storage: {e}")
        raise


async def generate_signed_url(file_url: str, expiration: int = 3600) -> str:
    """
    Generate a signed URL for a file in Google Cloud Storage.

    :param file_url: The URL of the file
    :param expiration: The expiration time of the signed URL in seconds (default is 1 hour)
    :return: The signed URL
    """
    file_path = file_url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]
    blob = bucket.blob(file_path)

    try:
        signed_url = await asyncio.to_thread(
            blob.generate_signed_url,
            expiration=expiration,
            method='GET'
        )
        return signed_url
    except GoogleCloudError as e:
        print(f"Error generating signed URL: {e}")
        raise
