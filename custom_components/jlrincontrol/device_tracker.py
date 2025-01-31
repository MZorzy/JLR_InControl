"""Support for tracking a JLR."""
import logging

from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import slugify

from . import DATA_KEY, SIGNAL_STATE_UPDATED

_LOGGER = logging.getLogger(__name__)


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    """Set up the Volvo tracker."""
    if discovery_info is None:
        return

    p = v.get_position()
    gps_position = (p["position"]["latitude"], p["position"]["longitude"])

    async def see_vehicle():
        """Handle the reporting of the vehicle position."""
        host_name = data.vehicle_name(vehicle)
        dev_id = '{}'.format(slugify(host_name))
        await async_see(
            dev_id=dev_id,
            host_name=host_name,
            source_type=SOURCE_TYPE_GPS,
            gps=gps_position,
            icon="mdi:car",
        )

    async_dispatcher_connect(hass, SIGNAL_STATE_UPDATED, see_vehicle)

    return True
