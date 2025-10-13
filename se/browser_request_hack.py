# Copyright 2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

# This function is imported from urllib3 and monkey-patched to avoid https://github.com/urllib3/urllib3/issues/3081
# MIT License
# Copyright (c) 2008-2020 Andrey Petrov and contributors.

# Detect urllib3 version for backward compatibility
try:
    import urllib3

    URLLIB3_VERSION_MAJOR = int(urllib3.__version__.split(".")[0])
except (ImportError, AttributeError, ValueError, IndexError):
    URLLIB3_VERSION_MAJOR = 1

# Import the appropriate modules based on urllib3 version
if URLLIB3_VERSION_MAJOR < 2:
    # urllib3 1.x compatibility (old API)
    import six
    from urllib3.util.url import PERCENT_RE

    def _encode_invalid_chars(component, allowed_chars, encoding="utf-8"):
        """Percent-encodes a URI component without reapplying onto an already
        percent-encoded component."""
        if component is None:
            return component

        component = six.ensure_text(component)

        # Normalize existing percent-encoded bytes.
        # Try to see if the component we're encoding is already percent-encoded
        # so we can skip all '%' characters but still encode all others.
        component, percent_encodings = PERCENT_RE.subn(lambda match: match.group(0), component)

        uri_bytes = component.encode("utf-8", "surrogatepass")
        is_percent_encoded = percent_encodings == uri_bytes.count(b"%")
        encoded_component = bytearray()

        for i in range(0, len(uri_bytes)):
            # Will return a single character bytestring on both Python 2 & 3
            byte = uri_bytes[i : i + 1]
            byte_ord = ord(byte)
            if (is_percent_encoded and byte == b"%") or (byte_ord < 128 and byte.decode() in allowed_chars):
                encoded_component += byte
                continue
            encoded_component.extend(b"%" + (hex(byte_ord)[2:].encode().zfill(2).upper()))

        return encoded_component.decode(encoding)

else:
    # urllib3 2.x+ (new API)
    import typing

    from urllib3.util.url import _PERCENT_RE
    from urllib3.util.util import to_str

    def _encode_invalid_chars(component: str | None, allowed_chars: typing.Container[str]) -> str | None:
        """Percent-encodes a URI component without reapplying onto an already
        percent-encoded component."""
        if component is None:
            return component

        component = to_str(component)

        # Normalize existing percent-encoded bytes.
        # Try to see if the component we're encoding is already percent-encoded
        # so we can skip all '%' characters but still encode all others.
        component, percent_encodings = _PERCENT_RE.subn(lambda match: match.group(0), component)

        uri_bytes = component.encode("utf-8", "surrogatepass")
        is_percent_encoded = percent_encodings == uri_bytes.count(b"%")
        encoded_component = bytearray()

        for i in range(0, len(uri_bytes)):
            # Will return a single character bytestring
            byte = uri_bytes[i : i + 1]
            byte_ord = ord(byte)
            if (is_percent_encoded and byte == b"%") or (byte_ord < 128 and byte.decode() in allowed_chars):
                encoded_component += byte
                continue
            encoded_component.extend(b"%" + (hex(byte_ord)[2:].encode().zfill(2).upper()))

        return encoded_component.decode()
