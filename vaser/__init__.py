import logging
import io
from typing import override

class VaserUnitOverflowError(RuntimeError):
    def __init__(self,msg,max_size):
        super().__init__(msg)
        self.max_size = max_size

class VaserInvalidFlagsError(RuntimeError):
    pass

class Vaser(object):
    GROUP_WIDTH = 6       
    
    @property
    def unit(self):
        return self._unit

    @property
    def fragment(self):
        return self._fragment

    @property
    def last(self):
        return self._last
    
    @property
    def units(self):
        return self._units
    
    @property
    def args(self):
        args = []
        for i in range(len(self._units)):
            args += [x['size'] for x in self._units[i]['args']]
        if self._args:
            args += self._args
        return args

    @property
    def bytes(self):
        if self._bytes is None:
            b = bytearray()
            for u in self._units:
                b += u['bytes']
            self._bytes = bytes(b)
        return self._bytes

    def __init__(self, sizes=None,* , unit=64, check=True, group_width: int|None = None):
        if group_width is None:
            group_width = self.GROUP_WIDTH
        self._group_width = group_width
        self._unit = unit
        self._args = []
        self._fragment = False
        self._last = False
        self._units = []
        self._bytes = None
        if sizes:
            self.add(sizes, check=check)

    def add(self, sizes, *, fragment=False, check=True):
        if self._fragment:
            raise RuntimeError('Cannot add an argument after a fragmented one')
        if self._last:
            raise RuntimeError('Cannot add an argument after a last one')
        try:
            _iterator = iter(sizes)
        except TypeError:
            # not iterable
            sizes = [sizes]
        self._bytes = None
        for size in sizes:
            self._args.append({'size':size,'fragment':fragment,'last':False})
            if check:
                try:
                    self._args_to_bytes()
                except VaserUnitOverflowError as e:
                    self._args.pop()
                    size_1 = e.max_size
                    if size_1 > 0:
                        logging.debug('Auto split: create fragment')
                        size_2 = size - size_1
                        self._args.append({'size':size_1,'fragment':True,'last':False})
                    else:
                        logging.debug('Auto split: add arg fully in new unit')
                        size_2 = size
                    logging.debug(f'Auto split: size_1=0x{size_1:x}, size_2=0x{size_2:x}')
                    encoding = self._args_to_bytes(finalize_unit=True)
                    self._units.append({'args':self._args, 'bytes':encoding})
                    self._args = []
                    self._args.append({'size':size_2,'fragment':fragment,'last':False})
    
    def finalize(self, *, fragment=False) -> bytes:
        if self._fragment:
            raise RuntimeError('Cannot add an argument after a fragmented one')
        if self._last:
            raise RuntimeError('Cannot add an argument after a last one')
        last = not fragment
        self._args[-1]['fragment']=fragment   
        self._args[-1]['last']=last
        encoding = self._args_to_bytes()
        self._units.append({'args':self._args, 'bytes':encoding})
        self._args = None
        self._fragment = fragment
        self._last = last
        self._bytes = None
        return self.bytes
    
    def _n_groups(self, width: int) -> int:
        return (width + self._group_width - 1) // self._group_width

    def _group_mask(self) -> int:
        return (1 << self._group_width) - 1

    def _max_size(self,size,overflow):
        n_groups_ov = self._n_groups(overflow)
        n_groups = self._n_groups(size.bit_length())
        if n_groups <= n_groups_ov:
            return 0 # must mark previous as last in unit
        n_groups -= n_groups_ov
        max_width = n_groups * self._group_width
        max_size = (1 << max_width) - 1
        return max_size

    def _encode_size(self, size: int):
        p = 0
        out = 0
        # encode size by group of x bits
        width = size.bit_length()
        n_groups = self._n_groups(width)
        logging.debug(f'width = {width}, n_groups = {n_groups}')
        mask = self._group_mask()
        for i in range(n_groups):
            g = size & mask
            logging.debug(f'group {i}: g = 0x{g:x}')
            size = size >> self._group_width
            out |= g << p 
            p += self._group_width + 1
        out |= 1 << (p-1) # mark the last group as such
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
            group_cnt  += 1
            if dat & 1:
                break
            dat = dat >> 1
            if 0 == dat:
                raise RuntimeError()
        n_groups = group_cnt
        logging.debug(f'width = {p}, n_groups = {n_groups}')
        return size, n_groups*(self._group_width+1)

    def _args_to_bytes(self, *,finalize_unit=False):
        logging.debug(f'----- args_to_bytes START -----')
        logging.debug(f'self._args: {self._args}')
        out = 0 # 0 encode 'no argument'
        p = 0
        for i in range(len(self._args)):
            size = self._args[i]['size']
            fragment = self._args[i]['fragment']
            last = self._args[i]['last']
            so,sp = self._encode_size(size)
            out |= so << p
            p += sp
            # encode 'last in unit'
            last_in_unit = fragment or last or (i+1 == len(self._args) and finalize_unit)
            if last_in_unit:
                out |= 1 << p
            p += 1
            logging.debug(f'size = {size}, last_in_unit = {last_in_unit}, p = {p}, fragment = {fragment}, last = {last}')
        if len(self._args) > 0:
            if fragment:
                out |= 1 << (self._unit - 2)
            p += 1
            if not fragment:
                if last:
                    out |= 1 << (self._unit - 1)   
            spare_bits =  self._unit - 2 - p
            logging.debug(f'Spare bits: {spare_bits}')
            if spare_bits < 0:
                max_size = self._max_size(size, -spare_bits)
                logging.debug(f'Max size: {max_size}')
                raise VaserUnitOverflowError(f'Cannot fit into {self._unit} bits',max_size)
        logging.debug(f'----- args_to_bytes END -----')
        return out.to_bytes(8,byteorder='little') 
    
    @classmethod
    def decode(cls, raw_bytes, **kwargs):
        logging.debug(f'----- decode START -----')
        out = cls(**kwargs)
        unit = out.unit
        logging.debug(f'decode: unit = {unit}')
        if unit != 64:
            raise RuntimeError()
        bytes_per_unit = unit // 8
        n_units = len(raw_bytes) // bytes_per_unit
        if n_units * bytes_per_unit != len(raw_bytes):
            raise RuntimeError()
        src = io.BytesIO(raw_bytes)
        for u in range(n_units):
            args = []
            rbytes = src.read(bytes_per_unit)
            dat = int.from_bytes(rbytes,byteorder='little')
            fragment = (dat >> (unit - 2)) & 1
            last = (dat >> (unit - 1)) & 1
            logging.debug(f'unit {u}: fragment = {fragment}, last = {last}, dat = 0x{dat:x}')
            if fragment and last:
                raise VaserInvalidFlagsError()
            p = 0
            while p < unit:
                size,sp = out._decode_size(dat)
                dat = dat >> sp 
                p += sp
                last_in_unit = dat & 1
                p += 1
                dat = dat >> 1
                logging.debug(f'add arg, p = {p}, size = {size}, last_in_unit = {last_in_unit}')
                args.append(size)
                if last_in_unit:
                    break
            for a in args[:-1]:
                out.add(a)
            out.add(args[-1],fragment=fragment)
        out.finalize(fragment=fragment)
        logging.debug(f'----- decode END -----')
        return out


def main():
    print('vaser main')


if __name__ == '__main__':
    main()