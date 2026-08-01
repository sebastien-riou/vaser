"""Command-line interface for the vaser package."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from vaser import Vaser, VaserFlags

_MARKERS = {
    'next': VaserFlags.LAST_IN_CHUNK,
    'fragment': VaserFlags.FRAGMENT,
    'last': VaserFlags.LAST_IN_LIST,
}


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('granularity must be an integer') from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError('granularity must be >= 1')
    return parsed


def _encode_args(args: Sequence[str], granularity: int) -> bytes:
    result = bytearray()

    chunk = Vaser(granularity=granularity)
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == 'null':
            payload = b''
        else:
            payload = bytes.fromhex(arg)

        flags = VaserFlags.DEFAULT
        if i + 1 < len(args):
            if args[i + 1] in _MARKERS:
                flags = _MARKERS[args[i + 1]]
                i += 1
        else:
            flags = VaserFlags.LAST_IN_CHUNK

        chunk.add([payload], flags=flags)

        if flags != VaserFlags.DEFAULT:
            result.extend(chunk.as_bytes)
            chunk = Vaser(granularity=granularity)

        i += 1

    return bytes(result)


def _decode_args(args: Sequence[str], granularity: int) -> str:
    output_parts: list[str] = []
    for arg in args:
        data = bytes.fromhex(arg)
        while data:
            chunk, consumed = Vaser.decode(data, granularity=granularity)
            for value in chunk.args:
                if value:
                    output_parts.append(value.hex())
                else:
                    output_parts.append('null')

            if chunk.flags == VaserFlags.LAST_IN_LIST:
                output_parts.append('last')
            elif chunk.flags == VaserFlags.FRAGMENT:
                output_parts.append('fragment')
            elif chunk.flags == VaserFlags.LAST_IN_CHUNK and data[consumed:]:
                output_parts.append('next')

            data = data[consumed:]
    return ' '.join(output_parts)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='vaser', description='Encode or decode Vaser chunks.')
    parser.add_argument('--granularity', type=_positive_int, default=1, help='Write/read granularity for padding when flags are not DEFAULT.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    encode_parser = subparsers.add_parser('encode', help='Encode Vaser chunks from hexadecimal payloads.')
    encode_parser.add_argument('values', nargs='+', help='Payload bytes in hex or markers null/next/fragment/last.')

    decode_parser = subparsers.add_parser('decode', help='Decode Vaser chunks from hexadecimal encoded chunks.')
    decode_parser.add_argument('values', nargs='+', help='Chunk bytes in hex.')

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == 'encode':
        sys.stdout.write(_encode_args(args.values, args.granularity).hex() + '\n')
        return 0

    sys.stdout.write(_decode_args(args.values, args.granularity) + '\n')
    return 0
