# Module discovery for v2 Engine. Each per-module side-effect import below
# fires that module's `@register` decorator, populating `MODULE_REGISTRY`
# (consumed by Engine Phase 1 enumeration).
#
# Item 23 retired the v1 `MODULES` manifest; v2 modules use the registry.
from webprobe.modules import headers  # noqa: F401
from webprobe.modules import info_disclosure  # noqa: F401
from webprobe.modules import paths  # noqa: F401
from webprobe.modules import sqli  # noqa: F401
from webprobe.modules import traversal  # noqa: F401
from webprobe.modules import xss  # noqa: F401

from webprobe.modules import access_control  # noqa: F401
from webprobe.modules import brute_force  # noqa: F401
from webprobe.modules import csrf  # noqa: F401
from webprobe.modules import error_leakage  # noqa: F401
from webprobe.modules import idor  # noqa: F401
from webprobe.modules import session  # noqa: F401
