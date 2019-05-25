import logging

#from .debugcog import DebugCog
from .botreadycog import BotReadyCog

from .colours import ColourCog
from .kingsraid.cog import KrSearchCog
from .cardboard.cog import DanbooruCog

from .publishsubscribecog import PublishSubscribeCog
from .plugtracker.kingsraidcog import PlugKingsRaidCog
from .plugtracker.browndustcog import PlugBrownDustCog


log = logging.getLogger(__name__)

ENABLED_COGS = [
    #DebugCog,
    BotReadyCog,
    ColourCog,
    KrSearchCog,
    DanbooruCog,
    PublishSubscribeCog,
    PlugKingsRaidCog,
    PlugBrownDustCog,
]
