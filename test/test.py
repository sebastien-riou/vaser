

def main():
    from test.common import parse_test_args
    from test import test_api, test_cli

    parse_test_args()
    test_api.test_it()
    test_cli.test_it()


if __name__ == '__main__':
    main()
