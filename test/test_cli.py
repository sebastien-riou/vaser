import subprocess
import sys

from test.common import parse_test_args


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-m', 'vaser', *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_encode_then_decode_same_as_c():
    encode = _run_cli(['encode', '010203', 'fragment', '0a0b0c', 'last'])
    assert encode.returncode == 0, encode.stderr
    encoded_hex = encode.stdout.strip()
    assert encoded_hex

    decode = _run_cli(['decode', encoded_hex])
    assert decode.returncode == 0, decode.stderr
    assert decode.stdout.strip() == '010203 fragment 0a0b0c last'


def test_encode_then_decode_with_granularity():
    encode = _run_cli(['encode', '--granularity', '4', '0102', 'last'])
    assert encode.returncode == 0, encode.stderr
    encoded_hex = encode.stdout.strip()
    assert encoded_hex

    decode = _run_cli(['decode', '--granularity', '4', encoded_hex])
    assert decode.returncode == 0, decode.stderr
    assert decode.stdout.strip() == '0102 last'

def test_encode_then_decode_with_granularity_8():
    encode = _run_cli(['encode', '--granularity', '8', '0001020304', 'null', '05'])
    assert encode.returncode == 0, encode.stderr
    encoded_hex = encode.stdout.strip()
    assert encoded_hex

    decode = _run_cli(['decode', '--granularity', '8', encoded_hex])
    assert decode.returncode == 0, decode.stderr
    assert decode.stdout.strip() == '0001020304 null 05'


def test_it():
    test_encode_then_decode_same_as_c()
    test_encode_then_decode_with_granularity()
    test_encode_then_decode_with_granularity_8()


if __name__ == '__main__':
    parse_test_args()
    test_it()
