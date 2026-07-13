from test.common import *
from vaser import Vaser, VaserUnitOverflowError

def find_max_val():
    arg = 1
    # Find MSB
    try:
        while True:
            arg = 2*arg
            s = Vaser(arg)
            s.finalize()
            if len(s.units) > 1:
                break
    except VaserUnitOverflowError as e:
        pass
    max_val = arg // 2
    msb = max_val.bit_length()
    # Now find other digits one by one
    for p in range(msb-1,-1,-1):
        candidate = max_val | (1 << p)
        args = [candidate] * 5
        try:
            s = Vaser(args)
            s.finalize()
            max_val = candidate
        except VaserUnitOverflowError as e:
            pass
    check_max_val(max_val)
    

def check_max_val(max_val):
    # Try it and check
    args = [max_val] * 5
    s = Vaser(args)
    s.finalize()
    check_test_case(args,s)
    logging.info(f'Max val: {max_val} (0x{max_val:x}, {max_val.bit_length()} bits)')
    # Try one more, should fail
    try:
        args = [max_val+1] * 5
        s = Vaser(args)
        s.finalize()
        raise RuntimeError("That was supposed to fail, this test needs update most likely (use --helper to fix)")
    except VaserUnitOverflowError as e:
        pass    

MAX_VAL = 0xffffffffffff

def test_it():
    check_max_val(MAX_VAL)
    args = [4,MAX_VAL,MAX_VAL,MAX_VAL, 255,1<<17,2,8,1<<32,128,1<<32]
    for i in range(1,MAX_VAL.bit_length()):
        first = 1 << i
        all_args = [first] + args
        s = Vaser(all_args)
        s.finalize()
        check_test_case(all_args,s)
    all_args = [MAX_VAL] + args
    s = Vaser(all_args)
    s.finalize()
    check_test_case(all_args,s)

if __name__ == '__main__':
    helper = parse_test_args()
    if helper:
        find_max_val()
    else:
        test_it()


    