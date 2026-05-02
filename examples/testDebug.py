import ftemplatemodules.auto  # noqa: F401 # pylint: disable=unused-import
from ftemplatemodules import set_debug_hook
from structlog import processors, configure, get_logger, WriteLoggerFactory
from pathlib import Path

set_debug_hook(lambda: None)  # Enable debugging during imports

from test import main  # noqa E402 - must be after debug is enabled

configure(
    processors=[
        processors.TimeStamper(fmt='iso'),
        processors.add_log_level,
        processors.JSONRenderer(),
    ],
    logger_factory=WriteLoggerFactory(
        file=Path("templateUseLog")
        .with_suffix(".log")
        .open("at", encoding="utf-8")
    ),
)

TEMPLATE_LOG = get_logger()


@set_debug_hook
def _(name: str, s: str, **kargs):
    TEMPLATE_LOG.info("template", fStringResult=s, name=name, kargs=kargs)


main()
