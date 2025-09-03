# EcoMAX360 Home Assistant Integration

This repository contains a modern, fully asynchronous custom integration
for Home Assistant that allows you to monitor and control boilers or
stoves equipped with a Plum EcoMAX 360 controller.  The integration
exposes a suite of temperature sensors reflecting the values reported by
the controller and provides a thermostat entity capable of changing
preset modes and adjusting the target temperature.  Following a
comprehensive refactoring, the low‑level communication code is now
isolated in a dedicated API layer and the Home Assistant logic is
cleanly separated, making the component easier to maintain and extend.

## Features

The integration has been redesigned to adhere to Home Assistant’s
recommended architecture.  The key features are:

- **Dynamic sensors** – For every measurement reported by the EcoMAX
  controller (e.g. supply temperature, domestic hot water temperature,
  buffer tank temperature, outdoor temperature) the integration
  automatically instantiates a sensor entity.  These sensors are
  updated at the interval configured via the options flow (default
  every 30 seconds).  Units and icons are assigned automatically based
  on the parameter definition.
- **Smart thermostat** – A climate entity exposes the thermostat
  functionality of the controller.  You can view the current and target
  temperatures and select preset modes (Eco, Comfort, Away, Calendar,
  etc.).  Changes are sent to the controller via a single
  asynchronous TCP connection.
- **Zero‑YAML setup** – Configuration is performed entirely via the
  Home Assistant UI.  When adding the integration you specify the
  IP address and port of your controller.  The polling interval can be
  tuned via the options flow; no manual editing of `configuration.yaml`
  is necessary.
- **Central data coordinator** – A `DataUpdateCoordinator` polls the
  controller at a configurable interval and shares the latest values
  with all entities.  Under the hood, it uses an asynchronous client
  that establishes a single TCP connection, listens for broadcast
  frames and disconnects cleanly after each poll.  Entity code never
  touches sockets directly.
- **Asynchronous API layer** – All low‑level communication with the
  EcoMAX controller lives in the `custom_components/ecomax360/api`
  package.  The client handles connection management, sending frames
  and listening for responses or broadcasts.  Frame construction and
  decoding are encapsulated in helper utilities.  This separation
  greatly improves testability and makes it trivial to extend the
  integration for other EcoMAX models.

## Installation

1. Copy the `custom_components/ecomax360` directory into the
   `<config>/custom_components` directory of your Home Assistant
   installation.  Create the `custom_components` directory if it does
   not already exist.
2. Restart Home Assistant.
3. Navigate to *Settings → Devices & Services* and click on *Add
   Integration*.  Search for “EcoMAX360” and follow the on‑screen
   instructions to enter your controller’s IP address and port.

