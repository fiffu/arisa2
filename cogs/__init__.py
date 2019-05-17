import logging

from .on_ready_cog import OnReadyCog


log = logging.getLogger(__name__)

ENABLED_COGS = [
    OnReadyCog,
]
