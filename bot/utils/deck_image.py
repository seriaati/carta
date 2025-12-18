import asyncio
import io
import logging
from collections.abc import Sequence

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.models.card import Card
from app.models.deck_card import DeckCard

logger = logging.getLogger(__name__)

# Card display configuration
CARD_WIDTH = 200
CARD_HEIGHT = 280
SPACING = 20
BACKGROUND_COLOR = (30, 30, 40)


def _generate_deck_image_sync(deck_data: Sequence[tuple[DeckCard, Card]]) -> bytes:  # noqa: PLR0914
    """
    Synchronous function to generate deck image.
    Creates a 3x2 grid layout with cards resized to maintain aspect ratio.
    """
    # Calculate canvas size
    canvas_width = (CARD_WIDTH * 3) + (SPACING * 4)
    canvas_height = (CARD_HEIGHT * 2) + (SPACING * 3)

    # Create canvas
    canvas = Image.new("RGB", (canvas_width, canvas_height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Try to load a font for empty slot markers, fallback to default if not available
    try:
        empty_font = ImageFont.truetype("arial.ttf", 48)
    except OSError:
        empty_font = ImageFont.load_default()

    # Track which positions are filled
    filled_positions = set()

    # Download and place cards
    for deck_card, card in deck_data:
        try:
            # Download card image
            response = httpx.get(card.image_url, timeout=10.0)
            response.raise_for_status()
            card_image = Image.open(io.BytesIO(response.content))

            # Resize maintaining aspect ratio
            card_image.thumbnail((CARD_WIDTH, CARD_HEIGHT), Image.Resampling.LANCZOS)

            # Track this position as filled
            filled_positions.add(deck_card.position)

            # Calculate position based on deck_card.position (1-6)
            # Position is 1-based, convert to 0-based for calculations
            position_idx = deck_card.position - 1
            row = position_idx // 3
            col = position_idx % 3

            # Calculate card position with centering
            x_pos = SPACING + (col * (CARD_WIDTH + SPACING)) + (CARD_WIDTH - card_image.width) // 2
            y_pos = (
                SPACING + (row * (CARD_HEIGHT + SPACING)) + (CARD_HEIGHT - card_image.height) // 2
            )

            # Paste card onto canvas
            canvas.paste(card_image, (x_pos, y_pos))

        except Exception as e:
            logger.warning("Failed to load card image for card_id=%s: %s", card.id, e)
            continue

    # Draw empty slot markers for unfilled positions
    for position in range(1, 7):
        if position not in filled_positions:
            position_idx = position - 1
            row = position_idx // 3
            col = position_idx % 3

            # Calculate slot position
            x_pos = SPACING + (col * (CARD_WIDTH + SPACING))
            y_pos = SPACING + (row * (CARD_HEIGHT + SPACING))

            # Draw empty slot rectangle
            draw.rectangle(
                [x_pos, y_pos, x_pos + CARD_WIDTH, y_pos + CARD_HEIGHT],
                outline=(80, 80, 90),
                width=2,
            )

            # Draw position number in center
            position_text = str(position)
            bbox = draw.textbbox((0, 0), position_text, font=empty_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            text_x = x_pos + (CARD_WIDTH - text_width) // 2
            text_y = y_pos + (CARD_HEIGHT - text_height) // 2

            draw.text((text_x, text_y), position_text, fill=(100, 100, 110), font=empty_font)

    # Convert to bytes
    output = io.BytesIO()
    canvas.save(output, format="PNG")
    return output.getvalue()


async def generate_deck_image(deck_data: Sequence[tuple[DeckCard, Card]]) -> bytes:
    """
    Generate a deck image with cards arranged in a 3x2 grid.
    Cards are resized to maintain aspect ratio.

    Args:
        deck_data: List of (DeckCard, Card) tuples (maximum 6 cards)

    Returns:
        PNG image as bytes
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _generate_deck_image_sync, deck_data)


def _generate_trade_image_sync(card_left: Card, card_right: Card, icon_path: str) -> bytes:
    """
    Synchronous function to generate trade request image.
    Shows two cards side-by-side with a trade icon in between.
    """
    # Icon configuration
    icon_size = 100
    icon_padding = 20  # Space between cards and icon

    # Calculate canvas size
    canvas_width = (
        SPACING + CARD_WIDTH + icon_padding + icon_size + icon_padding + CARD_WIDTH + SPACING
    )
    canvas_height = SPACING + CARD_HEIGHT + SPACING

    # Create canvas
    canvas = Image.new("RGB", (canvas_width, canvas_height), BACKGROUND_COLOR)

    # Load and place left card
    try:
        response = httpx.get(card_left.image_url, timeout=10.0)
        response.raise_for_status()
        left_image = Image.open(io.BytesIO(response.content))
        left_image.thumbnail((CARD_WIDTH, CARD_HEIGHT), Image.Resampling.LANCZOS)

        x_pos = SPACING + (CARD_WIDTH - left_image.width) // 2
        y_pos = SPACING + (CARD_HEIGHT - left_image.height) // 2
        canvas.paste(left_image, (x_pos, y_pos))
    except Exception as e:
        logger.warning("Failed to load left card image for card_id=%s: %s", card_left.id, e)

    # Load and place right card
    try:
        response = httpx.get(card_right.image_url, timeout=10.0)
        response.raise_for_status()
        right_image = Image.open(io.BytesIO(response.content))
        right_image.thumbnail((CARD_WIDTH, CARD_HEIGHT), Image.Resampling.LANCZOS)

        x_pos = SPACING + CARD_WIDTH + icon_padding + icon_size + icon_padding
        x_pos += (CARD_WIDTH - right_image.width) // 2
        y_pos = SPACING + (CARD_HEIGHT - right_image.height) // 2
        canvas.paste(right_image, (x_pos, y_pos))
    except Exception as e:
        logger.warning("Failed to load right card image for card_id=%s: %s", card_right.id, e)

    # Load and place trade icon in center
    try:
        icon_image = Image.open(icon_path)
        icon_image = icon_image.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

        # Center icon horizontally and vertically
        icon_x = SPACING + CARD_WIDTH + icon_padding
        icon_y = SPACING + (CARD_HEIGHT - icon_size) // 2

        # Handle transparency if icon has alpha channel
        if icon_image.mode == "RGBA":
            canvas.paste(icon_image, (icon_x, icon_y), icon_image)
        else:
            canvas.paste(icon_image, (icon_x, icon_y))
    except Exception as e:
        logger.warning("Failed to load trade icon from %s: %s", icon_path, e)

    # Convert to bytes
    output = io.BytesIO()
    canvas.save(output, format="PNG")
    return output.getvalue()


async def generate_trade_image(card_left: Card, card_right: Card) -> bytes:
    """
    Generate a trade request image showing two cards with a trade icon between them.

    Args:
        card_left: Card to display on the left side
        card_right: Card to display on the right side
        icon_path: Path to the trade icon image file (should be 100x100px, supports transparency)

    Returns:
        PNG image as bytes
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _generate_trade_image_sync, card_left, card_right, "assets/trade.png"
    )
