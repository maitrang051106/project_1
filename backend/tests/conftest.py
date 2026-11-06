import asyncio
import threading


class _NoSocketSelector:
    """A socket-free selector using threading.Event for instant cross-thread wakeup.

    Windows Sandbox blocks loopback TCP sockets used by socket.socketpair() in
    WindowsProactorEventLoop / WindowsSelectorEventLoop. This selector allows
    asyncio.BaseEventLoop (and Starlette TestClient / anyio portals) to run
    entirely in-memory with zero socket system calls.
    """

    def __init__(self) -> None:
        self._wake_event = threading.Event()
        self._map: dict = {}

    def select(self, timeout: float | None = None) -> list:
        if timeout is None:
            self._wake_event.wait(0.05)
        elif timeout > 0:
            self._wake_event.wait(timeout)
        self._wake_event.clear()
        return []

    def wake(self) -> None:
        self._wake_event.set()

    def close(self) -> None:
        self._wake_event.set()

    def get_map(self) -> dict:
        return self._map


class _InMemoryEventLoop(asyncio.BaseEventLoop):
    """Standard asyncio.BaseEventLoop backed by _NoSocketSelector."""

    def __init__(self) -> None:
        super().__init__()
        self._selector = _NoSocketSelector()

    def _make_self_pipe(self) -> None:
        pass

    def _close_self_pipe(self) -> None:
        pass

    def _write_to_self(self) -> None:
        self._selector.wake()

    def _process_events(self, event_list: list) -> None:
        pass


class _InMemoryEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self) -> asyncio.AbstractEventLoop:
        return _InMemoryEventLoop()


asyncio.set_event_loop_policy(_InMemoryEventLoopPolicy())
