from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Final

import requests
import tomli
import tomli_w

from . import VERSION

_LOGGER: Final = logging.getLogger(__name__)

KPROFILE_CONFIG_DIR: Final = Path.home() / '.config' / 'kprofile'
KPROFILE_CONFIG_FILE: Final = KPROFILE_CONFIG_DIR / 'config.toml'
TELEMETRY_MESSAGE: Final = (
    f'Telemetry: sending anonymous usage data. You can opt out by setting KPROFILE_TELEMETRY_DISABLED=true or consent=false in {KPROFILE_CONFIG_FILE}'
)


def _get_user_id() -> str:
    """Get or create persistent anonymous user ID"""
    if not KPROFILE_CONFIG_FILE.exists():
        KPROFILE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        config = {'user': {'user_id': str(uuid.uuid4()), 'consent': True}}
        with open(KPROFILE_CONFIG_FILE, 'wb') as f:
            tomli_w.dump(config, f)
        return str(config['user']['user_id'])

    with open(KPROFILE_CONFIG_FILE, 'rb') as f:
        config = tomli.load(f)

    return str(config['user']['user_id'])


def _has_permission() -> bool:
    """Check if telemetry is enabled"""
    if os.getenv('KPROFILE_TELEMETRY_DISABLED', '').lower() == 'true':
        return False

    _get_user_id()

    with open(KPROFILE_CONFIG_FILE, 'rb') as f:
        config = tomli.load(f)

    return config.get('user', {}).get('consent', True)


def _emit_event(event: str, properties: dict | None = None) -> None:
    """Send telemetry event to proxy server"""
    if not _has_permission():
        return

    _LOGGER.info(TELEMETRY_MESSAGE)

    if properties:
        properties['version'] = VERSION
    else:
        properties = {'version': VERSION}

    try:
        requests.post(
            'https://ojlk1fzi13.execute-api.us-east-1.amazonaws.com/dev/track',
            json={'user_id': _get_user_id(), 'event': event, 'properties': properties},
            timeout=2,
        )
    except Exception:
        pass  # Fail silently
