from test.common import *
from vaser import Vaser

def test_it():
    all_args = [4,12,255,1<<17,2,8,1<<32,128,1<<32]
    for n in range(2,len(all_args)):
        args = all_args[:n]
        s = Vaser(args)
        s.finalize()
        check_test_case(args,s)   
   
if __name__ == '__main__':
    parse_test_args()
    test_it()


    