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
    parser.add_argument('-c', "--config_data", action="append", nargs=2, metavar=('config','dir'), help='For config the data is in dir',required=True)
    parser.add_argument("num_waypoints", type=int, help='The number of the highest waypoint')

    args = parser.parse_args()

    if args.output_db is None:
        args.output_db = 'instructions-all.json'

    args.output_db = os.path.expandvars(args.output_db)
    for d in args.config_data:
        d[1] = os.path.expandvars(d[1])
        if not os.path.isdir(d[1]):
            print("The directory '%s' does not exist" %d[1])
    return args


args = process_args()
db = {}

wrong = 0
right = 0
for d in args.config_data:
    for i in range(1, args.num_waypoints+1):
        for j in range(1, args.num_waypoints+1):
            if i != j:
                try:
                    path_info = load_path(i,j, d[1])
                    instructions = load_instructions(i,j, d[1])
                    path_info["instructions"] = instructions
                    key = "l%s_to_l%s" %(i,j)
                    if key in db.keys():
                        db[key][d[0]] = path_info
                    else:
                        db[key] = {}
                        db[key][d[0]] = path_info
                    right = right + 1
                except IOError:
                    print("Warning: No path or instructions for l%s to l%s in %s" %(i,j,d[0]))
                    wrong = wrong + 1
                except Exception:
                    wrong = wrong + 1
                    print("Warning: Something bad happened for l%s to l%s in %s" %(i,j,d[0]))

if wrong > 0:
    print("There were a total of %s filled in and %s missing entries " %(right,wrong))

with open(args.output_db, 'w') as f:
    json.dump(db,f, sort_keys=True, indent=2)

