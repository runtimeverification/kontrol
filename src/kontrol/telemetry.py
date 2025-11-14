from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import requests
import tomli
import tomli_w

if TYPE_CHECKING:
    pass

import os
from rich.console import Console
from . import VERSION

console = Console()


KPROFILE_CONFIG_DIR = Path.home() / '.config' / '.kprofile'
KPROFILE_CONFIG_FILE = KPROFILE_CONFIG_DIR /'.config'/ 'config.toml'


def _get_user_id() -> str:
    """Get or create persistent anonymous user ID"""
    if not KPROFILE_CONFIG_FILE.exists():
        _prompt_telemetry_consent()

    with open(KPROFILE_CONFIG_FILE, 'rb') as f:
        config = tomli.load(f)

    return config['user']['user_id']


def _prompt_telemetry_consent() -> bool:
    """Prompt user for telemetry consent on first run"""
    console.print('\n' + '=' * 60)
    console.print('📊 Kontrol collects anonymous usage data to improve the tool.')
    console.print('📌 We only track: proof events, tool version, and errors.')
    console.print('🔒 No code, proof names, or personal data is collected.')
    console.print('=' * 60)

    response = input('Enable telemetry? [y/N]: ').strip().lower()
    consent = response == 'y'

    KPROFILE_CONFIG_DIR.mkdir(exist_ok=True)

    config = {'user': {'user_id': str(uuid.uuid4()), 'consent': consent}}

    with open(KPROFILE_CONFIG_FILE, 'wb') as f:
        tomli_w.dump(config, f)

    emoji = '✅' if consent else '❌'
    console.print(f'\n{emoji} Telemetry {"enabled" if consent else "disabled"}.')
    console.print(f'⚙️  Change anytime: edit {KPROFILE_CONFIG_FILE} or set KPROFILE_TELEMETRY_DISABLED=1\n')

    return consent

def _should_send_telemetry() -> bool:
    """Check if telemetry is enabled via consent"""
    if os.getenv('KPROFILE_TELEMETRY_DISABLED'):
        return False

    if not KPROFILE_CONFIG_FILE.exists():
        return _prompt_telemetry_consent()

    with open(KPROFILE_CONFIG_FILE, 'rb') as f:
        config = tomli.load(f)

    return config.get('user', {}).get('consent', False)


def _track_event(event: str, properties: dict | None = None) -> None:
    """Send telemetry event to proxy server"""
    if not _should_send_telemetry():
        return

    if properties:
        properties['version'] = VERSION
    else:
        properties = {'version': VERSION}

    print('sending event:', event, properties)
    # try:
    #     requests.post(
    #         'https://ojlk1fzi13.execute-api.us-east-1.amazonaws.com/dev/track',
    #         json={'user_id': _get_user_id(), 'event': event, 'properties': properties},
    #         timeout=2,
    #     )
    # except Exception:
    #     pass  # Fail silently
