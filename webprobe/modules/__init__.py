from webprobe.modules.base import BaseModule
from webprobe.modules.headers import HeadersModule
from webprobe.modules.info_disclosure import InfoDisclosureModule

MODULES: list[type[BaseModule]] = [
    HeadersModule,
    InfoDisclosureModule,
]
