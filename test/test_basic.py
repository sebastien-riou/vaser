from test.common import *
from vaser import Vaser


def test_it():
    args = [4, 13]
    s = Vaser(args,last=True)
    check_test_case(args, s)

    MAX_VAL = (1 << 64) - 1  # not really a max of the implementation, more a max of what we test
    args = [4, MAX_VAL, MAX_VAL, MAX_VAL, 255, 1 << 17, 2, 8, 1 << 32, 128, 1 << 32]
    for i in range(1, MAX_VAL.bit_length()):
        first = 1 << i
        all_args = [first] + args
        s = Vaser(all_args,last=True)
        #s.finalize()
        check_test_case(all_args, s)
    all_args = [MAX_VAL] + args
    s = Vaser(all_args,last=True)
    check_test_case(all_args, s)


if __name__ == '__main__':
    parse_test_args()
    test_it()
