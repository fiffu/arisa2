import logging

#from .debugcog import DebugCog
from .botreadycog import BotReadyCog
from .publishsubscribecog import PublishSubscribeCog
from .kingsraid.cog import KrSearchCog
from .plugtracker.kingsraidcog import PlugKingsRaidCog
from .plugtracker.browndustcog import PlugBrownDustCog

log = logging.getLogger(__name__)

ENABLED_COGS = [
    #DebugCog,
    BotReadyCog,
    PublishSubscribeCog,
    KrSearchCog,
    PlugKingsRaidCog,
    PlugBrownDustCog,
]
