import logging

from appconfig import DEBUGGING

from .debugcog import DebugCog
from .generalcog import General
from .emojistats.cog import EmojiTools

from .colours.cog import Colours
from .kingsraid.cog import KrSearch
from .cardboard.cog import DanbooruSearch

from .publishsubscribecog import PublishSubscribe
from .plugtracker.kingsraidcog import PlugKingsRaid
from .plugtracker.browndustcog import PlugBrownDust


log = logging.getLogger(__name__)

ENABLED_COGS = [
    DebugCog,
    General,
    Colours,
    EmojiTools,
    KrSearch,
    DanbooruSearch,
    PublishSubscribe,
    PlugKingsRaid,
    PlugBrownDust,
]
