import logging


class VaserUnitOverflowError(RuntimeError):
    def __init__(self, msg, max_size):
        super().__init__(msg)
        self.max_size = max_size


class VaserInvalidFlagsError(RuntimeError):
    pass


class Vaser:
    GROUP_WIDTH = 7  # work with full bytes (VLQ unit is GROUP_WIDTH + 1 for the 'stop' bit)
    VLQ_UNIT = GROUP_WIDTH + 1

    @property
    def fragment(self):
        return self._fragment

    @property
    def last(self):
        return self._last

    @property
    def args(self):
        return self._args

    @property
    def as_bytes(self):
        if self._bytes is None:
            return self._args_to_bytes()
        return self._bytes

    def __init__(self, sizes=None):
        self._group_width = self.GROUP_WIDTH
        self._args = []
        self._fragment = None
        self._last = None
        self._units = []
        self._bytes = None
        if sizes:
            self.add(sizes)

    def add(self, sizes, *, fragment=None):
        if self._fragment is not None:
            raise RuntimeError('Cannot add an argument after a fragmented one')
        if self._last is not None:
            raise RuntimeError('Cannot add an argument after a last one')
        try:
            _iterator = iter(sizes)
        except TypeError:
            # not iterable
            sizes = [sizes]
        self._bytes = None
        for size in sizes:
            self._args.append(size)
        if fragment is not None:
            self._fragment = fragment

    def finalize(self, *, fragment=None) -> bytes:
        if self._last:
            raise RuntimeError('Already finalized')
        if self._fragment is not None and fragment is not None:
            raise RuntimeError('Fragment already set')
        if self._fragment is None and fragment is not None:
            self._fragment = fragment
        if self._fragment is None:
            self._fragment = False
        self._last = not self._fragment
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
    print('vaser main')


if __name__ == '__main__':
    main()
