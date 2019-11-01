"""Support for Jaguar/Land Rover InControl services."""
import logging
import urllib.error
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import jlrpy
import voluptuous as vol
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_point_in_utc_time, track_time_interval
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)

DOMAIN = "jlrincontrol"
SIGNAL_VEHICLE_SEEN = "{}.vehicle_seen".format(DOMAIN)
DATA_KEY = DOMAIN
CONF_MUTABLE = "mutable"

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=1)

RESOURCES = {
    "FUEL_LEVEL_PERC": ("sensor", "fuel level perc", "mdi:fuel", "%"),
    "DISTANCE_TO_EMPTY_FUEL": ("sensor", "distance to empty fuel", "mdi:road", "km"),
    "EXT_KILOMETERS_TO_SERVICE": (
        "sensor",
        "ext kilometer to service",
        "mdi:garage",
        "km",
    ),
    "ODOMETER_METER": ("sensor", "odometer meter", "mdi:car", "m"),
    "ODOMETER_MILES": ("sensor", "odometer miles", "mdi:car", "mi"),
    "ODOMETER": ("sensor", "odometer", "mdi:car", "m"),
    "THEFT_ALARM_STATUS": ("sensor", "theft alarm status", "mdi:car-key", ""),
    "DOOR_IS_ALL_DOORS_LOCKED": (
        "binary_sensor",
        "door is all locked",
        "mdi:car-door-lock",
        "lock",
    ),
    "DOOR_FRONT_LEFT_POSITION": (
        "binary_sensor",
        "door front left position",
        "mdi:car-door",
        "",
    ),
    "DOOR_FRONT_RIGHT_POSITION": (
        "binary_sensor",
        "door front right position",
        "mdi:car-door",
        "",
    ),
    "DOOR_REAR_LEFT_POSITION": (
        "binary_sensor",
        "door rear left position",
        "mdi:car-door",
        "",
    ),
    "DOOR_REAR_RIGHT_POSITION": (
        "binary_sensor",
        "door rear right position",
        "mdi:car-door",
        "",
    ),
    "DOOR_ENGINE_HOOD_POSITION": (
        "binary_sensor",
        "doors engine hood position",
        "mdi:lock",
        "",
    ),
    "DOOR_BOOT_POSITION": ("binary_sensor", "door boot position", "mdi:lock", ""),
    "DOOR_FRONT_LEFT_LOCK_STATUS": (
        "binary_sensor",
        "door front left lock status",
        "mdi:car-door-lock",
        "",
    ),
    "DOOR_FRONT_RIGHT_LOCK_STATUS": (
        "binary_sensor",
        "door front right lock status",
        "mdi:car-door-lock",
        "",
    ),
    "DOOR_REAR_LEFT_LOCK_STATUS": (
        "binary_sensor",
        "door rear left lock status",
        "mdi:car-door-lock",
        "",
    ),
    "DOOR_REAR_RIGHT_LOCK_STATUS": (
        "binary_sensor",
        "door rear right lock status",
        "mdi:car-door-lock",
        "",
    ),
    "DOOR_ENGINE_HOOD_LOCK_STATUS": (
        "binary_sensor",
        "door engine hood lock status",
        "mdi:lock",
        "",
    ),
    "DOOR_BOOT_LOCK_STATUS": ("binary_sensor", "door boot Lock status", "mdi:lock", ""),
    "TYRE_PRESSURE_FRONT_LEFT": (
        "sensor",
        "tyre Pressure front left",
        "mdi:car-tire-alert",
        "bar",
    ),
    "TYRE_PRESSURE_FRONT_RIGHT": (
        "sensor",
        "tyre Pressure front right",
        "mdi:car-tire-alert",
        "bar",
    ),
    "TYRE_PRESSURE_REAR_LEFT": (
        "sensor",
        "tyre Pressure rear left",
        "mdi:car-tire-alert",
        "bar",
    ),
    "TYRE_PRESSURE_REAR_RIGHT": (
        "sensor",
        "tyre Pressure rear right",
        "mdi:car-tire-alert",
        "bar",
    ),
    "WASHER_FLUID_WARN": ("sensor", "washer fluid warn", "mdi:wiper-wash", ""),
    "BRAKE_FLUID_WARN": ("sensor", "brake fluid warn", "mdi:car-brake-alert", ""),
    "EXT_OIL_LEVEL_WARN": ("sensor", "ext oil level warn", "mdi:oil", ""),
    "ENG_COOLANT_LEVEL_WARN": ("sensor", "eng coolant level warn", "mdi:car-coolant-level", ""),

    "WINDOW_FRONT_LEFT_STATUS": ("sensor", "window front left status", "mdi:car-door", ""),
    "WINDOW_FRONT_RIGHT_STATUS": ("sensor", "window front right status", "mdi:car-door", ""),
    "WINDOW_REAR_LEFT_STATUS": ("sensor", "window rear left status", "mdi:car-door", ""),
    "WINDOW_REAR_RIGHT_STATUS": ("sensor", "window rear right status", "mdi:car-door", ""),
    
    "IS_SUNROOF_OPEN": ("binary_sensor","is sunroof open","mdi:car","",),
}

