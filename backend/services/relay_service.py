"""
FaceTrack - Access control relay trigger.

On a verified face match, this service signals the physical gate/turnstile
relay to unlock for a configured duration. ZKTeco access control panels
commonly expose either a simple HTTP relay endpoint or a raw TCP command
port; this implementation supports both, with HTTP preferred and TCP as
a fallback, so it can be adapted to whichever interface a given campus's
hardware exposes without changing the calling code in the pipeline.
"""
import logging
import socket
import threading
import time

import requests

from config import settings

logger = logging.getLogger("facetrack.relay")


class RelayService:
    def __init__(
        self,
        relay_http_url: str | None = None,
        relay_tcp_host: str | None = None,
        relay_tcp_port: int | None = None,
    ):
        # These can be overridden per-camera/per-gate if a campus has
        # multiple relay controllers; defaults come from environment/config.
        self.relay_http_url = relay_http_url
        self.relay_tcp_host = relay_tcp_host
        self.relay_tcp_port = relay_tcp_port

    def trigger_open(self, camera_id: str, duration_sec: int) -> bool:
        """Fire the relay open command asynchronously (in a background
        thread) so the recognition loop is never blocked waiting on
        network I/O to the access control panel."""
        thread = threading.Thread(
            target=self._trigger_sync,
            args=(camera_id, duration_sec),
            daemon=True,
        )
        thread.start()
        return True

    def _trigger_sync(self, camera_id: str, duration_sec: int) -> bool:
        for attempt in range(1, settings.RELAY_MAX_RETRIES + 2):
            try:
                if self._try_http(camera_id, duration_sec):
                    return True
                if self._try_tcp(duration_sec):
                    return True
            except Exception:
                logger.exception(
                    "Relay trigger attempt %d failed for camera %s", attempt, camera_id
                )
            time.sleep(0.25 * attempt)

        logger.error("All relay trigger attempts failed for camera %s", camera_id)
        return False

    def _try_http(self, camera_id: str, duration_sec: int) -> bool:
        url = self.relay_http_url
        if not url:
            return False
        response = requests.post(
            url,
            json={"camera_id": camera_id, "action": "open", "duration": duration_sec},
            timeout=settings.RELAY_HTTP_TIMEOUT_SEC,
        )
        response.raise_for_status()
        logger.info("Relay opened via HTTP for camera %s (%ss)", camera_id, duration_sec)
        return True

    def _try_tcp(self, duration_sec: int) -> bool:
        if not self.relay_tcp_host or not self.relay_tcp_port:
            return False
        command = f"OPEN {duration_sec}\n".encode("ascii")
        with socket.create_connection(
            (self.relay_tcp_host, self.relay_tcp_port), timeout=settings.RELAY_HTTP_TIMEOUT_SEC
        ) as sock:
            sock.sendall(command)
        logger.info("Relay opened via TCP (%ss)", duration_sec)
        return True
