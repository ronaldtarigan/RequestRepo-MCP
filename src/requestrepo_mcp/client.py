"""requestrepo client lifecycle management."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from requestrepo import Requestrepo

from .config import RequestrepoConfig


class RequestrepoClientManager:
    """Lazy singleton for the requestrepo client."""

    def __init__(
        self,
        config: RequestrepoConfig,
        client_factory: Callable[..., Requestrepo] = Requestrepo,
    ) -> None:
        self._config = config
        self._client_factory = client_factory
        self._client: Requestrepo | None = None
        self._lock = threading.Lock()

    def get_client(self) -> Requestrepo:
        """Get the singleton requestrepo client."""
        with self._lock:
            if self._client is None:
                kwargs: dict[str, Any] = {
                    "host": self._config.host,
                    "port": self._config.port,
                    "protocol": self._config.protocol,
                    "verify": self._config.verify,
                }
                if self._config.token:
                    kwargs["token"] = self._config.token
                elif self._config.admin_token:
                    kwargs["admin_token"] = self._config.admin_token

                self._client = self._client_factory(**kwargs)
            return self._client
