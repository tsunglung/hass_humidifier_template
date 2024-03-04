"""Support for Template Humidifier."""
import logging

import voluptuous as vol
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.script import Script
from homeassistant.components.template.const import CONF_AVAILABILITY_TEMPLATE
from homeassistant.components.template.template_entity import TemplateEntity
from homeassistant.components.fan import (
    DOMAIN as FAN_DOMAIN
)
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN
)
from homeassistant.components.humidifier import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_HUMIDITY,
    ENTITY_ID_FORMAT,
    MODE_AUTO,
    MODE_AWAY,
    MODE_NORMAL,
    HumidifierAction,
    HumidifierDeviceClass,
    HumidifierEntityFeature,
    HumidifierEntity
)
from homeassistant.const import (
    ATTR_CONFIGURATION_URL,
    ATTR_HW_VERSION,
    ATTR_MANUFACTURER,
    ATTR_MODE,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_SERIAL_NUMBER,
    ATTR_SUGGESTED_AREA,
    ATTR_SW_VERSION,
    ATTR_VIA_DEVICE,
    CONF_ENTITY_PICTURE_TEMPLATE,
    CONF_ICON_TEMPLATE,
    CONF_MODEL,
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    STATE_ON,
    STATE_OFF
)


DEFAULT_NAME = 'humidifier'
CONF_HUMIDITY_MIN = 'min_humidity'
CONF_HUMIDITY_MAX = 'max_humidity'
CONF_MODE_LIST = 'modes'
CONF_STATE_TEMPLATE = 'state_template'
CONF_CURRENT_HUMIDITY_TEMPLATE = 'current_humidity_template'
CONF_TARGET_HUMIDITY_TEMPLATE = 'target_humidity_template'
CONF_ACTION_TEMPLATE = 'action_template'
CONF_MODE_TEMPLATE = 'mode_template'
CONF_MODE_LIST_TEMPLATE = 'mode_list_template'
CONF_SWITCH_ID = 'switch_id'
CONF_SET_MODE_ACTION = 'set_mode_action'
CONF_SET_TARGET_HUMIDITY_ACTION = 'set_target_humidity_action'
CONF_TYPE = 'type'
CONF_CONFIGURATION_URL = 'configuration_url'
CONF_CONNECTIONS = 'connections'
CONF_IDENTIFIERS = 'identifiers'
CONF_HW_VERSION = 'hw_version'
CONF_MANUFACTURER = 'manufacturer'
CONF_SERIAL_NUMBER = 'serial_number'
CONF_SUGGESTED_AREA = 'suggested_area'
CONF_SW_VERSION = 'sw_version'
CONF_VIA_DEVICE = 'via_device'
CONF_DEVICE = 'device'

DEHUMIDIFIER_TYPE = 'dehumidifier'
HUMIDIFIER_TYPE = 'humidifier'

TYPES = [
  DEHUMIDIFIER_TYPE,
  HUMIDIFIER_TYPE
]

DEFAULT_TYPE = DEHUMIDIFIER_TYPE
DEFAULT_HUMIDITY = 50
DEFAULT_SWITCH_STATE = STATE_OFF
MIN_HUMIDITY = 40
MAX_HUMIDITY = 80

DOMAIN = "humidifier_template"

_LOGGER = logging.getLogger(__name__)


def validate_device_has_at_least_one_identifier(value: ConfigType) -> ConfigType:
    """Validate that a device info entry has at least one identifying value."""
    if value.get(CONF_IDENTIFIERS) or value.get(CONF_CONNECTIONS):
        return value
    raise vol.Invalid(
        "Device must have at least one identifying value in "
        "'identifiers' and/or 'connections'"
    )

