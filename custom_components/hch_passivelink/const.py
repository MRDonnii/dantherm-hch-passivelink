"""Constants for HCH PassiveLink."""

DOMAIN = "hch_passivelink"
DEFAULT_PORT = 4196
DEFAULT_NAME = "Dantherm HCH PassiveLink"
CONF_CONNECTION_TYPE = "connection_type"
CONF_SERIAL_PORT = "serial_port"
CONNECTION_TCP = "tcp"
CONNECTION_SERIAL = "serial"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_FILTER_NOTIFY_ENABLED = "filter_notify_enabled"
CONF_FILTER_NOTIFY_DAYS = "filter_notify_days"
CONF_FILTER_NOTIFY_SERVICE = "filter_notify_service"
CONF_PREHEATER_SENSORS_ENABLED = "preheater_sensors_enabled"
CONF_PREHEATER_SENSOR_HOST = "preheater_sensor_host"
CONF_PREHEATER_SENSOR_PORT = "preheater_sensor_port"
CONF_PREHEATER_SWAP_SENSORS = "preheater_swap_sensors"
DEFAULT_PREHEATER_SENSOR_PORT = 4197
DEFAULT_FILTER_NOTIFY_DAYS = 30

# Raspberry Pi host diagnostics - reported by the same optional endpoint
# (gateway/onewire_temperature_server.py) independently of whether DS18B20
# preheater sensors are configured.
PI_DIAGNOSTIC_KEYS = (
    "pi_model",
    "pi_kernel_version",
    "pi_cpu_temperature",
    "pi_uptime_seconds",
    "pi_load_average_1m",
    "pi_memory_used_percent",
    "pi_disk_used_percent",
    "pi_core_voltage",
    "pi_undervoltage_now",
    "pi_undervoltage_occurred",
    "pi_frequency_capped_now",
    "pi_frequency_capped_occurred",
    "pi_throttled_now",
    "pi_throttled_occurred",
    "pi_soft_temp_limit_now",
    "pi_soft_temp_limit_occurred",
)
