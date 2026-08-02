from __future__ import annotations

import argparse
import subprocess
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Check interoperability between C and Python Vaser CLI implementations.'
    )
    parser.add_argument(
        '--c-impl',
        default='./test-vaser',
        help='Path to the C implementation executable (default: ./test-vaser).',
    )
    parser.add_argument(
        '--granularity',
        type=int,
        default=1,
        help='Write/read granularity for padding when flags are not DEFAULT.',
    )
    parser.add_argument(
        'values',
        nargs='+',
        help='Payload bytes in hex or markers null/next/fragment/last.',
    )
    return parser.parse_args()


def _run_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\n"
            f"exit code: {result.returncode}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _build_command(base: str, granularity: int, values: list[str]) -> list[str]:
    command = [base]
    if granularity != 1:
        command.extend(['--granularity', str(granularity)])
    command.append('encode')
    command.extend(values)
    return command


def _build_decode_command(base: str, granularity: int, encoded: str) -> list[str]:
    command = [base]
    if granularity != 1:
        command.extend(['--granularity', str(granularity)])
    command.extend(['decode', encoded])
    return command


def main() -> int:
    args = _parse_args()
    c_encode_cmd = _build_command(args.c_impl, args.granularity, args.values)
    py_encode_cmd = [sys.executable, '-m', 'vaser'] + c_encode_cmd[1:]

    c_output = _run_command(c_encode_cmd)
    py_output = _run_command(py_encode_cmd)

    if c_output != py_output:
        print('ERROR: C and Python encode outputs differ.', file=sys.stderr)
        print(f'C output: {c_output}', file=sys.stderr)
        print(f'Python output: {py_output}', file=sys.stderr)
        return 1

    print(f'Encoded output: {c_output}')

    expected_decoded = ' '.join(args.values)
    if args.values[-1] not in ('next', 'last', 'fragment'):
        expected_decoded += ' next'

    c_decode_cmd = _build_decode_command(args.c_impl, args.granularity, c_output)
    py_decode_cmd = [sys.executable, '-m', 'vaser'] + _build_decode_command('vaser', args.granularity, c_output)[1:]

    c_decoded = _run_command(c_decode_cmd)
    py_decoded = _run_command(py_decode_cmd)

    if c_decoded != expected_decoded:
        print('ERROR: C decode output does not match original values.', file=sys.stderr)
        print(f'Expected: {expected_decoded}', file=sys.stderr)
        print(f'C decoded: {c_decoded}', file=sys.stderr)

    if py_decoded != expected_decoded:
        print('ERROR: Python decode output does not match original values.', file=sys.stderr)
        print(f'Expected: {expected_decoded}', file=sys.stderr)
        print(f'Python decoded: {py_decoded}', file=sys.stderr)

    if c_decoded != expected_decoded or py_decoded != expected_decoded:
        return 1

    print(f'Decoded: {c_decoded}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
