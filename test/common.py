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

def check_test_case(args, finalized, **kwargs):
    # check the args are correctly registered
    args_check = []
    for i in range(len(finalized.units)):
        args_check += [x['size'] for x in finalized.units[i]['args']]
    logging.info(f'args_check: {args_check}')
    ai = 0
    for a in args:
        remaining = a
        while remaining > 0:
            remaining -= args_check[ai]
            ai += 1
            if remaining < 0:
                raise RuntimeError()
            if ai > len(args_check):
                raise RuntimeError()
    if ai < len(args_check):
        raise RuntimeError()
    
    logging.info(f'bytes: {Utils.hexstr(finalized.bytes)}')
    
    # check the serialized version can be decoded and match the original
    raw_bytes = finalized.bytes
    logging.info(f'{Utils.hexstr(raw_bytes)}')
    decoded = Vaser.decode(raw_bytes, **kwargs)
    logging.info(f'decoded: {Utils.hexstr(decoded.bytes)}')
    logging.info(f'decoded: {decoded.args}')
    for i in range(len(finalized.units)):
        if finalized.units[i]['args'] != decoded.units[i]['args']:
            logging.debug(f"finalized.units[{i}]['args']: {finalized.units[i]['args']}")
            logging.debug(f"decoded.units[{i}]['args']:   {decoded.units[i]['args']}")
            raise RuntimeError()    