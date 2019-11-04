"""
Support for Mercedes cars with Mercedes ME.
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/device_tracker.mercedesme/
"""
import logging
from datetime import timedelta

from custom_components.mercedesmeapi import DATA_MME
from homeassistant.helpers.event import track_time_interval
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['mercedesmeapi']

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=30)


def setup_scanner(hass, config, see, discovery_info=None):
    """Set up the Mercedes ME tracker."""
    if discovery_info is None:
        return False

    data = hass.data[DATA_MME].data

    if not data.cars:
        return False

    MercedesMEDeviceTracker(hass, config, see, data)

    return True


class MercedesMEDeviceTracker(object):
    """A class representing a Mercedes ME device tracker."""

    def __init__(self, hass, config, see, data):
        """Initialize the Mercedes ME device tracker."""
        self.see = see
        self.data = data
        self.update_info()

        track_time_interval(
            hass, self.update_info, MIN_TIME_BETWEEN_SCANS)

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def update_info(self, now=None):
        """Update the device info."""
        for device in self.data.cars:

            location = device.location
            if location is None:
                continue

            dev_id = device.finorvin
            name = device.licenseplate

            p = v.get_position()
            position = (p['position']['latitude'], p['position']['longitude'])

            attrs = {
                'trackr_id': dev_id,
                'id': dev_id,
                'name': name
            }
            self.see(
                dev_id=dev_id, host_name=name,
                gps=position, attributes=attrs
            )

        return True
