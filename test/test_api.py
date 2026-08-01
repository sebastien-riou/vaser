from test.common import parse_test_args
from vaser import Vaser, VaserFlags


def test_encode_decode_default_flags():
    payload = b'\x01\x02\x03'
    chunk = Vaser(payload, flags=VaserFlags.DEFAULT)
    assert chunk.payload == payload
    assert chunk.fragment is False
    assert chunk.last_in_chunk is False
    assert chunk.last_in_list is False

    decoded, consumed = Vaser.decode(chunk.as_bytes)
    assert decoded.payload == payload
    assert decoded.flags == VaserFlags.DEFAULT
    assert consumed == len(chunk.as_bytes)


def test_encode_decode_fragment_flag():
    payload = b'\x99'
    chunk = Vaser(payload, flags=VaserFlags.FRAGMENT)
    assert chunk.fragment is True
    assert chunk.last_in_chunk is False
    assert chunk.last_in_list is False

    decoded, consumed = Vaser.decode(chunk.as_bytes)
    assert decoded.payload == payload
    assert decoded.flags == VaserFlags.FRAGMENT
    assert consumed == len(chunk.as_bytes)


def test_encode_decode_last_in_list_flag():
    payload = b'\x00\xFF'
    chunk = Vaser(payload, flags=VaserFlags.LAST_IN_LIST)
    assert chunk.last_in_list is True
    assert chunk.fragment is False

    decoded, consumed = Vaser.decode(chunk.as_bytes)
    assert decoded.payload == payload
    assert decoded.flags == VaserFlags.LAST_IN_LIST
    assert consumed == len(chunk.as_bytes)


def test_encode_decode_with_granularity_padding():
    for granularity in (1, 2, 4, 8):
        payload = b'\x01\x02\x03'
        chunk = Vaser(payload, flags=VaserFlags.DEFAULT, granularity=granularity)
        encoded = chunk.as_bytes
        assert len(encoded) % granularity == 0, f'Encoded length {len(encoded)} is not a multiple of granularity {granularity}'

        decoded, consumed = Vaser.decode(encoded, granularity=granularity)
        assert decoded.payload == payload, f'Decoded payload {decoded.payload} does not match original {payload}'
        assert decoded.flags == VaserFlags.DEFAULT, f'Decoded flags {decoded.flags} do not match original {VaserFlags.DEFAULT}'
        assert consumed == len(encoded), f'Consumed bytes {consumed} does not match encoded length {len(encoded)}'

def test_encode_decode_granularity_8():
    args = [b'\x00\x01\x02\x03\x04', b'', b'\x05']
    granularity = 8
    chunk = Vaser(args, flags=VaserFlags.LAST_IN_CHUNK, granularity=granularity)
    encoded = chunk.as_bytes
    assert len(encoded) % granularity == 0, f'Encoded length {len(encoded)} is not a multiple of granularity {granularity}'
    assert encoded == bytes.fromhex('14000102030400060500000000000000'), f'Encoded bytes {encoded.hex()} do not match expected'

    decoded, consumed = Vaser.decode(encoded, granularity=granularity)
    assert decoded.args == args, f'Decoded args {decoded.args} does not match original {args}'
    assert decoded.flags == VaserFlags.LAST_IN_CHUNK, f'Decoded flags {decoded.flags} do not match original {VaserFlags.LAST_IN_CHUNK}'
    assert consumed == len(encoded), f'Consumed bytes {consumed} does not match encoded length {len(encoded)}'

def test_it():
    test_encode_decode_default_flags()
    test_encode_decode_fragment_flag()
    test_encode_decode_last_in_list_flag()
    test_encode_decode_with_granularity_padding()
    test_encode_decode_granularity_8()


if __name__ == '__main__':
    parse_test_args()
    test_it()
