"""Vision client protocol."""

from typing import Protocol

from app.models import Detection


class VisionClient(Protocol):
    async def detect_objects(self, image_bytes: bytes) -> list[Detection]: ...
