from ftemplatemodules import set_debug_hook
from structlog import processors, configure, get_logger, WriteLoggerFactory
from pathlib import Path


set_debug_hook(lambda: None)  # Enable debuging during imports


from test import main  # noqa E402 - Must be after debug is enabled.

configure(processors=[
    processors.TimeStamper(fmt='iso'),
    processors.add_log_level,
    processors.JSONRenderer(),
], logger_factory=WriteLoggerFactory(
    file=Path("templateUseLog").with_suffix(".log").open("at")
),
)

TEMPLATE_LOG = get_logger()


@set_debug_hook
def _(name: str, str: str, **kargs):
    TEMPLATE_LOG.info("template", fStringResult=str, name=name, kargs=kargs)


main()
