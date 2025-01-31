"""Add Support for JLR Incontrol Binary Sensors."""
import logging

from homeassistant.components.binary_sensor import BinarySensorDevice

from . import RESOURCES, JLREntity

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the JLR Binary sensors."""
    if discovery_info is None:
        return
    add_devices([JLRSensor(hass, *discovery_info)])


class JLRSensor(JLREntity, BinarySensorDevice):
    """Representation of a JLR sensor."""

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        val = self.get_updated_info()
        if val is None:
            return val

        if val:
            val = val[self._attribute]
        else:
            return None

        if self._attribute in [
            "DOOR_IS_ALL_DOORS_LOCKED",
            "IS_SUNROOF_OPEN"
        ]:
            return bool(val == "FALSE")

        return val

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return RESOURCES[self._attribute][3]

    @property
    def icon(self):
        """Return the icon."""
        return RESOURCES[self._attribute][2]