SIGNAL_STATE_UPDATED = "{}.updated".format(DOMAIN)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): vol.All(cv.time_period, vol.Clamp(min=MIN_UPDATE_INTERVAL)),
                vol.Required(CONF_NAME): vol.Schema({cv.slug: cv.string}),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Set up the jlrpy component."""

    username = config[DOMAIN][CONF_USERNAME]
    password = config[DOMAIN][CONF_PASSWORD]

    state = hass.data[DATA_KEY] = JLRData(hass, config)

    interval = config[DOMAIN][CONF_SCAN_INTERVAL]

    try:
        connection = jlrpy.Connection(username, password)
    except urllib.error.HTTPError:
        _LOGGER.error("Could not connect to JLR. Please check your credentials")
        return False

    vehicles = []
    for vehicle in connection.vehicles:
        vehicle.info = vehicle.get_status()
        vehicles.append(vehicle)

    def discover_vehicle(vehicle):
        state.entities[vehicle.vin] = []

        for attr, (component, *_) in RESOURCES.items():
            hass.helpers.discovery.load_platform(
                component, DOMAIN, (vehicle.vin, attr), config
            )

    def update_vehicle(vehicle):
        """Update information on vehicle."""
        _LOGGER.info("Pulling info from JLR")

        state.vehicles[vehicle.vin] = vehicle
        if vehicle.vin not in state.entities:
            discover_vehicle(vehicle)
        #
        # for entity in state.entities[vehicle.vin]:
        #     entity.schedule_update_ha_state()

    #
    #     dispatcher_send(hass, SIGNAL_VEHICLE_SEEN, vehicle)
    #
    # def update(now):
    #     """Update status from the online service."""
    #     try:
    #         for vehicle in vehicles:
    #             update_vehicle(vehicle)
    #         return True
    #     except urllib.error.HTTPError:
    #         _LOGGER.error("Could not update vehicle status")
    #         return False
    #     finally:
    #         track_point_in_utc_time(hass, update,
    #                                 utcnow() + interval)
    #
    # return update(utcnow())

    try:
        for vehicle in vehicles:
            update_vehicle(vehicle)
        # return True
    except urllib.error.HTTPError:
        _LOGGER.error("Could not update vehicle status")
        # return False

    state.update(now=None)

    track_time_interval(hass, state.update, interval)

    return True


class JLRData:
    """Hold component state."""

    def __init__(self, hass, config):
        """Initialize the component state."""
        self._hass = hass
        self.entities = {}
        self.vehicles = {}
        self.config = config[DOMAIN]
        self.names = self.config.get(CONF_NAME)

    def vehicle_name(self, vehicle):
        """Provide a friendly name for a vehicle."""
        if not vehicle:
            return None
        elif vehicle.vin and vehicle.vin.lower() in self.names:
            return self.names[vehicle.vin.lower()]

        if vehicle.vin:
            return vehicle.vin

        return ""

    def update(self, now, **kwargs):
        _LOGGER.info("Updating vehicle data")
        # for vehicle in self.vehicles:

        for vehicle in self.vehicles:
            self.vehicles[vehicle].get_status()
        dispatcher_send(self._hass, SIGNAL_STATE_UPDATED)


class JLREntity(Entity):
    """Base class for all JLR Vehicle entities."""

    def __init__(self, hass, vin, attribute):
        """Initialize the entity."""
        self._hass = hass
        self._vin = vin
        self._attribute = attribute
        self._data = self._hass.data[DATA_KEY]
        self._vehicle = self._hass.data[DATA_KEY].vehicles[self._vin]
        self._name = self._data.vehicle_name(self.vehicle)

    @staticmethod
    def get_vehicle_status(vehicle_status):
        """Converts a weird quasi-dict returned by jlrpy into a proper dict"""
        dict_only = {}
        for element in vehicle_status:
            if element.get("key"):
                dict_only[element.get("key")] = element.get("value")
        return dict_only

    def get_updated_info(self):
        return self.get_vehicle_status(self.vehicle.info.get("vehicleStatus"))

    def update(self):
        _LOGGER.info("UPDATING NOW")

    @property
    def vehicle(self):
        """Return vehicle."""
        return self._vehicle

    @property
    def _entity_name(self):
        return RESOURCES[self._attribute][1]

    @property
    def name(self):
        """Return full name of the entity."""
        if self._name:
            return "{} {}".format(self._name, self._entity_name)
        else:
            return "{}".format(self._entity_name)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        vehicle_attr = self.vehicle.get_attributes()
        return dict(
            model="{} {} {}".format(
                vehicle_attr["modelYear"],
                vehicle_attr["vehicleBrand"],
                vehicle_attr["vehicleType"],
            )
        )
