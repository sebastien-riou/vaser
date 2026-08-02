from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Copy bytes from stdin to a serial device or file.'
    )
    parser.add_argument(
        '--baud',
        type=int,
        help='Specify the baudrate to use for the serial device.',
    )
    parser.add_argument(
        'device',
        help='Path to the output serial device.',
    )
    return parser.parse_args(argv)


def _open_output(device: str, baud: int | None):
    if baud is None:
        return Path(device).open('wb')

    try:
        import serial
    except ImportError as exc:
        raise RuntimeError(
            'pyserial is required when --baud is specified: install pyserial or omit --baud'
        ) from exc

    return serial.Serial(device, baudrate=baud)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    with _open_output(args.device, args.baud) as output:
        shutil.copyfileobj(sys.stdin.buffer, output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
