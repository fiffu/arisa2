import logging

from .on_ready_cog import OnReadyCog
from .kingsraid.cog import KrSearchCog


log = logging.getLogger(__name__)

ENABLED_COGS = [
    OnReadyCog,
    KrSearchCog
]
