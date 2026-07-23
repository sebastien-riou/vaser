from vaser import Vaser, VaserBin


def test_vaserbin_serializes_sizes_before_payload():
    payloads = [b'', b'abc', b'\x00\xff']
    chunk = VaserBin(payloads)

    encoded = chunk.as_bytes
    sizes_chunk, sizes_consumed = Vaser.decode(encoded)
    assert sizes_chunk.args == [len(payloads[0]), len(payloads[1]), len(payloads[2])]
    assert encoded[sizes_consumed:] == b''.join(payloads)


def test_vaserbin_decode_returns_payload_as_bytes():
    payload = b'\x00\xffabc'
    encoded = VaserBin([payload]).as_bytes

    decoded, consumed = VaserBin.decode(encoded)
    assert decoded.args == [payload]
    assert consumed == len(encoded)


def test_vaserbin_round_trip_multiple_arguments():
    payloads = [b'abc', b'', b'\x00\xff']
    encoded = VaserBin(payloads).as_bytes

    decoded, consumed = VaserBin.decode(encoded)
    assert decoded.args == payloads
    assert consumed == len(encoded)