Alternatively, you can add the repository as a custom repository in
HACS and install it from there.  See the [HACS documentation](https://hacs.xyz)
for details.

## Developer Guide

The project follows the recommended structure for Home Assistant custom
components.  After the refactoring there is a clear separation
between the Home Assistant–specific logic (entities, coordinator,
configuration flows) and the device communication layer.  The most
important modules are:

- **`custom_components/ecomax360/__init__.py`** – Implements the
  integration’s entry points.  When a config entry is set up, it
  creates an `EcoMaxClient` with the host/port provided by the user,
  instantiates an `EcoMaxDataUpdateCoordinator` to poll the device and
  stores both under `hass.data[DOMAIN][entry_id]`.  It forwards the
  entry to the sensor and climate platforms and registers an update
  listener to reload the entry whenever options change.  When the
  entry is unloaded, the client disconnects cleanly.
- **`custom_components/ecomax360/api/`** – Houses the pure API layer.
  - `client.py` defines `EcoMaxClient`, an asynchronous TCP client
    providing methods to send frames, receive acknowledgements and
    listen for specific broadcast frames.  It never interprets data
    itself; it simply returns decoded payloads using helper
    functions.
  - `parameters.py` declares the data structures used to decode
    thermostat and broadcast frames.  Each structure maps a key to
    the byte offset and type of the corresponding value.  The top‑level
    `PARAMETER` dictionary describes the high‑level commands (e.g.
    `GET_DATAS`, `GET_THERMOSTAT`) by specifying the function code,
    search marker and expected frame length.  This module is the
    single source of truth for parameter definitions.
  - `trame.py` (protocol) implements the `Trame` class used to
    assemble frames.  It encapsulates the EcoMAX protocol framing
    rules, computing length bytes and CRC checksums automatically.
    Other code constructs frames by instantiating `Trame` and calling
    `build()`; the API client handles sending the resulting bytes.
- **`custom_components/ecomax360/coordinator.py`** – Defines
  `EcoMaxDataUpdateCoordinator`, a subclass of Home Assistant’s
  `DataUpdateCoordinator`.  It holds an `EcoMaxClient`, polls the
  device at a configurable interval by calling
  `client.listen_frame("GET_DATAS")` and exposes the decoded values
  via its `data` attribute.  Errors during polling are wrapped into
  `UpdateFailed` so that Home Assistant marks the entities as
  unavailable.
- **`custom_components/ecomax360/sensor.py`** – Implements a generic
  sensor entity that derives from both `CoordinatorEntity` and
  `SensorEntity`.  At startup, one instance per measurement key in
  `ECOMAX` is created.  The unit of measurement and icon are looked up
  based on the key name.  Sensor values are read from
  `self.coordinator.data` and converted to floats when possible.
- **`custom_components/ecomax360/climate.py`** – Provides the
  `EcomaxThermostat` entity.  It derives from both `CoordinatorEntity`
  and `ClimateEntity` and uses the client to perform preset changes
  and setpoint updates through high‑level methods
  `async_change_preset()` and `async_set_setpoint()`, and to
  fetch thermostat state via `async_get_thermostat()`.  These
  abstractions hide the frame construction and acknowledgement logic
  from the entity.  The entity maps EcoMAX mode codes to Home
  Assistant preset names and exposes standard climate properties.
- **`custom_components/ecomax360/config_flow.py`** – Contains the UI
  configuration and options flows.  The flows prompt the user for
  host, port and scan interval, validate connectivity by attempting a
  connection with `EcoMaxClient`, prevent duplicate entries and
  persist changes.
- **`custom_components/ecomax360/const.py`** – Defines constants
  shared across the integration (domain name, configuration keys,
  default scan interval and list of supported platforms).

The code is annotated with Python type hints throughout and includes
docstrings explaining the purpose and behaviour of each class and
function.  These annotations aid static analysis and make it easier for
contributors to extend the integration with additional parameters or
entities.  For a deeper understanding of the protocol itself, consult
the comments in `api/parameters.py` and `trame.py`.

## Running the Tests

A comprehensive test suite resides in the `tests` directory.  The
tests focus on the internal helper functions and classes that make up
the integration and can be executed without a running Home Assistant
instance or a real EcoMAX controller.  Each test spins up a minimal
environment with stub modules to satisfy Home Assistant imports where
necessary.  The suite currently includes:

- **`test_utils.py`** – Verifies numeric conversion helpers and the
  `extract_data()` function used to decode payloads according to the
  structures defined in `api/parameters.py`.
- **`test_trame.py`** – Ensures that the `Trame` class correctly
  computes frame lengths and CRC checksums when assembling frames.
- **`test_climate.py`** – Uses Home Assistant stubs to load the
  thermostat entity in isolation.  It verifies that changing the
  preset mode and setting the temperature result in the expected
  frames being sent and that the entity updates its state when new
  thermostat data is received.
- **`test_sensor.py`** – Dynamically loads the sensor platform using
  Home Assistant stubs and asserts that sensor entities expose values
  from the coordinator, assign appropriate units and icons, and
  correctly report availability.
- **`test_coordinator.py`** – Provides a dummy client to the data
  coordinator and verifies that calling the private
  `_async_update_data` method triggers the expected calls on the
  client and returns the decoded data.

To run the tests locally, install `pytest` and execute:

```bash
pip install pytest
pytest -q
```

When contributing changes, ensure that all existing tests continue to
pass and consider adding new ones to cover your modifications.  In
particular, tests that exercise the API layer and the coordinator
would be valuable additions for future work.
