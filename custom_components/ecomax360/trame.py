"""Utility for constructing EcoMAX protocol frames.

This module defines the :class:`Trame` class which is responsible for
assembling binary frames understood by the EcoMAX controller.  A frame
encapsulates a command or request and includes addressing, a function
code, optional data payload and a CRC checksum.  Frames begin with
the start byte ``0x68`` and end with the delimiter ``0x16``.  The
payload layout is based on the reverse‑engineered protocol used by
Plum EcoMAX devices.

The :class:`Trame` class does not transmit the frame; it simply
prepares the bytes.  Use :class:`~custom_components.ecomax360.api.client.EcoMaxClient`
to send the built frames to the device.

Example
-------

To build a frame that writes a preset value to the controller::

    from custom_components.ecomax360.trame import Trame

    trame = Trame("6400", "0100", "29", "a9", "011e01", "00")
    frame_bytes = trame.build()
    # Use EcoMaxClient.async_send() to transmit frame_bytes

The length and CRC are computed automatically.  All values passed
should be hexadecimal strings (without the ``0x`` prefix) representing
two bytes (for addresses) or an arbitrary number of bytes for the
payload.  See the ``__init__`` docstring for details.
"""

from __future__ import annotations

import logging
from typing import Tuple

from .utils import int16_to_hex
from .api.parameters import SET_CODE

_LOGGER = logging.getLogger(__name__)


class Trame:
    """Represents a single EcoMAX protocol frame.

    Parameters
    ----------
    dest: str
        The destination address (DA) as a four‑character hex string
        (e.g. ``"6400"``).  The first two characters form ``DA0`` and
        the last two form ``DA1``.
    source: str
        The source address (SA) as a four‑character hex string
        (e.g. ``"0100"``).  As with ``dest``, the first two characters
        form ``SA0`` and the last two form ``SA1``.
    f: str
        The function code as a two‑character hex string.  For example,
        ``"29"`` indicates a write command and ``"40"`` a read command.
    ack_f: str
        The acknowledgement flag expected in responses, as a
        two‑character hex string.  This value is not used when
        constructing the frame but is stored for completeness.
    param: str
        The command or parameter identifier.  When sending a write
        command (``f == "29"``), this should be appended to the
        ``SET_CODE`` constant and ``value_hex`` to form the data field.
        For a read request, this string alone becomes the data field.
    value_hex: str
        Additional payload appended when sending a write command.  This
        should be a hex string representing the value to write.  It
        should not include any spaces.

    Notes
    -----
    The length of the frame (``L0 L1``) is computed automatically
    based on the sizes of the destination and source addresses, the
    function code and the data payload.  The checksum is computed
    using the CRC‑CCITT (XModem) algorithm.  Both the length and the
    CRC are inserted into the final frame when :meth:`build` is called.
    """

    def __init__(self, dest: str, source: str, f: str, ack_f: str, param: str, value_hex: str) -> None:
        self.da0: str = dest[:2]
        self.da1: str = dest[2:]
        self.sa0: str = source[:2]
        self.sa1: str = source[2:]
        self.f: str = f
        # The ack flag is not encoded into the frame but retained for
        # external users (e.g. EcoMaxClient) when waiting for responses.
        self.ack_f: str = ack_f
        # Compose the data field.  For write commands (function "29")
        # prepend the SET_CODE constant and the param and value; for
        # read commands use the parameter alone.
        if self.f == "29":
            # Include a space between each component for readability
            self.data: str = f"{SET_CODE} {param} {value_hex}"
        else:
            self.data = param
        # Compute the length bytes (L0 L1) upon initialisation
        self.l0, self.l1 = self.calculate_length()

    def calculate_length(self) -> Tuple[str, str]:
        """Compute the length bytes (L0 L1) for this frame.

        The length is the total number of *bytes* in the fields
        following the length itself (i.e. SA, DA, F and DATA).  DA and
        SA are each two bytes, the function code is one byte and the
        data field is variable.  This method returns the length as two
        one‑byte hex strings (little‑endian order: L0 = low byte, L1 = high
        byte).

        Returns
        -------
        tuple(str, str)
            A pair ``(L0, L1)`` where each element is a two‑character
            hex string.
        """
        # Each address component (DA and SA) is two bytes; function is one
        size_da = 2
        size_sa = 2
        size_f = 1
        # Convert the data field into bytes to determine its length
        size_data = len(bytes.fromhex(self.data))
        total_size = size_da + size_sa + size_f + size_data
        # Convert to little endian hex (4 characters)
        length_hex = int16_to_hex(total_size)
        # length_hex returns a 4‑character little endian hex string
        return length_hex[:2], length_hex[2:]

    def build(self) -> bytes:
        """Assemble the complete frame and return it as bytes.

        The frame consists of the start delimiter (0x68), the length
        bytes (L0 L1), the source address (SA0 SA1), destination
        address (DA0 DA1), function code, data payload, a two‑byte CRC
        and the end delimiter (0x16).  Internal spaces in the data
        field are removed when converting to bytes.

        Returns
        -------
        bytes
            The binary representation of the complete frame ready for
            transmission.
        """
        # Build the frame fields into a single hex string (without start/end)
        trame_crc_hex = f"{self.l0} {self.l1} {self.sa0} {self.sa1} {self.da0} {self.da1} {self.f} {self.data}"
        trame_crc_bytes = bytes.fromhex(trame_crc_hex)
        # Compute CRC over the above bytes
        crc_bytes = self.calculate_crc(trame_crc_bytes)
        # Construct full frame with start (68) and end (16) delimiters
        trame_hex = f"68 {trame_crc_hex} {crc_bytes.hex()} 16"
        return bytes.fromhex(trame_hex)

    @staticmethod
    def calculate_crc(data: bytes) -> bytes:
        """Compute the CRC‑CCITT (XModem) checksum for a sequence of bytes.

        The CRC is computed over the fields from L0 up to the end of the
        data payload.  The resulting 16‑bit integer is encoded as two
        bytes in big‑endian order.  See the EcoMAX protocol for
        further details.

        Parameters
        ----------
        data: bytes
            The data over which to compute the CRC.

        Returns
        -------
        bytes
            A two‑byte big‑endian representation of the CRC.
        """
        crc = 0x0000
        poly = 0x1021
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc.to_bytes(2, "big")
