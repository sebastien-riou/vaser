import argparse
import copy
import logging
from pathlib import Path
import hashlib
import runpy
from pysatl import Utils

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


def check_test_case(args, chunk, *, fragment=False, last=True, **kwargs):
    if chunk.args != args:
        logging.error(f'args:       {args}')
        logging.error(f'chunk.args: {chunk.args}')
        raise RuntimeError()
    if fragment != chunk.fragment:
        logging.error(f'fragment:       {fragment}')
        logging.error(f'chunk.fragment: {chunk.fragment}')
        raise RuntimeError()
    if last != chunk.last:
        raise RuntimeError()

    logging.info(f'bytes: {Utils.hexstr(chunk.bytes)}')

    # check the serialized version can be decoded and match the original
    raw_bytes = chunk.bytes
    decoded, consumed = Vaser.decode(raw_bytes, **kwargs)
    logging.debug(f'consumed: {consumed} bytes ({consumed*8} bits)')
    logging.debug(f'decoded: {Utils.hexstr(decoded.bytes)}')
    logging.info(f'decoded: {decoded.args}')
    if decoded.args != args:
        raise RuntimeError()
    if fragment != decoded.fragment:
        raise RuntimeError()
    if last != decoded.last:
        raise RuntimeError()
    if consumed != len(raw_bytes):
        raise RuntimeError()
