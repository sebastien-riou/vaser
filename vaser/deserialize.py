from __future__ import annotations

import argparse
import os
import pty
import sys
from pathlib import Path

from vaser import Vaser, VaserFlags
from vaser.cli import _positive_int


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Decode Vaser bytes from stdin or a serial device and print decoded arguments to stdout.'
    )
    parser.add_argument(
        '--granularity',
        type=_positive_int,
        default=1,
        help='Read granularity for padding when flags are not DEFAULT.',
    )
    parser.add_argument(
        '--device',
        help='Path to a serial device or symlink path when --pts is used.',
    )
    parser.add_argument(
        '--baud',
        type=int,
        help='Specify the baudrate to use for the serial device.',
    )
    parser.add_argument(
        '--pts',
        action='store_true',
        help='Create a pts device and symlink at the given device path.',
    )
    return parser.parse_args(argv)


def _open_pts_input(link_path: str) -> tuple[object, int, Path]:
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


def _open_input(device: str, baud: int | None):
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError(
            'pyserial is required when --device is specified: install pyserial'
        ) from exc

    return serial.Serial(device, baudrate=baud, timeout=None)


def _decode_stream_from_stream(stream, granularity: int) -> None:
    buffer = bytearray()
    first_token = True

    while True:
        chunk = stream.read(1)
        if not chunk:
            break

        buffer.extend(chunk)
        while len(buffer) > 0:
            try:
                #print(f"Buffer: {buffer.hex()}")  # Debugging line to check buffer length
                vaser_chunk, consumed = Vaser.decode(bytes(buffer), granularity=granularity)
            except ValueError:
                break

            output_parts: list[str] = []
            for value in vaser_chunk.args:
                output_parts.append(value.hex() if value else 'null')

            new_line = False
            if vaser_chunk.flags == VaserFlags.LAST_IN_LIST:
                output_parts.append('last')
                new_line = True
            elif vaser_chunk.flags == VaserFlags.FRAGMENT:
                output_parts.append('fragment')
            elif vaser_chunk.flags == VaserFlags.LAST_IN_CHUNK:
                output_parts.append('next')

            for token in output_parts:
                if not first_token:
                    sys.stdout.write(' ')
                sys.stdout.write(token)
                first_token = False
            if new_line:
                sys.stdout.write('\n')
                first_token = True
            buffer = buffer[consumed:]

    if buffer:
        raise RuntimeError('EOF reached before a complete Vaser frame was received')

    if not first_token:
        sys.stdout.write('\n')


def _open_input_stream(device: str | None, baud: int | None, pts: bool) -> tuple[object, int | None, Path | None]:
    if pts:
        if device is None:
            raise ValueError('--pts requires a device symlink path')
        return _open_pts_input(device)

    if device is not None:
        return _open_input(device, baud), None, None

    return sys.stdin.buffer, None, None


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    input_data: bytes
    slave_fd: int | None = None
    symlink_path: Path | None = None
    stream = None
    try:
        stream, slave_fd, symlink_path = _open_input_stream(
            args.device, args.baud, args.pts
        )
        _decode_stream_from_stream(stream, args.granularity)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        if stream is not None and stream is not sys.stdin.buffer:
            try:
                stream.close()
            except Exception:
                pass
        if slave_fd is not None:
            try:
                os.close(slave_fd)
            except Exception:
                pass
        if symlink_path is not None and symlink_path.is_symlink():
            symlink_path.unlink()


if __name__ == '__main__':
    raise SystemExit(main())
