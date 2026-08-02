import argparse
import logging
from pathlib import Path

from vaser import Vaser

resource_path = Path(__file__).parent


def parse_test_args():
    parser = argparse.ArgumentParser(description='test vectors generator')
    levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    parser.add_argument('--log-level', default='WARNING', choices=levels)
    parser.add_argument('--helper', default=False, action='store_true')
    args = parser.parse_args()
    logformat = '%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s'
    logdatefmt = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(level=args.log_level, format=logformat, datefmt=logdatefmt)
    return args.helper


