# eSTUDNA integration for Home Assistant

Cloud based integration for [eSTUDNA](https://www.estudna.cz/) devices utilizing
ThingsBoard API.

Supports both:

- **eSTUDNA** (original model) - uses CML API at https://cml.seapraha.cz/
- **eSTUDNA2** (new model) - uses CML5 API v2 at https://cml5.seapraha.cz/

## How to use

1. Install Home Assistant

1. Install HACS

1. Install this integration using HACS (add it as a custom repository)

1. Configure the integration

Search for **eSTUDNA** in the **Integrations** section of Home Assistant.

When configuring, you'll be asked to select your device type (eSTUDNA or eSTUDNA2)
and provide your CML app credentials.

## Features

### eSTUDNA (original)

- Water level sensor
- Two relay switches (OUT1, OUT2)

### eSTUDNA2 (new)

- Water level sensor
- Two relay switches (OUT1, OUT2)
