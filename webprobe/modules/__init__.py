from webprobe.modules.base import BaseModule
from webprobe.modules.headers import HeadersModule

MODULES: list[type[BaseModule]] = [
    HeadersModule,
]
