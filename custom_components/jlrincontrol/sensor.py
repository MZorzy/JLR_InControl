"""Support for JLR InControl sensors."""
import logging

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import RESOURCES, SIGNAL_STATE_UPDATED, JLREntity

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the JLR sensors."""
    if discovery_info is None:
        return
    add_entities([JLRSensor(hass, *discovery_info)])


class JLRSensor(JLREntity):
    """Representation of a JLR Sensor."""

    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.info("Updating ==========================================")
        val = self.get_updated_info()
        if val is None:
            return val
        if val:
            val = val[self._attribute]
        else:
            return None

        if self._attribute in [
            "last_connected",
            "service_inspection",
            "oil_inspection",
            "THEFT_ALARM_STATUS",
            "DOOR_FRONT_LEFT_POSITION",
            "WASHER_FLUID_WARN","BRAKE_FLUID_WARN","EXT_OIL_LEVEL_WARN","ENG_COOLANT_LEVEL_WARN",
            "WINDOW_FRONT_LEFT_STATUS","WINDOW_FRONT_RIGHT_STATUS","WINDOW_REAR_LEFT_STATUS","WINDOW_REAR_RIGHT_STATUS",
            "DOOR_FRONT_LEFT_POSITION","DOOR_FRONT_RIGHT_POSITION","DOOR_REAR_LEFT_POSITION","DOOR_REAR_RIGHT_POSITION",
        ]:
            return str(val)

        if self._attribute in [
            "DISTANCE_TO_EMPTY_FUEL",
            "ODOMETER_MILES","ODOMETER",
            "EXT_KILOMETERS_TO_SERVICE",
            "TYRE_PRESSURE_FRONT_LEFT","TYRE_PRESSURE_FRONT_RIGHT","TYRE_PRESSURE_REAR_LEFT","TYRE_PRESSURE_REAR_RIGHT",
            "FUEL_LEVEL_PERC",
        ]:
            return int(float(val))

        if self._attribute in ["ODOMETER_METER"]:
            return int(float(int(val) / 1000))

        return int(float(val))


    def update(self):
        _LOGGER.info("Updating here xxxxxxxxxxxxx")

    async def async_added_to_hass(self):
        _LOGGER.info(
            "CONNECTING TO DISPATCHER =============================================="
        )
        async_dispatcher_connect(
            self.hass, SIGNAL_STATE_UPDATED, self._schedule_immediate_update
        )

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return RESOURCES[self._attribute][3]

    @property
    def icon(self):
        """Return the icon."""
        return RESOURCES[self._attribute][2]

    @callback
    def _schedule_immediate_update(self):
        _LOGGER.info("IN CALLBACK HERE ==========XXXXXXXXXXXXXXXXXX===================")
        self.async_schedule_update_ha_state(True)
