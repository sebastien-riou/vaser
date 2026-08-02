from __future__ import annotations

import argparse
import os
import pty
import shutil
import sys
from pathlib import Path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Copy bytes from an input serial device to stdout.'
    )
    parser.add_argument(
        '--baud',
        type=int,
        help='Specify the baudrate to use for the serial device.',
    )
    parser.add_argument(
        '--pts',
        action='store_true',
        help='Create a pts device and create a symlink at the given device path.',
    )
    parser.add_argument(
        'device',
        help='Path to the input serial device.',
    )
    return parser.parse_args(argv)


def _open_physical_device(device: str, baud: int | None):
    if baud is None:
        return open(device, 'rb')

    try:
        import serial
    except ImportError as exc:
        raise RuntimeError(
            'pyserial is required when --baud is specified: install pyserial or omit --baud'
        ) from exc

    return serial.Serial(device, baudrate=baud, timeout=None)


def _open_pts_device(link_path: str) -> tuple[object, int, Path]:
    master_fd, slave_fd = pty.openpty()
    slave_path = Path(os.ttyname(slave_fd))

    symlink_path = Path(link_path)
    if symlink_path.exists() or symlink_path.is_symlink():
        os.close(master_fd)
        os.close(slave_fd)
        raise FileExistsError(f'{symlink_path} already exists')

    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    symlink_path.symlink_to(slave_path)

    return os.fdopen(master_fd, 'rb', closefd=True), slave_fd, symlink_path


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    symlink_path: Path | None = None
    slave_fd: int | None = None
    input_stream = None

    try:
        if args.pts:
            input_stream, slave_fd, symlink_path = _open_pts_device(args.device)
        else:
            input_stream = _open_physical_device(args.device, args.baud)

        try:
            while True:
                b = input_stream.read(1)
                #print(f"Read byte: {b.hex() if b else 'EOF'}")  # Debugging line to check read bytes
                if not b:
                    break
                sys.stdout.buffer.write(b)
                sys.stdout.buffer.flush()
        except KeyboardInterrupt:
            return 0
    finally:
        if input_stream is not None:
            try:
                input_stream.close()
            except Exception:
                pass
        if slave_fd is not None:
            try:
                os.close(slave_fd)
            except Exception:
                pass
        if symlink_path is not None and symlink_path.is_symlink():
            symlink_path.unlink()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
