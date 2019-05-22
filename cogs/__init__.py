import logging

#from .debugcog import DebugCog
from .onreadycog import BotReadyCog
from .publishsubscribecog import PublishSubscribeCog
from .kingsraid.cog import KrSearchCog
from .plugtracker.kingsraidcog import PlugKingsRaidCog

log = logging.getLogger(__name__)

ENABLED_COGS = [
    #DebugCog,
    BotReadyCog,
    PublishSubscribeCog,
    KrSearchCog,
    PlugKingsRaidCog,
]
