"""------------------for RobotKing"""
from __future__ import annotations
import logging
from enum import Enum

from ..const import StateOptions
from ..core_async import ClientAsync
from ..device import Device, DeviceStatus
from ..device_info import DeviceInfo
from ..core_exceptions import InvalidDeviceStatus

STATE_ROBOT_KING_POWER_OFF = "STATE_POWER_OFF"
STATE_ROBOT_KING_END = ["STATE_END", "STATE_COMPLETE"]
STATE_ROBOT_KING_ERROR_OFF = "OFF"
STATE_ROBOT_KING_ERROR_NO_ERROR = [
    "ERROR_NOERROR",
    "ERROR_NOERROR_TITLE",
    "No Error",
    "No_Error",
]

POWER_STATUS_KEY = ["State", "state"]
CMD_WAKE_UP = [["Config", "Wakeup"], ["Set", "Wakeup"], ["WakeUp", None]]

ADD_FEAT_POLL_INTERVAL = 300  # 5 minutes

class RKCleanMode(Enum):
    """The cleaning mode for an WH device."""

    ZZ = "@RK_TERM_CLEANMODE_ZIGZAG_W"
    SB = "@RK_TERM_CLEANMODE_SECTOR_W"
    SPOT = "@RK_TERM_CLEANMODE_FOCUS_W"
    MACRO = "@RK_TERM_CLEANMODE_MACRO_W"


_LOGGER = logging.getLogger(__name__)

class RobotKingDevice(Device):
    """A higher-level interface for a Robot King."""

    def __init__(self, client: ClientAsync, device_info: DeviceInfo):
        super().__init__(client, device_info, RobotKingStatus(self))

    def reset_status(self):
        self._status = RobotKingStatus(self)
        return self._status

    async def poll(self) -> RobotKingStatus | None:
        """Poll the device's current state."""

        res = await self._device_poll("robotKing",
            additional_poll_interval_v1=ADD_FEAT_POLL_INTERVAL,
            additional_poll_interval_v2=ADD_FEAT_POLL_INTERVAL,
            thinq2_query_device=True,)
        _LOGGER.warning("Res %s", str(res))

        if not res:
            return None

        self._status = RobotKingStatus(self, res)
        _LOGGER.warning("Status %s", str(self._status))

        return self._status

    async def wake_up(self):
        """Wakeup the device."""
        if not self._stand_by:
            raise InvalidDeviceStatus()

        keys = self._get_cmd_keys(CMD_WAKE_UP)
        await self.set(keys[0], keys[1], value=keys[2])
        self._stand_by = False
        self._update_status(POWER_STATUS_KEY, self._get_runstate_key("STATE_INITIAL"))


class RobotKingStatus(DeviceStatus):
    """
    Higher-level information about a robot king's current status.

    :param device: The Device instance.
    :param data: JSON data from the API.
    """

    _device: RobotKingDevice

    def __init__(self, device: RobotKingDevice, data: dict | None = None):
        """Initialize device status."""
        super().__init__(device, data)
        _LOGGER.warning("Data %s", str(data))

        self._run_state = None
        self._error = None

    def _get_run_state(self):
        """Get current run state."""
        if not self._run_state:
            state = self.lookup_enum(["State", "state"])
            _LOGGER.warning("State %s", str(state))

            if not state:
                self._run_state = STATE_ROBOT_KING_POWER_OFF
            else:
                self._run_state = state
        return self._run_state

    def _get_error(self):
        """Get current error."""
        if not self._error:
            error = self.lookup_reference(["Error", "error"], ref_key="title")
            if not error:
                self._error = STATE_ROBOT_KING_ERROR_OFF
            else:
                self._error = error
        return self._error

    def update_status(self, key, value):
        """Update device status."""
        if not super().update_status(key, value):
            return False
        self._run_state = None
        return True

    @property
    def is_on(self):
        """Return if device is on."""
        run_state = self._get_run_state()
        return STATE_ROBOT_KING_POWER_OFF not in run_state

    @property
    def is_run_completed(self):
        """Return if run is completed."""
        run_state = self._get_run_state()
        if any(state in run_state for state in STATE_ROBOT_KING_END) or (
            STATE_ROBOT_KING_POWER_OFF in run_state
        ):
            return True
        return False

    @property
    def is_error(self):
        """Return if an error is present."""
        if not self.is_on:
            return False
        error = self._get_error()
        if error in STATE_ROBOT_KING_ERROR_NO_ERROR or error == STATE_ROBOT_KING_ERROR_OFF:
            return False
        return True

    @property
    def run_state(self):
        """Return current run state."""
        run_state = self._get_run_state()
        if STATE_ROBOT_KING_POWER_OFF in run_state:
            run_state = StateOptions.NONE
        return self._update_feature('RUN_STATE', run_state)


    @property
    def error_msg(self):
        """Return current error message."""
        if not self.is_error:
            error = StateOptions.NONE
        else:
            error = self._get_error()
        return self._update_feature('ERROR_MSG', error)

    def _update_features(self):
        _ = [
            self.run_state,
            self.error_msg,
        ]
