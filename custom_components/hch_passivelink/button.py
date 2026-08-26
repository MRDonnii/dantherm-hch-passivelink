"""Filter-reset button for HCH PassiveLink."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import PassiveLinkEntity

DESCRIPTION = ButtonEntityDescription(
    key="filter_reset",
    translation_key="filter_reset",
    icon="mdi:air-filter",
    entity_category=EntityCategory.CONFIG,
)


class PassiveLinkFilterResetButton(PassiveLinkEntity, ButtonEntity):
    """Reset the locally tracked filter cycle to today.

    Purely local state — never writes to the Modbus bus.
    """

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, DESCRIPTION.key)
        self.entity_description = DESCRIPTION

    @property
    def available(self) -> bool:
        return self.coordinator.available

    async def async_press(self) -> None:
        self.coordinator.async_reset_filter()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([PassiveLinkFilterResetButton(entry.runtime_data)])
