"""Command-line interface for the vaser package."""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from vaser import Vaser


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser for encode/decode commands."""
    parser = argparse.ArgumentParser(prog='vaser', description='Encode and decode integer values with Vaser.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    encode_parser = subparsers.add_parser('encode', help='Encode integer values to bytes')
    encode_parser.add_argument('values', nargs='+', help='Integer values to encode, or the trailing keywords fragment/last')
    encode_parser.add_argument('--fragment', action='store_true', help='Set the fragment flag')
    encode_parser.add_argument('--last', action='store_true', help='Set the last flag')
    encode_parser.add_argument('--hex', action='store_true', help='Output or consume hexadecimal text instead of binary data')
    encode_parser.add_argument('--output', type=Path, help='Write encoded bytes to a binary file instead of stdout')

    decode_parser = subparsers.add_parser('decode', help='Decode bytes back to integer values')
    decode_parser.add_argument('--input', type=Path, help='Read encoded bytes from a binary file instead of stdin')
    decode_parser.add_argument('--hex', action='store_true', help='Read hexadecimal text instead of binary data')
    decode_parser.add_argument('--hex-in', help='Decode a hexadecimal string provided directly as an argument')
    decode_parser.add_argument('--output', type=Path, help='Write decoded values to a text file instead of stdout')

    return parser


def _read_input_bytes(input_path: Optional[Path], *, as_hex: bool) -> bytes:
    """Read bytes from stdin or from a file path, optionally as hexadecimal text."""
    if input_path is None:
        if as_hex:
            data = sys.stdin.readline()
        else:
            data = sys.stdin.buffer.read()
    else:
        data = input_path.read_bytes()

    if not as_hex:
        return data

    text = data.decode('utf-8').strip() if isinstance(data, (bytes, bytearray)) else str(data).strip()
    if not text:
        return b''
    return bytes.fromhex(text)


def _write_output_bytes(payload: bytes, output_path: Optional[Path], *, as_hex: bool) -> None:
    """Write bytes to stdout or a file path, optionally as hexadecimal text."""
    if as_hex:
        text = payload.hex()
        if output_path is None:
            sys.stdout.write(text)
        else:
            output_path.write_text(text)
        return

    if output_path is None:
        sys.stdout.buffer.write(payload)
        return
    output_path.write_bytes(payload)


def _write_output_text(payload: str, output_path: Optional[Path]) -> None:
    """Write text to stdout or a file path."""
    if output_path is None:
        sys.stdout.write(payload)
        return
    output_path.write_text(payload)


def _parse_encode_values(values: Sequence[str]) -> list[tuple[list[int], bool, bool]]:
    """Parse CLI values into one or more chunks delimited by fragment/last markers."""
    chunks: list[tuple[list[int], bool, bool]] = []
    current_values: list[int] = []
    current_fragment = False
    current_last = False

    def flush_chunk() -> None:
        if current_values or current_fragment or current_last:
            chunks.append((current_values[:], current_fragment, current_last))

    for value in values:
        if value == 'fragment':
            flush_chunk()
            current_values = []
            current_fragment = True
            current_last = False
        elif value == 'last':
            flush_chunk()
            current_values = []
            current_fragment = False
            current_last = True
        else:
            current_values.append(int(value))

    flush_chunk()
    return chunks


def _run_encode(values: Sequence[str], *, fragment: bool, last: bool, output_path: Optional[Path], as_hex: bool) -> int:
    """Encode provided values and emit them as bytes or hexadecimal text."""
    chunks = _parse_encode_values(values)
    if fragment:
        chunks = [(values, True, False) for values, _, _ in chunks] if not chunks else [(values, True, False) for values, _, _ in chunks]
    if last:
        chunks = [(values, False, True) for values, _, _ in chunks] if not chunks else [(values, False, True) for values, _, _ in chunks]

    payloads = []
    for parsed_values, parsed_fragment, parsed_last in chunks:
        chunk = Vaser(parsed_values, fragment=parsed_fragment if parsed_fragment else None, last=parsed_last if parsed_last else None)
        payloads.append(chunk.as_bytes)

    if output_path is None:
        if as_hex:
            sys.stdout.write(''.join(payload.hex() for payload in payloads))
            sys.stdout.write('\n')
        else:
            for payload in payloads:
                sys.stdout.buffer.write(payload)
    else:
        output_bytes = b''.join(payloads)
        if as_hex:
            output_path.write_text(output_bytes.hex())
        else:
            output_path.write_bytes(output_bytes)
    return 0


def _run_decode(input_path: Optional[Path], output_path: Optional[Path], as_hex: bool, hex_in: Optional[str]) -> int:
    """Decode bytes from stdin, a file, or a supplied hex string and emit values as text."""
    if hex_in is not None:
        payload = bytes.fromhex(hex_in)
    else:
        payload = _read_input_bytes(input_path, as_hex=as_hex)
    decoded, _ = Vaser.decode(payload)
    values_text = ' '.join(str(value) for value in decoded.args)
    suffixes = []
    if decoded.fragment:
        suffixes.append('fragment')
    if decoded.last:
        suffixes.append('last')
    text = values_text if not suffixes else f'{values_text} {" ".join(suffixes)}'
    _write_output_text(text, output_path)
    if output_path is None:
        sys.stdout.write('\n')
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the package entry point for the CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == 'encode':
        return _run_encode(args.values, fragment=args.fragment, last=args.last, output_path=args.output, as_hex=args.hex)
    if args.command == 'decode':
        return _run_decode(args.input, args.output, as_hex=args.hex, hex_in=args.hex_in)
    parser.error('Unknown command')
    return 2
