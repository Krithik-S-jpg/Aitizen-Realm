"""FastAPI router for Simulation control and real-time observation.

Provides REST endpoints and WebSockets for monitoring and driving the simulation.
"""

import asyncio
import logging
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.application.services.engine_service import EngineService
from app.domain.interfaces.event_bus import IEventBus
from app.domain.models.engine import Event
from app.infrastructure.api.dependencies import get_engine_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections for streaming real-time events."""

    def __init__(self) -> None:
        """Initializes the connection pool."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts a WebSocket connection and registers it.

        Args:
            websocket: The FastAPI WebSocket connection.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "New WebSocket connection registered. Total: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Deregisters a disconnected WebSocket connection.

        Args:
            websocket: The FastAPI WebSocket connection.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                "WebSocket connection removed. Total: %d",
                len(self.active_connections),
            )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Sends a JSON message to all active WebSocket connections.

        Args:
            message: The dictionary data to send.
        """
        if not self.active_connections:
            return

        logger.debug("Broadcasting message to %d clients", len(self.active_connections))

        async def _safe_send(conn: WebSocket) -> WebSocket | None:
            try:
                await conn.send_json(message)
                return None
            except Exception as e:
                logger.error("Failed to send message to WebSocket client: %s", e)
                return conn

        results = await asyncio.gather(
            *[_safe_send(connection) for connection in self.active_connections]
        )
        disconnected = [conn for conn in results if conn is not None]
        for connection in disconnected:
            self.disconnect(connection)


# Global connection manager
manager = ConnectionManager()


async def register_event_broadcaster(event_bus: IEventBus) -> None:
    """Subscribes an event broadcaster callback to all major simulation events.

    Args:
        event_bus: The Event Bus instance.
    """
    events = [
        "simulation:started",
        "simulation:paused",
        "simulation:resumed",
        "simulation:stopped",
        "tick:started",
        "tick:completed",
    ]

    async def _broadcast_event(event: Event) -> None:
        message = {
            "type": "event",
            "name": event.name,
            "tick": event.tick,
            "timestamp": event.timestamp,
            "payload": event.payload,
        }
        await manager.broadcast(message)

    for event_name in events:
        event_bus.subscribe(event_name, _broadcast_event)
        logger.info("Subscribed WebSocket broadcaster to event: %s", event_name)


@router.get("/state", response_model=dict[str, Any])
def get_state(
    engine_service: EngineService = Depends(get_engine_service),
) -> dict[str, Any]:
    """Gets the current status and tick state of the simulation.

    Args:
        engine_service: The EngineService dependency.

    Returns:
        JSON object containing state and tick.
    """
    tick = engine_service.get_current_tick()
    return {
        "state": engine_service.get_simulation_state(),
        "tick_rate": engine_service.get_tick_rate(),
        "current_tick": tick.value,
        "tick_timestamp": tick.timestamp,
    }


@router.post("/start", response_model=dict[str, Any])
async def start_simulation(
    engine_service: EngineService = Depends(get_engine_service),
) -> dict[str, Any]:
    """Starts the simulation engine run loop.

    Args:
        engine_service: The EngineService dependency.

    Returns:
        JSON object containing current state.
    """
    await engine_service.start_simulation()
    return {
        "message": "Simulation started",
        "state": engine_service.get_simulation_state(),
    }


@router.post("/pause", response_model=dict[str, Any])
async def pause_simulation(
    engine_service: EngineService = Depends(get_engine_service),
) -> dict[str, Any]:
    """Pauses the running simulation engine.

    Args:
        engine_service: The EngineService dependency.

    Returns:
        JSON object containing current state.
    """
    await engine_service.pause_simulation()
    return {
        "message": "Simulation paused",
        "state": engine_service.get_simulation_state(),
    }


@router.post("/resume", response_model=dict[str, Any])
async def resume_simulation(
    engine_service: EngineService = Depends(get_engine_service),
) -> dict[str, Any]:
    """Resumes a paused simulation engine.

    Args:
        engine_service: The EngineService dependency.

    Returns:
        JSON object containing current state.
    """
    await engine_service.resume_simulation()
    return {
        "message": "Simulation resumed",
        "state": engine_service.get_simulation_state(),
    }


@router.post("/step", response_model=dict[str, Any])
async def step_simulation(
    engine_service: EngineService = Depends(get_engine_service),
) -> dict[str, Any]:
    """Executes a single simulation tick.

    Args:
        engine_service: The EngineService dependency.

    Returns:
        JSON object containing completed tick details.
    """
    try:
        tick = await engine_service.step_simulation()
        return {
            "message": "Step executed successfully",
            "tick": tick.value,
            "timestamp": tick.timestamp,
        }
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/stop", response_model=dict[str, Any])
async def stop_simulation(
    engine_service: EngineService = Depends(get_engine_service),
) -> dict[str, Any]:
    """Stops the simulation engine and resets the tick count.

    Args:
        engine_service: The EngineService dependency.

    Returns:
        JSON object containing current state.
    """
    await engine_service.stop_simulation()
    return {
        "message": "Simulation stopped",
        "state": engine_service.get_simulation_state(),
    }


@router.post("/rate", response_model=dict[str, Any])
def set_tick_rate(
    ticks_per_second: float = Query(
        ...,
        gt=0.0,
        description="Number of simulation ticks per second",
    ),
    engine_service: EngineService = Depends(get_engine_service),
) -> dict[str, Any]:
    """Updates the execution rate of the simulation.

    Args:
        ticks_per_second: Desired speed in ticks per second.
        engine_service: The EngineService dependency.

    Returns:
        JSON object with the new speed.
    """
    try:
        engine_service.set_tick_rate(ticks_per_second)
        return {
            "message": f"Tick rate updated to {ticks_per_second} ticks per second",
            "tick_rate": engine_service.get_tick_rate(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    engine_service: EngineService = Depends(get_engine_service),
) -> None:
    """WebSocket endpoint for real-time monitoring of simulation events.

    Args:
        websocket: The WebSocket connection object.
        engine_service: The EngineService dependency.
    """
    await manager.connect(websocket)

    try:
        tick = engine_service.get_current_tick()
        await websocket.send_json(
            {
                "type": "init",
                "state": engine_service.get_simulation_state(),
                "tick_rate": engine_service.get_tick_rate(),
                "current_tick": tick.value,
                "tick_timestamp": tick.timestamp,
            }
        )

        while True:
            # We must read incoming frames to keep socket alive and capture client exits
            data = await websocket.receive_text()
            logger.debug("Received message from WebSocket client: %s", data)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error("Error in WebSocket loop: %s", e)
    finally:
        manager.disconnect(websocket)
