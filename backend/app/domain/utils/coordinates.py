"""Coordinate translation utility functions.

Provides robust mappings between absolute world-space coordinates,
chunk-space coordinates, and chunk-local space coordinates.
"""

from app.core.config import settings


def world_to_chunk(x: int, y: int) -> tuple[int, int]:
    """Translates absolute world coordinates to parent chunk coordinates.

    Args:
        x: Absolute world X coordinate.
        y: Absolute world Y coordinate.

    Returns:
        A tuple of (chunk_x, chunk_y).
    """
    return x // settings.CHUNK_SIZE, y // settings.CHUNK_SIZE


def chunk_to_world(chunk_x: int, chunk_y: int) -> tuple[int, int]:
    """Translates chunk coordinates to top-left absolute world coordinates.

    Args:
        chunk_x: Chunk X coordinate.
        chunk_y: Chunk Y coordinate.

    Returns:
        A tuple of (absolute_x, absolute_y) representing the top-left tile.
    """
    return chunk_x * settings.CHUNK_SIZE, chunk_y * settings.CHUNK_SIZE


def world_to_local(x: int, y: int) -> tuple[int, int]:
    """Translates absolute world coordinates to local chunk-relative coordinates.

    Args:
        x: Absolute world X coordinate.
        y: Absolute world Y coordinate.

    Returns:
        A tuple of (local_x, local_y).
    """
    return x % settings.CHUNK_SIZE, y % settings.CHUNK_SIZE


def local_to_world(
    chunk_x: int, chunk_y: int, local_x: int, local_y: int
) -> tuple[int, int]:
    """Translates local chunk-relative coordinates back to absolute world coordinates.

    Args:
        chunk_x: Parent chunk X coordinate.
        chunk_y: Parent chunk Y coordinate.
        local_x: Local relative X coordinate.
        local_y: Local relative Y coordinate.

    Returns:
        A tuple of (absolute_x, absolute_y).
    """
    return (
        chunk_x * settings.CHUNK_SIZE + local_x,
        chunk_y * settings.CHUNK_SIZE + local_y,
    )
