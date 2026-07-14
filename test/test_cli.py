import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_encode_decode_round_trip(tmp_path):
    encoded_path = tmp_path / 'payload.bin'
    output_path = tmp_path / 'decoded.txt'

    encode_result = subprocess.run(
        [
            sys.executable,
            '-m',
            'vaser',
            'encode',
            '4',
            '13',
            '--fragment',
            '--last',
            '--output',
            str(encoded_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert encode_result.returncode == 0, encode_result.stderr
    assert encoded_path.exists()

    decode_result = subprocess.run(
        [
            sys.executable,
            '-m',
            'vaser',
            'decode',
            '--input',
            str(encoded_path),
            '--output',
            str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert decode_result.returncode == 0, decode_result.stderr
    assert output_path.exists()
    assert output_path.read_text().strip() == '4 13'
