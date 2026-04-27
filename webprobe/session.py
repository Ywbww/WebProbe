import threading
import requests
from typing import Callable

_local = threading.local()


def make_session_factory(args) -> Callable[[], requests.Session]:
    def factory() -> requests.Session:
        s = getattr(_local, "session", None)
        if s is None:
            s = requests.Session()
            # Future: --cookie flag (Sprint 2) will set s.cookies here
            _local.session = s
        return s
    return factory
