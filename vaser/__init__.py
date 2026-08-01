"""Compact VLQ-style serialization helpers for Vaser chunk framing."""

from __future__ import annotations

import enum
from typing import Iterable, Union


class VaserInvalidFlagsError(RuntimeError):
    """Raised when invalid Vaser flags are encountered."""

    pass


class VaserFlags(enum.IntEnum):
    DEFAULT = 0
    FRAGMENT = 1
    LAST_IN_CHUNK = 2
    LAST_IN_LIST = 3


def _vlq_encode(value: int) -> bytes:
    if value < 0:
        raise ValueError('value must be non-negative')
    if value == 0:
        return b'\x00'

    parts: list[int] = []
    while value > 0:
        byte = value & 0x7F
        value >>= 7
        if value:
            byte |= 0x80
        parts.append(byte)
    return bytes(parts)


def _vlq_decode(data: bytes) -> tuple[int, int]:
    value = 0
    shift = 0
    consumed = 0
    for byte in data:
        consumed += 1
        value |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            return value, consumed
        shift += 7
        if shift >= 64:
            raise ValueError('VLQ too large')
    raise ValueError('incomplete VLQ')


def _encode_tl(payload_size: int, flags: VaserFlags) -> bytes:
    tl = (payload_size << 2) | int(flags)
    return _vlq_encode(tl)


def _decode_tl(data: bytes) -> tuple[int, VaserFlags, int]:
    tl, consumed = _vlq_decode(data)
    try:
        flags = VaserFlags(tl & 3)
    except ValueError as exc:
        raise VaserInvalidFlagsError(tl & 3) from exc
    payload_size = tl >> 2
    return payload_size, flags, consumed


def _normalize_payload(payload: Union[bytes, bytearray, memoryview, Iterable[bytes]]) -> tuple[list[bytes], bytes]:
    if isinstance(payload, (bytes, bytearray, memoryview)):
        data = bytes(payload)
        return [data], data
    if isinstance(payload, str):
        raise TypeError('payload must be bytes-like or an iterable of bytes-like values')

    values: list[bytes] = []
    pieces: list[bytes] = []
    for item in payload:
        if isinstance(item, (bytes, bytearray, memoryview)):
            piece = bytes(item)
            values.append(piece)
            pieces.append(piece)
        else:
            raise TypeError('each payload item must be bytes-like')
    data = b''.join(pieces)
    return values, data


def _encode_values(payload: bytes) -> bytes:
    return payload


def _decode_values(data: bytes) -> list[bytes]:
    return [data]


class Vaser:
    def __init__(self, args: Union[bytes, bytearray, memoryview, Iterable[bytes]], *, flags: Union[VaserFlags, int] = VaserFlags.DEFAULT, granularity: int = 1):
        self._args, self._payload = _normalize_payload(args)
        try:
            self.flags = VaserFlags(flags)
        except ValueError as exc:
            raise VaserInvalidFlagsError(flags) from exc

        if granularity < 1:
            raise ValueError('granularity must be >= 1')
        self.granularity = granularity

    @property
    def payload(self) -> bytes:
        return self._payload

    @property
    def args(self) -> list[bytes]:
        return self._args[:]

    @property
    def fragment(self) -> bool:
        return self.flags == VaserFlags.FRAGMENT

    @property
    def last_in_chunk(self) -> bool:
        return self.flags == VaserFlags.LAST_IN_CHUNK

    @property
    def last_in_list(self) -> bool:
        return self.flags == VaserFlags.LAST_IN_LIST

    @property
    def as_bytes(self) -> bytes:
        encoded: bytes = b''
        total_args = len(self._args)
        for index, arg in enumerate(self._args):
            flags = self.flags if index == total_args - 1 else VaserFlags.DEFAULT
            encoded += _encode_tl(len(arg), flags) + arg

        if self.granularity > 1:
            remainder = len(encoded) % self.granularity
            if remainder:
                padding = self.granularity - remainder
                encoded += b'\x00' * padding
        return encoded

    @classmethod
    def decode(cls, data: bytes, *, granularity: int = 1) -> tuple['Vaser', int]:
        consumed = 0
        args: list[bytes] = []
        flags = VaserFlags.DEFAULT

        while consumed < len(data):
            payload_size, flags, header_size = _decode_tl(data[consumed:])
            payload_start = consumed + header_size
            payload_end = payload_start + payload_size
            if len(data) < payload_end:
                raise ValueError('not enough data to decode payload')

            args.append(data[payload_start:payload_end])
            consumed = payload_end

            if flags != VaserFlags.DEFAULT:
                break
            if consumed == len(data):
                break

        if granularity > 1:
            remainder = consumed % granularity
            if remainder:
                padded_end = consumed + (granularity - remainder)
                if len(data) < padded_end:
                    raise ValueError('not enough data to decode padded payload')
                if any(byte != 0 for byte in data[consumed:padded_end]):
                    raise ValueError('invalid padding')
                consumed = padded_end

        return cls(args, flags=flags, granularity=granularity), consumed

    def __repr__(self) -> str:
        return f'Vaser(flags={self.flags.name}, payload={self._payload!r}, granularity={self.granularity})'


from vaser.cli import main


if __name__ == '__main__':
    raise SystemExit(main())
