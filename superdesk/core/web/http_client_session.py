from typing import ClassVar
import asyncio
import logging

import aiohttp


logger = logging.getLogger(__name__)


class AsyncHttpClientSessionMixin:
    """
    Mixin class for managing an asynchronous HTTP client session.

    The purpose of this class is to provide functionality for maintaining a shared
    instance of an asynchronous `aiohttp.ClientSession`. It handles lazy initialization,
    session creation, and cleanup when the event loop changes or the session is closed.
    This mixin ensures an efficient and reusable session management strategy for
    asynchronous HTTP requests in applications.

    :cvar http_timeout: Configures the timeout settings for the
        HTTP client session, including connection and socket read timeouts.
    :cvar http_verify_ssl: Determines whether to enable SSL certificate verification for HTTP requests.
    """

    _http_session: ClassVar[aiohttp.ClientSession | None] = None
    _connected_loop: ClassVar[asyncio.AbstractEventLoop | None] = None
    _http_lock: ClassVar[asyncio.Lock | None] = None
    http_timeout: ClassVar[aiohttp.ClientTimeout] = aiohttp.ClientTimeout(connect=5, sock_read=30)
    http_verify_ssl: ClassVar[bool] = True

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """
        Returns a lock unique to the class (subclass) to ensure concurrency safety.
        """

        if "_http_lock" not in cls.__dict__ or cls._http_lock is None:
            cls._http_lock = asyncio.Lock()
        return cls._http_lock

    @classmethod
    async def _get_http_session(cls) -> tuple[aiohttp.ClientSession, bool]:
        """
        Provides a method for retrieving or creating an asynchronous HTTP session associated with
        the current event loop.

        :return: A tuple containing the HTTP session instance and a flag indicating if a new session was created.
        """
        # Lazy initialization of session
        new_session_created = False
        current_loop = asyncio.get_running_loop()

        async with cls._get_lock():
            if cls._connected_loop != current_loop:
                # Event loop has changed, make sure to re-connect to the new one
                if cls._http_session and not cls._http_session.closed:
                    await cls._http_session.close()
                cls._http_session = None
                cls._connected_loop = current_loop

            if cls._http_session is None or cls._http_session.closed:
                cls._http_session = cls._create_http_session()
                new_session_created = True

            return cls._http_session, new_session_created

    @classmethod
    def _create_http_session(cls) -> aiohttp.ClientSession:
        """
        Creates and initializes an aiohttp ClientSession for HTTP requests.

        This method configures a TCP connector with SSL verification settings and a timeout
        specific to the application. It also integrates with the application's lifecycle
        to ensure that the session is closed after the serving phase ends.

        :return: An initialized aiohttp ClientSession instance.
        """

        from superdesk.core import get_current_app

        connector = aiohttp.TCPConnector(ssl=cls.http_verify_ssl)
        session = aiohttp.ClientSession(connector=connector, timeout=cls.http_timeout)
        app = get_current_app()

        @app.after_serving
        async def close_session():
            if session and not session.closed:
                try:
                    await session.close()
                except Exception:
                    logger.exception("Failed to close aiohttp ClientSession")

            cls._http_session = None

        return session

    async def http_session(self) -> aiohttp.ClientSession:
        """
        Provides an asynchronous HTTP session for making requests.

        The method fetches or creates an HTTP session, ensures any required
        initialization happens if a new session is created, and finally
        returns the session for use.

        :return: An instance of the active or newly created HTTP session.
        """

        session, new_session_created = await self._get_http_session()
        if new_session_created:
            await self.on_http_session_start(session)
        return session

    async def on_http_session_start(self, http_client: aiohttp.ClientSession):
        """
        Handles the initialization of an HTTP session. This is typically invoked when an HTTP
        client session starts to allow for any setup or customization that is required.

        :param http_client: The HTTP client session that has been started.
        """

        pass
