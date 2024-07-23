import logging
import requests
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def get_json_from_url(url, headers: Optional[dict] = {}):
    connect_timeout = 1.0
    read_timeout = 10.0

    try:
        r = requests.get(url, timeout=(connect_timeout, read_timeout), headers=headers)
        return r.json()
    except Exception:
        logger.error("Cannot connect to url : %s", sys.exc_info()[0])
        raise
