from typing import Any

import httpx

from app.core.config import settings


async def upload_image_to_cdn(image_data: str) -> str:
    """Upload image to CDN and return the image URL.

    Args:
        image_data: Base64 data URI string (e.g., 'data:image/png;base64,...')

    Returns:
        str: The full URL of the uploaded image

    Raises:
        httpx.HTTPStatusError: If the upload fails
    """
    # Extract base64 data from data URI if present (format: 'data:image/png;base64,iVBORw0KG...')
    base64_data = image_data.split(",", 1)[1] if image_data.startswith("data:") else image_data

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://img.seria.moe/upload",
            headers={"Authorization": f"Bearer {settings.cdn_api_key}"},
            json={"source": base64_data},
            timeout=30.0,
        )
        response.raise_for_status()

        result: dict[str, Any] = response.json()
        return f"https://r2.img.seria.moe/{result['filename']}"


async def delete_image_from_cdn(image_url: str) -> None:
    """Delete image from CDN.

    Args:
        image_url: Full URL of the image to delete (e.g., 'https://cdn.example.com/filename.png')

    Raises:
        httpx.HTTPStatusError: If the deletion fails
    """
    # Extract filename from URL
    filename = image_url.rsplit("/", maxsplit=1)[-1]

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"https://img.seria.moe/{filename}",
            headers={"Authorization": f"Bearer {settings.cdn_api_key}"},
            timeout=30.0,
        )
        response.raise_for_status()
