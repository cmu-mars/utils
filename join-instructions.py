#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import sys
import json

def load_path(src, target, dir):
    filename = os.path.join(dir, "l%s_to_l%s.json" %(src,target))
    f = open(filename)
    s = f.read()
    f.close()
    j = json.loads(s)
    return j

def load_instructions(src, target, dir):
    filename = os.path.join(dir, "l%s_to_l%s.ig" %(src,target))
    f = open(filename)
    s = f.read()
    f.close ()
    return s

def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output_db", type=str, help='The file to output the instruction DB to')
    parser.add_argument("num_waypoints", type=int, help='The number of the highest waypoint')
    parser.add_argument("dir", type=str, help="The directory containing instructions and paths")

    args = parser.parse_args()

    if args.output_db is None:
        args.output_db = 'instructions-all.json'

    args.output_db = os.path.expandvars(args.output_db)
    args.dir = os.path.expandvars(args.dir)
    if not os.path.isdir(args.dir):
        print("The directory '%s' does not exist" %args.dir)
        sys.exit()

    return args


args = process_args()
db = {}

wrong = 0
right = 0
for i in range(1, args.num_waypoints):
    for j in range(1, args.num_waypoints):
        if i != j:
            try:
                path_info = load_path(i,j, args.dir)
                instructions = load_instructions(i,j, args.dir)
                path_info["instructions"] = instructions
                db["l%s_to_l%s" %(i,j)] = path_info
                right = right + 1
            except IOError:
                print("Warning: No path or instructions for l%s to l%s" %(i,j))
                wrong = wrong + 1
            except Exception:
                wrong = wrong + 1
                print("Warning: Something bad happened for l%s to l%s" %(i,j))

if wrong > 0:
    print("There were a total of %s filled in and %s missing entries " %(right,wrong))

with open(args.output_db, 'w') as f:
    json.dump(db,f, sort_keys=True, indent=2)

