from webprobe.modules.base import BaseModule
from webprobe.modules.headers import HeadersModule
from webprobe.modules.info_disclosure import InfoDisclosureModule
from webprobe.modules.paths import PathsModule
from webprobe.modules.sqli import SqliModule
from webprobe.modules.traversal import TraversalModule
from webprobe.modules.xss import XssModule

MODULES: list[type[BaseModule]] = [
    HeadersModule,
    InfoDisclosureModule,
    PathsModule,
    SqliModule,
    XssModule,
    TraversalModule,
]
