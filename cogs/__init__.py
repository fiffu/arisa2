import logging

#from .debugcog import DebugCog
from .botreadycog import BotReady
from .generalcog import General

from .colours import Colours
from .kingsraid.cog import KrSearch
from .cardboard.cog import DanbooruSearch

from .publishsubscribecog import PublishSubscribe
from .plugtracker.kingsraidcog import PlugKingsRaid
from .plugtracker.browndustcog import PlugBrownDust


log = logging.getLogger(__name__)

ENABLED_COGS = [
    #DebugCog,
    BotReady,
    General,
    Colours,
    KrSearch,
    DanbooruSearch,
    PublishSubscribe,
    PlugKingsRaid,
    PlugBrownDust,
]
