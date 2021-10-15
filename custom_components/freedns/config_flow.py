""""""
import asyncio
from aiohttp.client_exceptions import InvalidURL, ClientError
import logging
from typing import Union

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientSession
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_URL,
)
from homeassistant.core import callback

from . import async_update_freedns
from .const import (
    CONF_INTERVAL_MINIMUM,
    DEFAULT_CONF_NAME,
    DEFAULT_INTERVAL_MINS,
    DEFAULT_REQUEST_TIMEOUT_SECS,
    DOMAIN,
    STEP_CHECK,
    STEP_CONFIG,
    STEP_FINISH,
    STEP_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


async def _async_build_schema_with_user_input(step: str, user_input=None) -> vol.Schema:
    """Build the input and validation schema for the config UI

    :param step: the step we're in for a configuration or installation of the integration
    :param user_input: the data that should be used as defaults
    :return: the schema including necessary restrictions, defaults, pre-selections etc.
    """

    if user_input is None:
        user_input = {}

    schema = {}
    if step == STEP_CONFIG:
        schema = {
            vol.Optional(CONF_URL): cv.string,
            vol.Optional(CONF_ACCESS_TOKEN): cv.string,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_INTERVAL_MINS),
            ): cv.positive_int,
        }
    elif step == STEP_OPTIONS:
        schema = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_INTERVAL_MINS),
            ): cv.positive_int,
        }

    return vol.Schema(schema)


class FreeDNSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """"""

    task_check = None

    def __init__(self):
        self._errors: dict = {}
        self._options: dict = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler"""

        return FreeDNSOptionsFlowHandler(config_entry=config_entry)

    async def _async_task_check(
            self,
            url: str,
            auth_token: str,
            timeout: int
    ) -> None:

        session: ClientSession = self.hass.helpers.aiohttp_client.async_get_clientsession()
        try:
            await async_update_freedns(hass=self.hass, session=session, url=url, auth_token=auth_token, timeout=timeout)
        except InvalidURL:
            self._errors["base"] = "invalid_url"
        except ClientError:
            self._errors["base"] = "cant_connect"

        await asyncio.sleep(2)
        self.hass.async_create_task(self.hass.config_entries.flow.async_configure(flow_id=self.flow_id))

    async def async_step_user(self, user_input: Union[dict, None] = None) -> data_entry_flow.FlowResult:
        """"""

        return await self.async_step_config()

    async def async_step_config(self, user_input: Union[dict, None] = None) -> data_entry_flow.FlowResult:
        """"""

        if user_input is not None:
            if (user_input.get(CONF_URL) and user_input.get(CONF_ACCESS_TOKEN)) \
                    or (not user_input.get(CONF_URL) and not user_input.get(CONF_ACCESS_TOKEN)):
                self._errors["base"] = "url_access_exclusive"
            elif user_input.get(CONF_URL):
                url = user_input.get(CONF_URL)
                url_netloc = vol.urlparse.urlparse(url=url).netloc
                if not url_netloc.endswith("afraid.org"):
                    self._errors["base"] = "invalid_url"
                else:
                    self._errors = {}
            elif user_input.get(CONF_SCAN_INTERVAL) < CONF_INTERVAL_MINIMUM:
                self._errors["base"] = "below_minimum_scan_interval"

            if not self._errors:
                self._options.update(user_input)
                self._options[CONF_TIMEOUT] = DEFAULT_REQUEST_TIMEOUT_SECS
                return await self.async_step_check(user_input=user_input)

        return self.async_show_form(
            step_id=STEP_CONFIG,
            data_schema=await _async_build_schema_with_user_input(STEP_CONFIG, user_input),
            errors=self._errors
        )

    # noinspection PyUnusedLocal
    async def async_step_check(self, user_input=None) -> data_entry_flow.FlowResult:
        """"""

        if not self.task_check:
            self.task_check = self.hass.async_create_task(
                self._async_task_check(
                    url=self._options.get(CONF_URL),
                    auth_token=self._options.get(CONF_ACCESS_TOKEN),
                    timeout=self._options.get(CONF_TIMEOUT),
                )
            )
            return self.async_show_progress(step_id=STEP_CHECK, progress_action="task_check")

        # noinspection PyBroadException
        try:
            await self.task_check
            self.task_check = None
        except Exception:
            return self.async_abort(reason="abort_check")

        if self._errors:
            return self.async_show_progress_done(next_step_id=STEP_CONFIG)

        ret = self.async_show_progress_done(next_step_id=STEP_FINISH)
        return ret

    # noinspection PyUnusedLocal
    async def async_step_finish(self, user_input=None) -> data_entry_flow.FlowResult:
        """"""

        return self.async_create_entry(title=DEFAULT_CONF_NAME, data={}, options=self._options)


class FreeDNSOptionsFlowHandler(config_entries.OptionsFlow):
    """"""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Constructor"""

        super().__init__()
        self._config_entry = config_entry
        self._errors: dict = {}
        self._options: dict = dict(config_entry.options)

    async def _async_task_check(
            self,
            url: str,
            auth_token: str,
            timeout: int
    ) -> None:

        session: ClientSession = self.hass.helpers.aiohttp_client.async_get_clientsession()
        await async_update_freedns(hass=self.hass, session=session, url=url, auth_token=auth_token, timeout=timeout)

        self.hass.async_create_task(self.hass.config_entries.flow.async_configure(flow_id=self.flow_id))

    # noinspection PyUnusedLocal
    async def async_step_init(self, user_input=None) -> data_entry_flow.FlowResult:
        """"""

        return await self.async_step_options()

    async def async_step_options(self, user_input: Union[dict, None] = None) -> data_entry_flow.FlowResult:
        """"""

        if user_input is not None:
            if user_input.get(CONF_SCAN_INTERVAL) < CONF_INTERVAL_MINIMUM:
                self._errors["base"] = "below_minimum_scan_interval"
            else:
                self._errors = {}
                self._options.update(user_input)
                return await self.async_step_finish(user_input=user_input)

        return self.async_show_form(
            step_id=STEP_OPTIONS,
            data_schema=await _async_build_schema_with_user_input(STEP_OPTIONS, self._options),
            errors=self._errors
        )

    # noinspection PyUnusedLocal
    async def async_step_finish(self, user_input=None) -> data_entry_flow.FlowResult:
        """"""

        return self.async_create_entry(title=DEFAULT_CONF_NAME, data=self._options)
