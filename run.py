#!/usr/bin/env python

from collections import namedtuple
import subprocess
import os
import sys
import argparse
import copy
import json
import re
import shutil
import traceback
from termcolor import colored
import filecmp


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, 'out')


# TODO: buggy on multiple & consequence $$$
REPLACE_RE = re.compile(r'\$([#A-Za-z0-9_.-]+)?\$?')


def is_variable(path):
    # TODO: more checking
    return path[0] == '$' and path[1] != '$'


def make_out_dir():
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)


def get_path(configs, path):
    split_path = path.strip('$').split('.')
    first_path = split_path[0]
    config = None
    for c in configs:
        if first_path in c:
            config = c

    if config is None:
        raise Exception("Cannot find path: %s in config %s" % (path, repr(configs)))

    c = config
    for p in split_path:
        c = c[p]
    return c


def replace_config(configs, be_replaced):
    if isinstance(be_replaced, list):
        be_replaced = list(be_replaced)
        for i in range(len(be_replaced)):
            be_replaced[i] = replace_config(configs, be_replaced[i])
#            if is_variable(be_replaced[i]):
#                be_replaced[i] = get_path(configs, be_replaced[i])
        return be_replaced
    elif isinstance(be_replaced, dict):
        be_replaced = dict(be_replaced)
        for key in be_replaced:
            be_replaced[key] = replace_config(configs, be_replaced[key])
            #if is_variable(be_replaced[key]):
            #    be_replaced[key] = get_path(configs, be_replaced[key])
        return be_replaced
    elif isinstance(be_replaced, basestring):
        match = REPLACE_RE.search(be_replaced)
        while match:
            match_str = match.group(0)
            replaced = get_path(configs, match_str)
            be_replaced = be_replaced[:match.start()] + replaced + be_replaced[match.end():]
            match = REPLACE_RE.search(be_replaced)
        return be_replaced
    else:
        raise Exception("Wrong type: " + be_replaced)


def main(config, argv):
    default_config = config['#default']
    default_config['#argv'] = argv

    raw_command = config['#command']
    raw_env = config['#env']

    for item in config['#config']:
        try:
            configs = [default_config, item]
            item_name = replace_config(configs, '$#name')
            print colored(replace_config(configs, '$#heading'), 'blue')
            command = replace_config(configs, raw_command)
            env = os.environ.copy()
            for key in raw_env:
                env[key] = replace_config(configs, raw_env[key])
            out = subprocess.check_output(command, stderr=subprocess.STDOUT, env=env)
            print out
            with open(os.path.join(OUT_DIR, item_name), 'w') as f:
                f.write(out)
        except:
            print colored('!!!!!!!!!!!!!!!!!!!!! Error !!!!!!!!!!!!!!!!!!!!!', 'red')
            print colored(traceback.format_exc(), 'red')
        print


def display_group(config):
    configs = [config]

    all_files = os.listdir(OUT_DIR)

    equals = []

    for f in all_files:
        eq = None
        for e in equals: 
            if filecmp.cmp(os.path.join(OUT_DIR, f), os.path.join(OUT_DIR, e[0])):
                eq = e
                break
        if eq is None:
            equals.append([f])
        else:
            eq.append(f)

    print colored(replace_config(configs, '$#analyzer.#heading'), 'blue')
    if equals:
        for i, group in enumerate(equals):
            print "Group %d: %s" % (i + 1, ',  '.join(map(lambda x: colored(x, 'green'), group)))
    else:
        print "<Empty>"


def parse_args():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print "Usage: %s config # stdin: argv" % sys.argv[0]
        print "Usage: %s config argv" % sys.argv[0]
        return
    else:
        with open(sys.argv[1], 'r') as f:
            config = json.loads(f.read())

        if len(sys.argv) == 2:
            argv = sys.stdin.read()
        elif len(sys.argv) == 3:
            argv = sys.argv[2]

        make_out_dir()
        main(config, argv)
        display_group(config)


if __name__ == "__main__":
    parse_args()


