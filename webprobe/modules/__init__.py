from webprobe.modules.base import BaseModule
from webprobe.modules.headers import HeadersModule
from webprobe.modules.info_disclosure import InfoDisclosureModule
from webprobe.modules.paths import PathsModule
from webprobe.modules.sqli import SqliModule
from webprobe.modules.traversal import TraversalModule
from webprobe.modules.xss import XssModule

# v2 modules: import for @register side effects (Phase 1 enumeration
# reads MODULE_REGISTRY). Each v2 module file decorates its class with
# @register at module level, so a side-effect import is sufficient.
from webprobe.modules import access_control  # noqa: F401
from webprobe.modules import brute_force  # noqa: F401
from webprobe.modules import csrf  # noqa: F401
from webprobe.modules import error_leakage  # noqa: F401
from webprobe.modules import idor  # noqa: F401
from webprobe.modules import session  # noqa: F401

MODULES: list[type[BaseModule]] = [
    HeadersModule,
    InfoDisclosureModule,
    PathsModule,
    SqliModule,
    XssModule,
    TraversalModule,
]
