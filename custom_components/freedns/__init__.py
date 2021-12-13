"""Integrate with FreeDNS Dynamic DNS service at freedns.afraid.org."""
import asyncio
import datetime
import logging

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_URL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_UNSUB_UPDATE_LISTENER,
    DEFAULT_INTERVAL_MINS,
    DEFAULT_REQUEST_TIMEOUT_SECS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_URL = "https://freedns.afraid.org/dynamic/update.php"


async def async_update_freedns(
        session: aiohttp.ClientSession,
        url: str,
        auth_token: str,
        timeout: int
) -> bool:
    """Update FreeDNS."""

    params = None

    if url is None:
        url = UPDATE_URL

    if auth_token is not None:
        params = {auth_token: ""}

    try:
        with async_timeout.timeout(timeout):
            _LOGGER.debug("Using FreeDNS URL %s with params %s", url, params)
            resp = await session.get(url, params=params, raise_for_status=True)
            body = await resp.text()
            body = body.strip()

            if "has not changed" in body or "No IP change detected" in body:
                # IP has not changed.
                _LOGGER.debug("FreeDNS update skipped: IP has not changed")
                return True

            if "ERROR" not in body:
                _LOGGER.debug("Updating FreeDNS was successful: %s", body)
                return True

            if "Invalid update URL" in body:
                _LOGGER.error("FreeDNS update token is invalid")
                raise
            else:
                _LOGGER.warning("Updating FreeDNS failed: %s", body)
                raise

    except aiohttp.client.InvalidURL:
        _LOGGER.error("Invalid URL: %s", url)
        raise

    except aiohttp.ClientError:
        _LOGGER.warning("Can't connect to FreeDNS API")
        raise

    except asyncio.TimeoutError:
        _LOGGER.warning("Timeout (%s seconds) from FreeDNS API at %s", timeout, url)
        raise


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Initialise the FreeDNS component

    :param hass:
    :param config_entry:
    :return:
    """

    # region #-- prepare the storage --#
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})
    # endregion

    # region #-- listen for config changes --#
    config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )
    # endregion

    # region #-- setup updating the FreeDNS entry --#
    session: aiohttp.ClientSession = hass.helpers.aiohttp_client.async_get_clientsession()
    url = config_entry.options.get(CONF_URL)
    auth_token = config_entry.options.get(CONF_ACCESS_TOKEN)
    update_interval = config_entry.options.get(CONF_SCAN_INTERVAL)
    req_timeout = config_entry.options.get(CONF_TIMEOUT)

    try:
        await async_update_freedns(session, url, auth_token, req_timeout)
    except Exception as err:
        raise ConfigEntryNotReady(err)

    async def async_update_domain_callback(_: datetime.datetime):
        """Update the FreeDNS entry."""

        try:
            await async_update_freedns(session, url, auth_token, req_timeout)
        except (asyncio.exceptions.TimeoutError, asyncio.exceptions.CancelledError):
            pass

    config_entry.async_on_unload(
        async_track_time_interval(hass, async_update_domain_callback, datetime.timedelta(minutes=update_interval))
    )
    # endregion

    return True


# noinspection PyUnusedLocal
async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Cleanup when unloading a config entry

    :param hass:
    :param config_entry:
    :return:
    """

    hass.data[DOMAIN].pop(config_entry.entry_id)

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Reload the config entry

    :param hass:
    :param config_entry:
    :return:
    """

    return await hass.config_entries.async_reload(config_entry.entry_id)
