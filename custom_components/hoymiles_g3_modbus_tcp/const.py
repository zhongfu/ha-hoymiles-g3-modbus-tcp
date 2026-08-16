"""Constants for the Hoymiles G3 Modbus TCP integration."""

DOMAIN = "hoymiles_g3_modbus_tcp"
NAME = "Hoymiles G3 Modbus TCP"
MANUFACTURER = "Hoymiles"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT = "unit"
CONF_POLL_INTERVAL = "poll_interval"
CONF_FULL_POLL_INTERVAL = "full_poll_interval"
DEFAULT_PORT = 502
DEFAULT_UNIT = 1
DEFAULT_POLL_INTERVAL = 10
DEFAULT_FULL_POLL_INTERVAL = 60
UNAVAILABLE_AFTER_FAILURES = 2  # consecutive failed polls of a tier before its entities go unavailable
