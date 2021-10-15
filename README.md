
# FreeDNS

Home Assistant integration for the FreeDNS service.

## Description

This custom component has been designed to for Home Assistant and allows you 
to keep your DNS records up to date. This has been heavily based on the 
official Home Assistant integration which can be found 
[here](https://www.home-assistant.io/integrations/freedns/).

## Setup

When setting up the integration you will be asked for the following information.

![Initial Setup Screen](https://github.com/uvjim/hass_freedns/raw/main/images/setup.png)

- `Full update URL`: this should be the full URL call to make for updates &ast;
- `Access token`: the access token to use &ast;
- `Scan Interval (in minutes)`: the frequency in minutes at which the 
  FreeDNS API should be called (defaults to 10 minutes) 

> &ast; these options are mutually exclusive

## Configurable Options

It is possible to configure the following options for the integration.

![Options Screen](https://github.com/uvjim/hass_freedns/raw/main/images/options.png)

- `Scan Interval (in minutes)`: the frequency in minutes at which the 
  FreeDNS API should be called