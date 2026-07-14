"""Compact VLQ-style serialization helpers for integer values.

This module provides a small encoder/decoder for sequences of integer values
that can be serialized into bytes and reconstructed later.
"""

import logging


class VaserInvalidFlagsError(RuntimeError):
    """Raised when invalid fragment or finalization flags are encountered."""

    pass


class Vaser:
    """Encode and decode sequences of integer values into a compact byte format.

    The encoder stores a list of integer values and serializes them using a
    variable-length quantity (VLQ) scheme. It can also reconstruct a decoded
    instance from previously encoded bytes.
    """
    GROUP_WIDTH = 7  # work with full bytes (VLQ unit is GROUP_WIDTH + 1 for the 'stop' bit)
    VLQ_UNIT = GROUP_WIDTH + 1

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
        """Return the encoded integer values stored in this instance."""
        return self._args

    @property
    def as_bytes(self):
        """Return the serialized bytes for the current chunk."""
        if self._bytes is None:
            return self._args_to_bytes()
        return self._bytes

    def __init__(self, values=None, *, fragment=None, last=None):
        """Initialize a new encoder instance.

        :param values: Optional initial integer values to register.
        :type values: int or iterable of int
        :param fragment: Whether the chunk is fragmented.
        :type fragment: bool or None
        :param last: Whether the chunk is the last one.
        :type last: bool or None
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
        """Add one or more integer values to the chunk.

        :param values: One integer value or an iterable of integer values.
        :type values: int or iterable of int
        :param fragment: Mark the chunk as fragmented when provided.
        :type fragment: bool or None
        :param last: Mark the chunk as final when provided.
        :type last: bool or None
        :raises RuntimeError: If the chunk was already finalized or fragmented.
        """
        if self._fragment is not None:
            raise RuntimeError('Cannot add an argument after a fragmented one')
        if self._last is not None:
            raise RuntimeError('Cannot add an argument after a last one')
        try:
            _iterator = iter(values)
        except TypeError:
            # not iterable
            values = [values]
        self._bytes = None
        for value in values:
            self._args.append(value)
        if fragment is not None or last is not None:
            self.finalize(fragment=fragment,last=last)

    def finalize(self, *, fragment=None, last=None) -> bytes:
        """Finalize the chunk and serialize it to bytes.

        :param fragment: Set the fragmented flag on the payload.
        :type fragment: bool or None
        :param last: Set the final flag on the payload.
        :type last: bool or None
        :returns: The encoded byte representation.
        :rtype: bytes
        :raises RuntimeError: If the payload was already finalized.
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
            self._last = True
        self._bytes = self._args_to_bytes()
        return self.as_bytes

    def _n_groups(self, width: int) -> int:
        return max(1, (width + self._group_width - 1) // self._group_width)

    def _group_mask(self) -> int:
        return (1 << self._group_width) - 1

    def _encode_size(self, value: int):
        p = 0
        out = 0
        # encode size by group of x bits
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

    def _decode_size(self, dat):
        logging.debug(f'dat = 0x{dat:x}')
        p = 0
        size = 0
        mask = self._group_mask()
        group_cnt = 0
        while True:
            s = dat & mask
            dat = dat >> self._group_width
            size |= s << p
            p += self._group_width
            logging.debug(f'group {group_cnt }: s = 0x{s:x}, dat = 0x{dat:x}')
            group_cnt += 1
            if dat & 1:
                break
            dat = dat >> 1
            if 0 == dat:
                raise RuntimeError()
        n_groups = group_cnt
        logging.debug(f'width = {p}, n_groups = {n_groups}')
        return size, n_groups * (self._group_width + 1)

    def _args_to_bytes(self, *, finalize_unit=False):
        logging.debug('----- args_to_bytes START -----')
        logging.debug(f'self._args: {self._args}')
        out = 0
        p = 0
        nao, nap = self._encode_size(len(self._args))
        out = nao
        p = nap
        flags = 0
        if self._fragment:
            flags |= 1
        if self._last:
            flags |= 2
        fo, fp = self._encode_size(flags)
        out |= fo << p
        p += fp
        for i in range(len(self._args)):
            size = self._args[i]
            so, sp = self._encode_size(size)
            out |= so << p
            p += sp
            logging.debug(f'size = {size}, p = {p}')
        logging.debug(f'nap = {nap}, fp = {fp}, p = {p}')
        for i in [nap, fp, p]:
            if 0 != i % self.VLQ_UNIT:
                raise RuntimeError()
        payload_size = (p + 7) // 8
        logging.debug(f'payload_size = {payload_size}')
        pso, psp = self._encode_size(payload_size)
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
            v, p = out._decode_size(raw_bits)
            raw_bits = raw_bits >> p
            consumed_bits += p
            return v

        payload_size = read_vlq()
        logging.debug(f'consumed_bits: {consumed_bits}, payload_size: {payload_size}')
        consumed = ((consumed_bits + 7) // 8) + payload_size
        logging.debug(f'consumed: {consumed}')
        n_values = read_vlq()
        flags = read_vlq()
        fragment = flags & 1
        last = flags & 2
        if flags & ~3:
            raise VaserInvalidFlagsError(f'Invalid flags: {flags}')
        logging.debug(f'fragment: {fragment}, last: {last}')
        for i in range(n_values):
            a = read_vlq()
            logging.debug(f'arg {i}: {a}')
            out.add(a)
        if last or fragment:
            out.finalize(fragment=fragment)

        logging.debug('----- decode END -----')
        return out, consumed


def main():
    """Run the package entry point for manual verification."""
    print('vaser main')


if __name__ == '__main__':
    main()
