from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vaser.cli import _encode_args, _positive_int


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Encode arguments using the Vaser CLI encoding format and write the encoded bytes to stdout or a serial device.'
    )
    parser.add_argument(
        '--granularity',
        type=_positive_int,
        default=1,
        help='Write granularity for padding when flags are not DEFAULT.',
    )
    parser.add_argument(
        '--device',
        help='Path to a serial device. Output will be written to this device instead of stdout.',
    )
    parser.add_argument(
        'values',
        nargs='+',
        help='Payload bytes in hex or markers null/next/fragment/last.',
    )
    return parser.parse_args(argv)


def _open_output(device: str):
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError(
            'pyserial is required when --device is specified: install pyserial'
        ) from exc

    return serial.Serial(device, timeout=None)


def _write_output(data: bytes, device: str | None) -> None:
    if device is None:
        sys.stdout.buffer.write(data)
        return

    with _open_output(device) as output:
        output.write(data)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    encoded = _encode_args(args.values, args.granularity)
    _write_output(encoded, args.device)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
