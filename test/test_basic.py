from test.common import *
from vaser import Vaser

def test_it():
    args = [4,12]
    s = Vaser(args)
    s.finalize()
    check_test_case(args,s)
    
   
if __name__ == '__main__':
    parse_test_args()
    test_it()


    