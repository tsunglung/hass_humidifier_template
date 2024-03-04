The `humidifier_template` platform creates humidifier devices that combine integrations and provides the ability to run scripts or invoke services for each of the `set_*` commands of a humidifier entity.

## Configuration

All configuration variables are optional. The humidifier device will work in optimistic mode (assumed state) if a template isn't defined.

If you do not define a `template` or its corresponding `action` the humidifier device will not have that attribute, e.g. either `swing_mode_template` or `set_swing_mode` must be defined for the humidifier to have a swing mode.

| Name                             | Type                                                                      | Description                                                                                                                                                                                                                                                                                     | Default Value                                      |
| -------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| name                             | `string`                                                                  | The name of the humidifier device.                                                                                                                                                                                                                                                                 | "Template humidifier"                                 |
| unique_id                             | `string`                                                                  | The [unique id](https://developers.home-assistant.io/docs/entity_registry_index/#unique-id) of the humidifier entity.                                                                                                                                                                                                                                                                 | None                                 |
| current_humidity_template        | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the current humidity.                                                                                                                                                                                                                                                 |                                                    |
| target_humidity_template      | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the target humidity of the humidifier device.                                                                                                                                                                                                                         |                                                    |
| state_template               | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the state of the humidifier device.                                                                                                                                                                                                                                  |                                                    |
| mode_template               | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the mode of the humidifier device.                                                                                                                                                                                                                                  |                                                    |
| action_template               | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Defines a template to get the action of the humidifier device.                                                                                                                                                                                                                                  |                                                    |
|                                  |                                                                           |                                                                                                                                                                                                                                                                                                 |                                                    |
| set_target_humidity_action                  | [`action`](https://www.home-assistant.io/docs/scripts)                    | Defines an action to run when the humidifier device is given the set target humidity command. Can use `humidity` variables.                                                                                                                  |                                                    |
| set_mode_action                    | [`action`](https://www.home-assistant.io/docs/scripts)                    | Defines an action to run when the humidifier device is given the set mode command. Can use `mode` variable.                                                                                                                                                                              |                                                    |
|                                  |                                                                           |                                                                                                                                                                                                                                                                                                 |                                                    |
| modes                            | `list`                                                                    | A list of supported modes. Needs to be a subset of the default values.                                                                                                                                                                                                                     | ["auto", "off", "comfort", "config", "dry", "smart"] |
|                                  |                                                                           |                                                                                                                                                                                                                                                                                                 |                                                    |
| min_humidity                         | `float`                                                                   | Minimum set point available.                                                                                                                                                                                                                                                                    | 40                                                  |
| max_humidity                         | `float`                                                                   | Maximum set point available.                                                                                                                                                                                                                                                                    | 70                                                 |

## Example Configuration

```yaml
humidifier:
  - platform: humidifier_template
    name: Bedroom Dehumidifier
    modes:
      - "auto"
      - "dry"
      - "comfort"
      - "config"
    min_humidity: 40
    max_humidity: 80

    # get current humidity.
    current_humidity_template: "{{ states('sensor.bedroom_humidity') }}"

    # mode switch for UI.
    mode_template: "{{ states('input_boolean.bedroom_mode') }}"

    # example action
    set_mode_action:
      # allows me to disable sending commands to dehumidifier via UI.
      - condition: state
        entity_id: input_boolean.enable_dehumidifier_controller
        state: "on"

      # send the humidifiers current state to esphome.
      - service: fan.set_preset_mode
        target:
          entity_id: fan.bedroom_dehumidifier_nottemplate
        data:          
          preset_mode: "{{ mode }}"

      # could also send IR command via broadlink service calls etc.
```

### Example action to control existing Home Assistant devices

```yaml
humidifier:
  - platform: humidifier_template
    # ...
    set_hvac_mode:
      # allows you to control an existing Home Assistant FAN device
      - service: fan.set_preset_mode
        data:
          entity_id: fan.bedroom_dehumidifier_nottemplate
          mode: "{{ states('fan.bedroom_dehumidifier_template') }}"
```

### Use Cases

- Merge multiple components into one humidifier device (just like any template platform).
- Control optimistic humidifier devices such as IR aircons via service calls.