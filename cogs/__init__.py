import logging

from .on_ready_cog import OnReadyCog
from .kingsraid.cog import KrSearchCog
from .plugtracker.kingsraidcog import PlugKingsRaidCog

log = logging.getLogger(__name__)

ENABLED_COGS = [
    OnReadyCog,
    KrSearchCog,
    PlugKingsRaidCog
]