HUMIDIFIER_ENTITY_DEVICE_INFO_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(CONF_IDENTIFIERS, default=list): vol.All(
                cv.ensure_list, [cv.string]
            ),
            vol.Optional(CONF_CONNECTIONS, default=list): vol.All(
                cv.ensure_list, [vol.All(vol.Length(2), [cv.string])]
            ),
            vol.Optional(CONF_MANUFACTURER): cv.string,
            vol.Optional(CONF_MODEL): cv.string,
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_HW_VERSION): cv.string,
            vol.Optional(CONF_SERIAL_NUMBER): cv.string,
            vol.Optional(CONF_SW_VERSION): cv.string,
            vol.Optional(CONF_VIA_DEVICE): cv.string,
            vol.Optional(CONF_SUGGESTED_AREA): cv.string,
            vol.Optional(CONF_CONFIGURATION_URL): cv.configuration_url,
        }
    ),
    validate_device_has_at_least_one_identifier,
)

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
  {
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SWITCH_ID): cv.string,
    vol.Optional(CONF_HUMIDITY_MIN, default=MIN_HUMIDITY): vol.Coerce(int),
    vol.Optional(CONF_HUMIDITY_MAX, default=MAX_HUMIDITY): vol.Coerce(int),
    vol.Optional(CONF_STATE_TEMPLATE): cv.template,
    vol.Optional(CONF_CURRENT_HUMIDITY_TEMPLATE): cv.template,
    vol.Optional(CONF_TARGET_HUMIDITY_TEMPLATE): cv.template,
    vol.Optional(CONF_ACTION_TEMPLATE): cv.template,
    vol.Optional(CONF_MODE_TEMPLATE): cv.template,
    vol.Optional(CONF_MODE_LIST_TEMPLATE): cv.template,
    vol.Optional(CONF_TYPE, default=DEFAULT_TYPE): vol.All(cv.string, vol.In(TYPES)),
    vol.Optional(
        CONF_MODE_LIST,
        default=[
            MODE_AUTO,
            MODE_AWAY,
            MODE_NORMAL
        ],
    ): cv.ensure_list,
    vol.Optional(CONF_SET_MODE_ACTION): cv.SCRIPT_SCHEMA,
    vol.Optional(CONF_SET_TARGET_HUMIDITY_ACTION): cv.SCRIPT_SCHEMA,
    vol.Optional(CONF_UNIQUE_ID): cv.string,
    vol.Optional(CONF_DEVICE): HUMIDIFIER_ENTITY_DEVICE_INFO_SCHEMA,
  }
)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
):
  """Set up the humidifier platform."""

  async_add_entities([TemplateHumidifier(hass, config)])


def device_info_from_specifications(
    specifications: dict[str, Any] | None,
) -> DeviceInfo | None:
    """Return a device description for device registry."""
    if not specifications:
        return None

    info = DeviceInfo(
        identifiers={(DOMAIN, id_) for id_ in specifications[CONF_IDENTIFIERS]},
        connections={
            (conn_[0], conn_[1]) for conn_ in specifications[CONF_CONNECTIONS]
        },
    )

    if CONF_MANUFACTURER in specifications:
        info[ATTR_MANUFACTURER] = specifications[CONF_MANUFACTURER]

    if CONF_MODEL in specifications:
        info[ATTR_MODEL] = specifications[CONF_MODEL]

    if CONF_NAME in specifications:
        info[ATTR_NAME] = specifications[CONF_NAME]

    if CONF_HW_VERSION in specifications:
        info[ATTR_HW_VERSION] = specifications[CONF_HW_VERSION]

    if CONF_SERIAL_NUMBER in specifications:
        info[ATTR_SERIAL_NUMBER] = specifications[CONF_SERIAL_NUMBER]

    if CONF_SW_VERSION in specifications:
        info[ATTR_SW_VERSION] = specifications[CONF_SW_VERSION]

    if CONF_VIA_DEVICE in specifications:
        info[ATTR_VIA_DEVICE] = (DOMAIN, specifications[CONF_VIA_DEVICE])

    if CONF_SUGGESTED_AREA in specifications:
        info[ATTR_SUGGESTED_AREA] = specifications[CONF_SUGGESTED_AREA]

    if CONF_CONFIGURATION_URL in specifications:
        info[ATTR_CONFIGURATION_URL] = specifications[CONF_CONFIGURATION_URL]

    return info


