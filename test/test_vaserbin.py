from test.common import parse_test_args
from vaser import Vaser, VaserBin, to_ints


def test_vaserbin_serializes_sizes_before_payload():
    payloads = [b'', b'abc', b'\x00\xff']
    chunk = VaserBin(payloads)
    encoded = chunk.as_bytes
    assert chunk.size() == len(chunk.as_bytes)
    sizes_chunk, sizes_consumed = Vaser.decode(encoded)
    expected = [len(payloads[0]), len(payloads[1]), len(payloads[2])]
    sizes = to_ints(sizes_chunk.args)
    assert sizes == expected, f"Expected {expected}, got {sizes}"
    assert encoded[sizes_consumed:] == b''.join(payloads)


def test_vaserbin_decode_returns_payload_as_bytes():
    payloads = [b'\x00\xffabc']
    chunk = VaserBin(payloads)
    encoded = chunk.as_bytes
    assert chunk.size() == len(chunk.as_bytes)
    
    decoded, consumed = VaserBin.decode(encoded)
    assert decoded.args == payloads
    assert consumed == len(encoded)


def test_vaserbin_round_trip_multiple_arguments():
    payloads = [b'abc', b'', b'\x00\xff']
    chunk = VaserBin(payloads)
    encoded = chunk.as_bytes
    assert chunk.size() == len(chunk.as_bytes)
    
    decoded, consumed = VaserBin.decode(encoded)
    assert decoded.args == payloads
    assert consumed == len(encoded)

if __name__ == '__main__':
    parse_test_args()
    test_vaserbin_serializes_sizes_before_payload()
    test_vaserbin_decode_returns_payload_as_bytes()
    test_vaserbin_round_trip_multiple_arguments()