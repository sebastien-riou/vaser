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
    assert output_path.read_text().strip() == '4 13 fragment'


def test_hex_encode_decode_round_trip():
    encode_result = subprocess.run(
        [sys.executable, '-m', 'vaser', 'encode', '4', '13', '--hex'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert encode_result.returncode == 0, encode_result.stderr
    assert encode_result.stdout.strip()

    decode_result = subprocess.run(
        [sys.executable, '-m', 'vaser', 'decode', '--hex'],
        cwd=REPO_ROOT,
        input=encode_result.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    assert decode_result.returncode == 0, decode_result.stderr
    assert decode_result.stdout.strip() == '4 13 next'


def test_hex_in_argument():
    result = subprocess.run(
        [sys.executable, '-m', 'vaser', 'decode', '--hex-in', '848282848d'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '4 13 last'


def test_encode_accepts_trailing_flag_keywords():
    result = subprocess.run(
        [sys.executable, '-m', 'vaser', 'encode', '4', '13', 'fragment'],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout != b''


def test_encode_splits_on_markers_inside_sequence():
    result = subprocess.run(
        [sys.executable, '-m', 'vaser', 'encode', '4', 'fragment', '13', 'last'],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout != b''


def test_encode_splits_on_next_marker_and_decode_emits_next():
    encode_result = subprocess.run(
        [sys.executable, '-m', 'vaser', 'encode', '4', 'next', '13', '--hex'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert encode_result.returncode == 0, encode_result.stderr

    decode_result = subprocess.run(
        [sys.executable, '-m', 'vaser', 'decode', '--hex'],
        cwd=REPO_ROOT,
        input=encode_result.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    assert decode_result.returncode == 0, decode_result.stderr
    assert decode_result.stdout.strip().splitlines() == ['4 next', '13 next']


def test_decode_handles_multiple_chunks():
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'vaser',
            'encode',
            '4',
            'fragment',
            '13',
            'last',
            '--hex',
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    decode_result = subprocess.run(
        [sys.executable, '-m', 'vaser', 'decode', '--hex'],
        cwd=REPO_ROOT,
        input=result.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    assert decode_result.returncode == 0, decode_result.stderr
    assert decode_result.stdout.strip().splitlines() == ['4 fragment', '13 last']