class TemplateHumidifier(TemplateEntity, HumidifierEntity, RestoreEntity):

    def __init__(self, hass: HomeAssistant, config: ConfigType):
        """Initialize the humidifier."""
        super().__init__(
            hass,
            availability_template=config.get(CONF_AVAILABILITY_TEMPLATE),
            icon_template=config.get(CONF_ICON_TEMPLATE),
            entity_picture_template=config.get(CONF_ENTITY_PICTURE_TEMPLATE),
        )
        self.hass = hass
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, config[CONF_NAME], hass=hass
        )
        self._config = config
        self._attr_unique_id = config.get(
            CONF_UNIQUE_ID,
            f"template_humidifier_{config[CONF_NAME].lower().replace(" ", "_")}"
        )
        self._attr_name = config[CONF_NAME]
        self._attr_min_humidity = config.get(CONF_HUMIDITY_MIN, MIN_HUMIDITY)
        self._attr_max_humidity = config.get(CONF_HUMIDITY_MAX, MAX_HUMIDITY)
        self._state_template = config.get(CONF_STATE_TEMPLATE, None)
        self._current_humidity_template = config.get(CONF_CURRENT_HUMIDITY_TEMPLATE, None)
        self._target_humidity_template = config.get(CONF_TARGET_HUMIDITY_TEMPLATE, None)
        self._action_template = config.get(CONF_ACTION_TEMPLATE, None)
        self._mode_template = config.get(CONF_MODE_TEMPLATE, None)
        self._mode_list_template = config.get(CONF_MODE_LIST_TEMPLATE, None)
        self._switch_id = config.get(CONF_SWITCH_ID, None)
        self._set_mode_action = config.get(CONF_SET_MODE_ACTION, None)
        self._set_target_humidity_action = config.get(CONF_SET_TARGET_HUMIDITY_ACTION, None)

        self._current_humidity = DEFAULT_HUMIDITY

        self._state = DEFAULT_SWITCH_STATE == STATE_ON
        self._attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER
        if self._config[CONF_TYPE] == HUMIDIFIER_TYPE:
            self._attr_device_class = HumidifierDeviceClass.HUMIDIFIER

        # To cheack if the switch state change if fired by the platform
        self._self_changed_switch = False

        self._target_humidity = DEFAULT_HUMIDITY
        if self._config[CONF_MODE_LIST]:
            self._attr_supported_features = HumidifierEntityFeature.MODES
            self._attr_available_modes = config[CONF_MODE_LIST]
            self._attr_mode = MODE_NORMAL
        if self._config.get(CONF_DEVICE):
            self._attr_device_info = device_info_from_specifications(self._config.get(CONF_DEVICE))

        self._available = True

        # set script variables
        self._set_mode_script = None
        set_mode_action = config.get(CONF_SET_MODE_ACTION)
        if set_mode_action:
            self._set_mode_script = Script(
                hass, set_mode_action, self._attr_name, DOMAIN
            )

        self._set_target_humidity_script = None
        set_target_humidity_action = config.get(CONF_SET_TARGET_HUMIDITY_ACTION)
        if set_target_humidity_action:
            self._set_target_humidity_script = Script(
                hass, set_target_humidity_action, self._attr_name, DOMAIN
            )

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Check If we have an old state
        previous_state = await self.async_get_last_state()
        if previous_state is not None:
            self._state = previous_state.state

            if mode := previous_state.attributes.get(
                ATTR_MODE, MODE_NORMAL
            ):
                self._attr_mode = mode

            if humidity := previous_state.attributes.get(
                ATTR_HUMIDITY, DEFAULT_HUMIDITY
            ):
                self._target_temp = humidity

            if current_temperature := previous_state.attributes.get(
                ATTR_CURRENT_HUMIDITY
            ):
                self._current_temp = current_temperature

            if humidity := previous_state.attributes.get(
                ATTR_CURRENT_HUMIDITY
            ):
                self._current_humidity = humidity

        # register templates
        if self._state_template:
            self.add_template_attribute(
                "_state",
                self._state_template,
                None,
                self._update_state,
                none_on_template_error=True,
            )

        if self._mode_template:
            self.add_template_attribute(
                "_mode",
                self._mode_template,
                None,
                self._update_mode,
                none_on_template_error=True,
            )

        if self._mode_list_template:
            self.add_template_attribute(
                "_mode_list",
                self._mode_list_template,
                None,
                self._update_mode_list,
                none_on_template_error=True,
            )

        if self._current_humidity_template:
            self.add_template_attribute(
                "_current_humidity",
                self._current_humidity_template,
                None,
                self._update_current_humidity,
                none_on_template_error=True,
            )

        if self._target_humidity_template:
            self.add_template_attribute(
                "_target_humidity",
                self._target_humidity_template,
                None,
                self._update_target_humidity,
                none_on_template_error=True,
            )

        if self._action_template:
            self.add_template_attribute(
                "_action",
                self._action_template,
                None,
                self._update_action,
                none_on_template_error=True,
            )

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._current_humidity

    @property
    def target_humidity(self) -> int | None:
        """Return the target humidity."""
        return self._target_humidity

    @property
    def is_on(self):
        """Return if the humidifier is on."""
        return self._state

    async def async_set_humidity(self, humidity):
        """Set target humidity."""
        self._target_humidity = humidity

        if self._set_target_humidity_script is not None:
            await self._set_target_humidity_script.async_run(
                run_variables={ATTR_HUMIDITY: humidity}, context=self._context
            )

    async def async_set_mode(self, mode: str) -> None:
        """Set new mode."""
        if self._mode_template is None:
            self._attr_mode = mode  # always optimistic
            self.async_write_ha_state()

        if self._set_mode_script is not None:
            await self._set_mode_script.async_run(
                run_variables={ATTR_MODE: mode}, context=self._context
            )

    async def async_turn_on(self) -> None:
        """Turn the device on."""
        self._state = True

        if self._switch_id is not None:
            if "fan" in self._switch_id:
                await self.hass.services.async_call(
                    FAN_DOMAIN,
                    SERVICE_TURN_ON,
                    {"entity_id": self._switch_id}
                )
            else:
                await self.hass.services.async_call(
                    SWITCH_DOMAIN,
                    SERVICE_TURN_ON,
                    {"entity_id": self._switch_id}
                )

    async def async_turn_off(self) -> None:
        """Turn the device off."""
        self._state = False

        if self._switch_id is not None:
            if "fan" in self._switch_id:
                await self.hass.services.async_call(
                    FAN_DOMAIN,
                    SERVICE_TURN_OFF,
                    {"entity_id": self._switch_id}
                )
            else:
                await self.hass.services.async_call(
                    SWITCH_DOMAIN,
                    SERVICE_TURN_OFF,
                    {"entity_id": self._switch_id}
                )

    @callback
    def _update_state(self, state):
        self._state = False
        if state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                if isinstance(state, TemplateError):
                    self._state = None
                    return

                if isinstance(state, bool):
                    self._state = state
                    return

                if isinstance(state, str):
                    self._state = state.lower() in ("true", STATE_ON)
                    return

            except ValueError:
                _LOGGER.error("Could not parse state from %s", state)
            self._state = False

    @callback
    def _update_mode(self, mode):
        if mode not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._attr_mode = mode
            except ValueError:
                _LOGGER.error("Could not parse mode from %s", mode)

    @callback
    def _update_mode_list(self, mode_list):
        if mode_list not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._attr_supported_features = HumidifierEntityFeature.MODES
                self._attr_available_modes = mode_list
                self._attr_mode = mode_list[0]
            except ValueError:
                _LOGGER.error("Could not parse mode from %s", mode_list)

    @callback
    def _update_current_humidity(self, humidity):
        if humidity not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._current_humidity = int(humidity)
            except ValueError:
                _LOGGER.error("Could not parse humidity from %s", humidity)

    @callback
    def _update_target_humidity(self, humidity):
        if humidity not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._target_humidity = int(humidity)
            except ValueError:
                _LOGGER.error("Could not parse humidity from %s", humidity)

    @callback
    def _update_action(self, action):
        if action not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                if not self._state:
                    self._attr_action = HumidifierAction.OFF
                else:
                    self._attr_action = HumidifierAction.HUMIDIFYING
                    if self._config.get(CONF_TYPE, HUMIDIFIER_TYPE) == DEHUMIDIFIER_TYPE:
                        self._attr_action = HumidifierAction.DRYING
                    if action == "fan":
                        self._attr_action = HumidifierAction.IDLE
            except ValueError:
                _LOGGER.error("Could not parse action from %s", action)

