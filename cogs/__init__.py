import logging

from appconfig import DEBUGGING

# Debugging
from .debugcog import DebugCog
from .emojistats.cog import EmojiTools

# Custom tricks and tools
from .cardboard.cog import DanbooruSearch
from .colours.cog import Colours
from .generalcog import General
from .interceptor.cog import Interceptor

# Game-specific
from .epicseven.cog import EpicSeven
from .kingsraid.cog import KrSearch

# Automated site tracking service
from .plugtracker.kingsraidcog import PlugKingsRaid
from .plugtracker.browndustcog import PlugBrownDust
from .publishsubscribecog import PublishSubscribe
from .stovetracker.epicsevencog import StoveEpicSeven
from .tracking.twitchcog import TwitchMogra
from .sgxtracker.sgxresearchcog import SgxResearch
from .mhybbstracker.mhybbscog import MhyBbs



log = logging.getLogger(__name__)


ENABLED_COGS = [
    DebugCog,

    DanbooruSearch,
    Colours,
    EmojiTools,
    General,
    Interceptor,

    EpicSeven,
    KrSearch,

    PlugKingsRaid,
    PlugBrownDust,
    PublishSubscribe,
    StoveEpicSeven,
    TwitchMogra,
    SgxResearch,
    MhyBbs,
]
