"""Compact VLQ-style serialization helpers for values.

This module provides a small encoder/decoder for sequences of values
that can be serialized into bytes and reconstructed later.
"""

import logging


def to_ints(values):
    """Convert a sequence of values to a list of integers.

    :param values: A single :class:`bytes` value or an iterable of bytes.
    :type values: bytes or iterable of bytes
    :returns: A list of integers corresponding to the input values.
    :rtype: list[int]
    """
    if isinstance(values, (bytes, bytearray, memoryview)):
        return [int.from_bytes(values, byteorder='little')]
    try:
        iterator = iter(values)
    except TypeError as exc:
        raise TypeError('Values must be bytes/int or an iterable of bytes/int') from exc
    out = []
    for value in iterator:
        if isinstance(value, (bytes, bytearray, memoryview)):
            out.append(int.from_bytes(value, byteorder='little'))
        elif isinstance(value, int):
            out.append(value)
        else:
            raise TypeError('Values must be bytes/int or an iterable of bytes/int')
    return out

class VaserInvalidFlagsError(RuntimeError):
    """Raised when invalid fragment or finalization flags are encountered."""

    pass


class Vaser:
    """Encode and decode sequences of values into a compact byte format.

    The encoder stores a list of values and serializes them using a
    variable-length quantity (VLQ) scheme. It can also reconstruct a decoded
    instance from previously encoded bytes.
    """
    GROUP_WIDTH = 7  # work with full bytes (VLQ unit is GROUP_WIDTH + 1 for the 'stop' bit)
    VLQ_UNIT = GROUP_WIDTH + 1

    @staticmethod
    def _coerce_value(value) -> bytes | int:
        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value)
        if isinstance(value, int):
            return value
        raise TypeError('VaserBin values must be bytes/int or an iterable of bytes/int')

    @classmethod
    def _coerce_values(cls, values):
        if values is None:
            return []
        if isinstance(values, (bytes, bytearray, memoryview)):
            return [cls._coerce_value(values)]
        if isinstance(values, int):
            return [cls._coerce_value(values)]
        try:
            iterator = iter(values)
        except TypeError as exc:
            raise TypeError('VaserBin values must be bytes/int or an iterable of bytes/int') from exc
        return [cls._coerce_value(value) for value in iterator]

    @property
    def fragment(self):
        """Return whether the payload is marked as fragmented."""
        return self._fragment

    @property
    def last(self):
        """Return whether the payload is marked as the final chunk."""
        return self._last

    @property
    def args(self):
        """Return the encoded values stored in this instance."""
        return self._args

    @property
    def as_bytes(self):
        """Return the serialized bytes for the current chunk."""
        if self._bytes is None:
            return self._args_to_bytes()
        return self._bytes

    def __init__(self, values=None, *, fragment=None, last=None):
        """Initialize a new encoder instance.

        :param values: A single :class:`bytes` value or an iterable of bytes.
        :type values: bytes or iterable of bytes
        :param fragment: Whether the chunk is fragmented.
        :type fragment: bool or None. If not None, it triggers finalization.
        :param last: Whether the chunk is the last one.
        :type last: bool or None. If not None, it triggers finalization.
        """
        self._group_width = self.GROUP_WIDTH
        self._args = []
        self._fragment = None
        self._last = None
        self._units = []
        self._bytes = None
        if values:
            self.add(values, fragment=fragment, last=last)

    def add(self, values, *, fragment=None, last=None):
        """Add one or more values to the chunk.

        :param values: A single :class:`bytes` value or an iterable of bytes.
        :type values: bytes or iterable of bytes
        :param fragment: Mark the chunk as fragmented when provided.
        :type fragment: bool or None. If not None, it triggers finalization.
        :param last: Mark the chunk as final when provided.
        :type last: bool or None. If not None, it triggers finalization.
        :raises RuntimeError: If the chunk was already finalized.
        """
        if self._fragment is not None:
            raise RuntimeError('Cannot add an argument after a fragmented one')
        if self._last is not None:
            raise RuntimeError('Cannot add an argument after a last one')
        values = self._coerce_values(values)
        self._bytes = None
        for value in values:
            self._args.append(value)
        if fragment is not None or last is not None:
            self.finalize(fragment=fragment,last=last)

    def finalize(self, *, fragment=None, last=None) -> bytes:
        """Finalize the chunk and serialize it to bytes.

        :param fragment: Set the fragmented flag on the chunk.
        :type fragment: bool or None. If None, defaults to False.
        :param last: Set the final flag on the chunk.
        :type last: bool or None. If None, defaults to False.
        :returns: The encoded byte representation.
        :rtype: bytes
        :raises RuntimeError: If the chunk was already finalized.
        """
        if self._last is not None:
            raise RuntimeError('Already finalized')
        if fragment is not None:
            self._fragment = fragment
        if self._fragment is None:
            self._fragment = False
        if last is not None:
            self._last = last
        if self._last is None:
            self._last = False
        if self._fragment and self._last:
            raise VaserInvalidFlagsError('fragment and last cannot both be true')
        self._bytes = self._args_to_bytes()
        return self.as_bytes

    def _n_groups(self, width: int) -> int:
        return max(1, (width + self._group_width - 1) // self._group_width)

    def _group_mask(self) -> int:
        return (1 << self._group_width) - 1

    def _encode_value(self, value):
        p = 0
        out = 0
        # encode value by group of x bits
        if isinstance(value, (bytes, bytearray, memoryview)):
            width = len(value) * 8
            value = int.from_bytes(value, byteorder='little')
        else:
            width = value.bit_length()
        n_groups = self._n_groups(width)
        mask = self._group_mask()
        v = value
        for i in range(n_groups):
            g = v & mask
            logging.debug(f'group {i}: g = 0x{g:x}')
            v = v >> self._group_width
            out |= g << p
            p += self._group_width + 1
        out |= 1 << (p - 1)  # mark the last group as such
        logging.debug(
            f"value = {value}, width = {width}, n_groups = {n_groups}, out = {out.to_bytes((p+7)//8,byteorder='little')}"
        )
        return out, p

    def _decode_value(self, dat):
        logging.debug(f'dat = 0x{dat:x}')
        p = 0
        val = 0
        mask = self._group_mask()
        group_cnt = 0
        while True:
            s = dat & mask
            dat = dat >> self._group_width
            val |= s << p
            p += self._group_width
            logging.debug(f'group {group_cnt }: s = 0x{s:x}, dat = 0x{dat:x}')
            group_cnt += 1
            if dat & 1:
                break
            dat = dat >> 1
            if 0 == dat:
                raise RuntimeError()
        n_groups = group_cnt
        nbytes_if_int = (val.bit_length() + 7) // 8
        nbytes_if_bytes = p // 8
        val = val.to_bytes(max(nbytes_if_int, nbytes_if_bytes), byteorder='little')
        logging.debug(f'decoded value = {val}, p = {p}, n_groups = {n_groups}')
        return val, n_groups * (self._group_width + 1)

    def _encoded_value_width(self, value) -> int:
        """Return the number of bits needed to encode a value with the VLQ scheme."""
        if isinstance(value, (bytes, bytearray, memoryview)):
            width = len(value) * 8
        else:
            width = value.bit_length()
        n_groups = max(1, (width + self._group_width - 1) // self._group_width)
        return n_groups * self.VLQ_UNIT

    def size(self) -> int:
        """Return the number of bytes that :attr:`as_bytes` would produce."""
        p = 0
        nap = self._encoded_value_width(len(self._args))
        p += nap
        flags = int(bool(self._fragment)) | (int(bool(self._last)) << 1)
        fp = self._encoded_value_width(flags)
        p += fp
        for value in self._args:
            p += self._encoded_value_width(value)
        for i in [nap, fp, p]:
            if 0 != i % self.VLQ_UNIT:
                raise RuntimeError()
        payload_size = (p + 7) // 8
        psp = self._encoded_value_width(payload_size)
        return ((psp + 7) // 8) + payload_size

    def _args_to_bytes(self, *, finalize_unit=False):
        logging.debug('----- args_to_bytes START -----')
        logging.debug(f'self._args: {self._args}')
        out = 0
        p = 0
        nao, nap = self._encode_value(len(self._args))
        out = nao
        p = nap
        flags = 0
        if self._fragment:
            flags |= 1
        if self._last:
            flags |= 2
        fo, fp = self._encode_value(flags)
        out |= fo << p
        p += fp
        for i in range(len(self._args)):
            value = self._args[i]
            so, sp = self._encode_value(value)
            out |= so << p
            p += sp
            logging.debug(f'value = {value}, p = {p}')
        logging.debug(f'nap = {nap}, fp = {fp}, p = {p}')
        for i in [nap, fp, p]:
            if 0 != i % self.VLQ_UNIT:
                raise RuntimeError()
        payload_size = (p + 7) // 8
        logging.debug(f'payload_size = {payload_size}')
        pso, psp = self._encode_value(payload_size)
        out = (out << psp) | pso
        out_size = ((psp + 7) // 8) + payload_size
        logging.debug('----- args_to_bytes END -----')
        return out.to_bytes(out_size, byteorder='little')

    @classmethod
    def decode(cls, raw_bytes, **kwargs):
        """Decode bytes back into a :class:`Vaser` instance.

        :param raw_bytes: The encoded byte sequence to parse.
        :type raw_bytes: bytes
        :param kwargs: Keyword arguments forwarded to :meth:`__init__`.
        :returns: A tuple containing the decoded instance and the number of
            bytes consumed from the input.
        :rtype: tuple[Vaser, int]
        """
        logging.debug('----- decode START -----')
        out = cls(**kwargs)
        raw_bits = int.from_bytes(raw_bytes, byteorder='little')
        consumed_bits = 0

        def read_vlq() -> int:
            nonlocal raw_bits, consumed_bits
            v, p = out._decode_value(raw_bits)
            raw_bits = raw_bits >> p
            consumed_bits += p
            return v

        def read_vlq_int() -> int:
            vbytes = read_vlq()
            return int.from_bytes(vbytes, byteorder='little')

        payload_size = read_vlq_int()
        logging.debug(f'consumed_bits: {consumed_bits}, payload_size: {payload_size}')
        consumed = ((consumed_bits + 7) // 8) + payload_size
        logging.debug(f'consumed: {consumed}')
        n_values = read_vlq_int()
        flags = read_vlq_int()
        fragment = bool(flags & 1)
        last = bool(flags & 2)
        if flags & ~3:
            raise VaserInvalidFlagsError(f'Invalid flags: {flags}')
        logging.debug(f'fragment: {fragment}, last: {last}')
        for i in range(n_values):
            a = read_vlq()
            logging.debug(f'arg {i}: {a}')
            out.add(a)
        if fragment or last:
            out.finalize(fragment=fragment, last=last)

        logging.debug('----- decode END -----')
        return out, consumed


class VaserBin(Vaser):
    """Encode and decode sequences of byte values using a size-prefixed format.

    The serialized stream starts with a :class:`Vaser` encoding of the list of
    individual value sizes. The payload that follows contains the original byte
    values appended one after another.
    """

    @staticmethod
    def _coerce_value(value) -> bytes:
        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value)
        raise TypeError('VaserBin values must be bytes or an iterable of bytes')

    @classmethod
    def _coerce_values(cls, values):
        if values is None:
            return []
        if isinstance(values, (bytes, bytearray, memoryview)):
            return [cls._coerce_value(values)]
        try:
            iterator = iter(values)
        except TypeError as exc:
            raise TypeError('VaserBin values must be bytes or an iterable of bytes') from exc
        return [cls._coerce_value(value) for value in iterator]

    def __init__(self, values=None, *, fragment=None, last=None):
        super().__init__(values=None, fragment=None, last=None)
        if values is not None:
            self.add(values, fragment=fragment, last=last)

    def add(self, values, *, fragment=None, last=None):
        """Add one or more byte values to the chunk.

        :param values: A single :class:`bytes` value or an iterable of bytes.
        :type values: bytes or iterable of bytes
        :param fragment: Mark the chunk as fragmented when provided.
        :type fragment: bool or None
        :param last: Mark the chunk as final when provided.
        :type last: bool or None
        :raises RuntimeError: If the chunk was already finalized.
        :raises TypeError: If values are not bytes-like.
        """
        super().add(self._coerce_values(values), fragment=fragment, last=last)


    def size(self) -> int:
        """Return the number of bytes that :attr:`as_bytes` would produce."""
        sizes = [len(value) for value in self._args]
        return Vaser(sizes, fragment=self._fragment, last=self._last).size() + sum(sizes)

    def _args_to_bytes(self) -> bytes:
        sizes = [len(value) for value in self._args]
        sizes_payload = Vaser(sizes, fragment=self._fragment, last=self._last).as_bytes
        return sizes_payload + b''.join(self._args)

    @classmethod
    def decode(cls, raw_bytes, **kwargs):
        """Decode bytes back into a :class:`VaserBin` instance."""
        out = cls(**kwargs)
        sizes_chunk, sizes_consumed = Vaser.decode(raw_bytes)
        out._fragment = sizes_chunk.fragment
        out._last = sizes_chunk.last
        sizes = [int.from_bytes(x, byteorder='little') for x in sizes_chunk.args]
        remaining = raw_bytes[sizes_consumed:]
        consumed = sizes_consumed
        values = []
        offset = 0
        for size in sizes:
            if offset + size > len(remaining):
                raise RuntimeError('Truncated value payload')
            values.append(remaining[offset:offset + size])
            offset += size
        if offset != len(remaining):
            raise RuntimeError('Unexpected trailing data')
        out._args = values
        consumed += offset
        out._bytes = out._args_to_bytes()
        return out, consumed


from vaser.cli import main


if __name__ == '__main__':
    raise SystemExit(main())
