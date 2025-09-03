"""Asynchronous client for EcoMAX controllers.

This module defines :class:`EcoMaxClient`, a thin wrapper around a TCP
connection to an EcoMAX controller.  The protocol used by the controller
is a binary frame‑based protocol.  Each frame starts with a 0x68 byte and
ends with 0x16.  Between these markers the frame contains a header with
the length, destination and source addresses as well as a function code
followed by a data payload and finally a 2‑byte CRC.

The client class does not interpret these frames itself; instead it
provides helper methods for sending raw frames and for listening for
frames containing specific payloads defined by the :mod:`parameters` module.

This class is intended to be used by the data coordinator and by the
entities that need to send commands to the EcoMAX device.  It handles
connecting to the device, performing non‑blocking reads and writes, and
closing the socket when finished.

The implementation deliberately avoids storing any global host or port.
Every instance of :class:`EcoMaxClient` is constructed with the desired
host and port, which are provided by the user via the Home Assistant
configuration flow.  This design makes the integration easier to test and
avoids leaking configuration details into unrelated modules.

Usage example::

    client = EcoMaxClient("192.168.1.38", 8899)
    await client.async_connect()
    data = await client.listen_frame("GET_DATAS")
    await client.async_disconnect()

"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
from typing import Dict, Optional

from .parameters import PARAMETER

# The Trame class is used to build and encode frames.  Importing it here
# avoids duplicating the frame construction logic in higher level modules.
from ..trame import Trame

# struct is required for packing floating point values into little-endian
import struct
from ..utils import extract_data


_LOGGER = logging.getLogger(__name__)


class EcoMaxClient:
    """Asynchronous TCP client for the EcoMAX controller.

    Each instance of :class:`EcoMaxClient` manages its own TCP connection.
    The connection is lazy–initialised; it will not be opened until
    :meth:`async_connect` is called.  After use, it is important to call
    :meth:`async_disconnect` to release the network resources.

    Parameters
    ----------
    host: str
        The IP address or hostname of the EcoMAX controller.
    port: int
        The TCP port to connect to.  The default port on most devices is
        ``8899`` but this may vary depending on the installation.
    """

    def __init__(self, host: str, port: int) -> None:
        self.host: str = host
        self.port: int = port
        self._socket: Optional[socket.socket] = None
        # Use the running loop for socket operations; required for
        # non‑blocking socket methods.
        self._loop = asyncio.get_event_loop()

    async def async_connect(self) -> None:
        """Open a non‑blocking TCP connection to the EcoMAX controller.

        This method can safely be called multiple times; the connection
        will only be opened if it is not already established.  If the
        connection attempt fails, an exception will be raised.
        """
        if self._socket is not None:
            return
        _LOGGER.debug("Connecting to EcoMAX at %s:%s", self.host, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        try:
            await self._loop.sock_connect(sock, (self.host, self.port))
        except Exception:
            sock.close()
            raise
        self._socket = sock

    async def async_disconnect(self) -> None:
        """Close the underlying socket.

        This method is idempotent; closing an already closed socket has
        no effect.
        """
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None

    async def _async_recv_hex(self) -> str:
        """Receive bytes from the socket and return a hex string.

        This helper reads up to 1024 bytes from the socket in a single
        call.  It is used internally by :meth:`listen_frame` and
        :meth:`async_request`.
        """
        assert self._socket is not None, "Socket not connected"
        data = await self._loop.sock_recv(self._socket, 1024)
        return data.hex()

    async def async_send(self, frame: bytes, ack_flag: str) -> None:
        """Send a frame to the controller and wait for acknowledgement.

        This method writes the given frame to the socket and waits until
        the controller replies with an acknowledgement frame that contains
        ``ack_flag`` at the expected position.  If an acknowledgement is
        not received within a reasonable number of attempts, the method
        silently returns.  The frame itself is not parsed or stored; the
        caller is responsible for handling any required responses.

        Parameters
        ----------
        frame: bytes
            The binary frame to send to the controller.
        ack_flag: str
            The two–character hex string identifying the acknowledgement
            flag (e.g. ``"a9"``).  The method will compare this flag
            against the 15th and 16th hex characters of each received
            frame (positions 14:16 in a zero‑based index).
        """
        assert self._socket is not None, "Socket not connected"
        attempts = 0
        max_attempts = 10
        while attempts < max_attempts:
            await self._loop.sock_sendall(self._socket, frame)
            response_hex = await self._async_recv_hex()
            # Response must be long enough to contain ack_flag
            if response_hex and len(response_hex) >= 16 and response_hex[14:16] == ack_flag:
                _LOGGER.debug("Acknowledgement received for frame: %s", frame.hex())
                return
            attempts += 1
            # Short pause between retries to avoid flooding the bus
            await asyncio.sleep(0.1)
        _LOGGER.warning("No acknowledgement received for frame after %d attempts", max_attempts)

    async def async_request(
        self,
        frame: bytes,
        datastruct: Dict[str, Dict[str, object]],
        data_to_search: str,
        ack_flag: str,
        *,
        max_tries: int = 5,
    ) -> Optional[Dict[str, object]]:
        """Send a request frame and parse the first matching response.

        The EcoMAX protocol uses request/response semantics for many
        commands.  This method sends ``frame`` and then repeatedly reads
        incoming frames until it finds one that contains the ``data_to_search``
        marker and has the expected acknowledgement flag.  When found,
        :func:`extract_data` is called to decode the payload according to
        ``datastruct``.  If no matching frame is received after
        ``max_tries`` attempts, the method returns ``None``.

        Parameters
        ----------
        frame: bytes
            The binary frame to send.
        datastruct: dict
            A mapping describing how to decode the payload.  See
            :mod:`~custom_components.ecomax360.api.parameters` for the
            structure definition.
        data_to_search: str
            A substring that must appear in the hexadecimal representation
            of the response for it to be considered valid.
        ack_flag: str
            A two–character hex string used to filter responses.  Only
            responses whose bytes 14:16 equal ``ack_flag`` are considered.
        max_tries: int, optional
            The maximum number of attempts to send the request and wait for
            a matching response.  Defaults to 5.

        Returns
        -------
        dict or None
            A dictionary of decoded values if a matching frame was
            received, otherwise ``None``.
        """
        assert self._socket is not None, "Socket not connected"
        tries = 0
        while tries < max_tries:
            await self._loop.sock_sendall(self._socket, frame)
            # allow some time for the device to respond
            await asyncio.sleep(0.1)
            frames_hex = await self._async_recv_hex()
            # split into individual frames by looking for 68 .. 16 patterns
            responses = re.findall(r"68.*?16", frames_hex)
            for resp_hex in responses:
                # Filter on ack flag
                if len(resp_hex) >= 16 and resp_hex[14:16] == ack_flag:
                    if data_to_search in resp_hex:
                        return extract_data(resp_hex, datastruct)
            tries += 1
        _LOGGER.debug(
            "No matching response for frame %s after %d attempts", frame.hex(), max_tries
        )
        return None

    # ------------------------------------------------------------------
    # High-level thermostat operations
    # ------------------------------------------------------------------
    async def async_change_preset(self, preset_hex: str) -> None:
        """Change the operating preset of the EcoMAX controller.

        This method encapsulates the frame construction and acknowledgement
        handling required to set a new preset mode on the controller.  The
        caller should supply the preset as a two‑character hex string
        (e.g. ``"01"`` for ``eco``).  Connection management is handled
        internally: the socket is opened if necessary and closed when the
        operation completes.

        Parameters
        ----------
        preset_hex: str
            The hex representation of the desired preset mode.
        """
        # Always ensure the socket is connected before sending
        await self.async_connect()
        try:
            # The write payload for changing preset is 011e01 followed by
            # the preset code.  See Trame documentation for details.
            frame = Trame("6400", "0100", "29", "a9", "011e01", preset_hex).build()
            await self.async_send(frame, "a9")
        finally:
            await self.async_disconnect()

    async def async_set_setpoint(self, code: str, temperature: float) -> None:
        """Set the target temperature on the controller.

        The controller expects a 4‑byte floating point value encoded
        little‑endian.  The ``code`` parameter selects the function code
        used for the write (either ``"012001"`` or ``"012101"`` depending
        on the operating mode).  Connection management is handled
        internally.

        Parameters
        ----------
        code: str
            The 6‑digit hex string representing the write command code.
        temperature: float
            The new setpoint temperature to apply.
        """
        await self.async_connect()
        try:
            # Pack the float into a 32‑bit little‑endian representation
            value_hex = struct.pack("<f", float(temperature)).hex()
            frame = Trame("6400", "0100", "29", "a9", code, value_hex).build()
            await self.async_send(frame, "a9")
        finally:
            await self.async_disconnect()

    async def async_get_thermostat(self) -> Optional[Dict[str, object]]:
        """Read the thermostat state from the controller.

        This convenience method constructs a request frame using the
        definitions in :mod:`parameters` and decodes the response into
        a dictionary.  It handles opening and closing the connection
        internally.

        Returns
        -------
        dict or None
            The decoded thermostat values, or ``None`` if no response
            was received.
        """
        await self.async_connect()
        try:
            # Build the frame for GET_THERMOSTAT.  According to the protocol
            # this uses DA=6400, SA=2000, F=40 and a data payload of 647800.
            request_frame = Trame("6400", "2000", "40", "c0", "647800", "").build()
            param_info = PARAMETER.get("GET_THERMOSTAT")
            data_to_search = param_info.get("dataToSearch") if param_info else ""
            return await self.async_request(request_frame, THERMOSTAT, data_to_search, "c0")
        finally:
            await self.async_disconnect()

    async def listen_frame(self, param: str, *, max_tries: int = 100) -> Optional[Dict[str, object]]:
        """Listen for unsolicited frames matching a parameter definition.

        Many EcoMAX controllers broadcast frames without being polled.  To
        extract values from these broadcasts, this method repeatedly reads
        from the socket, splits the data into individual frames and looks
        for a frame whose hexadecimal representation contains the
        ``dataToSearch`` marker defined in :mod:`~custom_components.ecomax360.api.parameters`
        for ``param``.  When such a frame is found, it is decoded using
        the appropriate data structure and returned.

        Parameters
        ----------
        param: str
            The key of the parameter as defined in :data:`PARAMETER`.  For
            example ``"GET_DATAS"`` or ``"GET_THERMOSTAT"``.
        max_tries: int, optional
            The maximum number of read attempts to perform.  Defaults to
            100.  Each attempt reads up to 1024 bytes from the socket.

        Returns
        -------
        dict or None
            A dictionary of decoded values if a matching frame is found,
            otherwise ``None``.
        """
        if param not in PARAMETER:
            _LOGGER.warning("Unknown parameter '%s' passed to listen_frame", param)
            return None
        param_info = PARAMETER[param]
        data_struct = param_info["dataStruct"]
        data_to_search = param_info.get("dataToSearch")
        # Some parameter definitions specify a fixed length for the frame in
        # bytes; if present we can use it to filter frames quickly.  The
        # length value is the total number of *bytes* of the frame, but
        # since our incoming data is a hex string each byte corresponds to
        # two characters.  We therefore multiply by 2 to obtain the length
        # in hexadecimal characters.
        expected_length = param_info.get("length")
        if expected_length is not None:
            expected_hex_length = expected_length * 2
        else:
            expected_hex_length = None

        tries = 0
        while tries < max_tries:
            # Attempt to connect if not already connected
            await self.async_connect()
            frames_hex = await self._async_recv_hex()
            # find all potential frames in the data
            frames = re.findall(r"68.*?16", frames_hex)
            for resp_hex in frames:
                # If we know the expected length, skip frames that don't match
                if expected_hex_length is not None and len(resp_hex) != expected_hex_length:
                    continue
                if data_to_search and data_to_search not in resp_hex:
                    continue
                # decode and return
                return extract_data(resp_hex, data_struct)
            tries += 1
        _LOGGER.debug(
            "No broadcast frame found for parameter '%s' after %d attempts", param, max_tries
        )
        return None