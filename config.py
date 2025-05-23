import os
from dotenv import load_dotenv, dotenv_values

BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))

def env(key, default=None):
    return dotenv_values().get(key, default)

config = {
    # PNP Server specific configuration
    "pnp": {
        "host": env('PNP_HOST', 'http://10.0.0.1:5000'),
        "default_backoff_delay": {
            "hours": 0,
            "minutes": 5,
            "seconds": 0
        }
    },

    # Netbox specific configuration
    "netbox": {
        "url": env('NETBOX_URL', 'http://localhost:8000'),
        "api_token": env('NETBOX_API_TOKEN', ''),
        "default_site": env('NETBOX_DEFAULT_SITE', 'Provisioning Site'),
        "default_role": env('NETBOX_DEFAULT_ROLE', 'Access Switch'),
        "tag_devices": env('NETBOX_TAG_DEVICES', True),
        "default_device_tag": env('NETBOX_DEFAULT_DEVICE_TAG', 'pnp-device')
    },
}