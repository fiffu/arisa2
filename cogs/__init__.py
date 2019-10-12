import logging

from appconfig import DEBUGGING

from .debugcog import DebugCog
from .generalcog import General

from .cardboard.cog import DanbooruSearch
from .colours.cog import Colours
from .epicseven.cog import EpicSeven
from .kingsraid.cog import KrSearch

from .publishsubscribecog import PublishSubscribe
from .plugtracker.kingsraidcog import PlugKingsRaid
from .plugtracker.browndustcog import PlugBrownDust
from .stovetracker.epicsevencog import StoveEpicSeven
from .tracking.twitchcog import TwitchMogra


log = logging.getLogger(__name__)

ENABLED_COGS = [
    DebugCog,
    General,
    Colours,
    KrSearch,
    EpicSeven,
    DanbooruSearch,
    PublishSubscribe,
    PlugKingsRaid,
    PlugBrownDust,
    StoveEpicSeven,
    TwitchMogra,
]
