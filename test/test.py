def main():
    from test.common import parse_test_args
    from test import test_basic, test_auto_split, test_max_val
    parse_test_args()
    test_basic.test_it()
    test_auto_split.test_it()
    test_max_val.test_it()

    
if __name__ == '__main__':
    main()


    