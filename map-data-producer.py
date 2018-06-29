#! /usr/bin/env python
from __future__ import print_function

import argparse
import os
import sys
import json
import csv
import statistics
import re

def stats(into, l):
    into["mean"] = statistics.mean(l) if len(l) > 0 else -1
    into["stdev"] = statistics.stdev(l) if len(l) > 0 else -1

def process_file(filename, speed=None, ignore_illuminance=False):
    rows = []

    configs_in_file = set()

    with open(args.csv) as f:
        dict_data = csv.DictReader(f)

        # Process File
        for row in dict_data:
            row["Succeeded"] = row["Succeeded"].lower() == "true"
            row["Time"] = float(row["Time"])
            if not args.ignore_illuminance:
                row["MaxI"] = float(row["MaxI"].split('=')[1])
                row["MinI"] = float(row["MinI"].split('=')[1])
            if hasattr(row, "Hit"):
                row["Hit"] = re.split("[=\s]",row["Hit"])[1].lower () == "true"; 
            elif row["Reason"].startswith("hit_obstacle"):
                row["Hit"] = re.split("[=\s]", row["Reason"])[1].lower() == "true"
                row["Reason"] = ""
            configs_in_file.add(row["Configuration"])
            rows.append(row)
    configs = []
    configs.extend(choices)
    configs.extend(configs_in_file)
    if args.config is not None:
        configs = []
        configs.extend(args.config)

    min_illuminance={}
    max_illuminance={}
    failure_rate={}
    time={}

    data = {}

    for row in rows:
        if row["Configuration"] in configs:
            # Order so that ln_lm ensures m > n
            ls = int(row["Start"][1:])
            lt = int(row["Target"][1:])
            if ls > lt:
                tmp = ls
                ls = lt
                lt = tmp
            key = "l%s_l%s" % (ls,lt)
            if speed is not None:
                key = "%s_%s" %(key,speed)
            datum = {}
            if key not in data.keys():
                data[key] = datum
            else:
                datum = data[key]
            datum["from"] = "l%s" %ls
            datum["to"] = "l%s" %lt
            if row["Configuration"] not in datum.keys():
                datum[row["Configuration"]] = {}
            datum = datum[row["Configuration"]]

            if "success" not in datum.keys():
                datum["success"] = []
            datum["success"].append(1 if row["Succeeded"] else 0)

            if "time" not in datum.keys():
                datum["time"] = []
            if row["Succeeded"]:
                datum["time"].append(row["Time"])


            split = row["Configuration"].split('-')
            if "hitchance" not in datum.keys():
                datum["hitchance"] = []
            datum["hitchance"].append(1 if row["Hit"] and int(split[len(split)-1]) > 25 else 0)
            if speed is not None:
                datum["speed"] = speed
            if not ignore_illuminance:
                # Illuminance is independent of config so add at top level
                if "max_illuminance" not in data[key].keys():
                    data[key]["max_illuminance"] = []
                data[key]["max_illuminance"].append(row["MaxI"])

                if "min_illuminance" not in data[key].keys():
                    data[key]["min_illuminance"] = []
                data[key]["min_illuminance"].append(row["MinI"])
            

    return data

choices=['amcl-kinect', 'amcl-lidar', 'mrpt-lidar', 'mrpt-kinect', 'aruco']
parse_args = argparse.ArgumentParser()
parse_args.add_argument("-s", "--stats", action='store_true', help='Print out the stats')
parse_args.add_argument('-c', '--config', choices=['amcl-kinect', 'amcl-lidar', 'mrpt-lidar', 'mrpt-kinect', 'aruco'], nargs='+', help="The configuration(s) to include")
parse_args.add_argument('-m', '--map', type=str, help="The map file to update")
parse_args.add_argument('-e', '--speed', action='append', nargs=2, metavar=('SPEED', 'DATA'), help='A speed and data.csv pair for speed-specific data')
parse_args.add_argument('-i', '--ignore_illuminance', action='store_true', help='Ignore any illuminance data if it exists (keep map data intact)')
parse_args.add_argument("csv", type=str, help="The CSV to process")

args = parse_args.parse_args()
update_map = False
args.csv = os.path.expanduser(args.csv)
if hasattr(args,'map') and args.map is not None:
    args.map = os.path.expanduser(args.map)
    update_map = True

data = {}
if args.speed is not None:
    for combo in args.speed:
        data.update(process_file(combo[1], combo[0], ignore_illuminance=args.ignore_illuminance))
else:
    data = process_file(args.csv, ignore_illuminance=args.ignore_illuminance)

    
map_json = {}
if update_map:  
    f = open(args.map)
    s = f.read()
    map_json = json.loads(s)
if not args.ignore_illuminance:
    map_json["max_illuminance"] = []
    map_json["min_illuminance"] = []

map_json["time"] = []
map_json["successrate"] = []
map_json["hitrate"] = []

# Do the stats
for key in data:
    mi = {}
    mi["from"] = data[key]["from"]
    mi["to"] = data[key]["to"]
    if hasattr(data[key], "speed"):
        mi["speed"] = data[key]["speed"]
    if not args.ignore_illuminance:
        stats(mi, data[key]["max_illuminance"])
        map_json["max_illuminance"].append(mi)

    mi = {}
    mi["from"] = data[key]["from"]
    mi["to"] = data[key]["to"]
    if not args.ignore_illuminance:
        stats(mi, data[key]["min_illuminance"])
        map_json["min_illuminance"].append(mi)

    all_times = []

    t = {}
    t["from"] = data[key]["from"]
    t["to"] = data[key]["to"]

    sr = {}
    sr["from"] = data[key]["from"]
    sr["to"] = data[key]["to"]
    all_successes = []

    hr = {}
    hr["from"] = data[key]["from"]
    hr["to"] = data[key]["to"]
    all_hits = []

    for config in data[key].keys():
        if config in ["max_illuminance", "min_illuminance", "from", "to"]:
            continue
        td = {}
        if len(data[key][config]["time"]) > 1:
            stats(td, data[key][config]["time"])
            all_times.extend(data[key][config]["time"])
        elif len(data[key][config]["time"]) > 0:
            td["mean"] = data[key][config]["time"][0]
            td["stdev"] = 0
        else:
            td["mean"] = 0.0
            td["stdev"] = 0.0
        t[config] = td

        srd = {}
        srd["successrate"] = sum(data[key][config]["success"]) / float(len(data[key][config]["success"]));
        all_successes.extend(data[key][config]["success"])
        sr[config] = srd

        hrd = {}
        hrd["hitrate"] = sum(data[key][config]["hitchance"]) / float(len(data[key][config]["hitchance"]))
        all_hits.extend(data[key][config]["hitchance"])
        hr[config] = hrd

    stats(t, all_times);
    map_json["time"].append(t)

    sr["prob"] = sum(all_successes)/ float(len(all_successes))
    map_json["successrate"].append(sr)

    hr["prob"] = sum(all_hits)/ float(len(all_hits))
    map_json["hitrate"].append(hr)


if update_map:
    with open(args.map, 'w') as m:
        json.dump(map_json, m, indent=4)


failed_edges = {}
hit_edges = {}

for i in range(len(map_json["max_illuminance"])):
    ill = map_json["max_illuminance"][i]
    dar = map_json["min_illuminance"][i]
    tim = map_json["time"][i]
    bum = map_json["hitrate"][i]
    suc = map_json["successrate"][i]

    froms = set([ill["from"], dar["from"], bum["from"], suc["from"], tim["from"]])
    if len(froms) != 1:
        print ("The assumption that all indexes have the same from,to is wrong %s" %str(froms))
        sys.exit()

    print("Edge: %s to %s:" %(ill["from"], ill["to"]))
    print("   Max illuminance: avg=%s, stdev=%s" %(ill["mean"],ill["stdev"]))
    print("   Min illuminance: avg=%s, stdev=%s" %(dar["mean"], dar["stdev"]))
    print("   Overall time: avg=%s, stdev=%s" %(tim["mean"], tim["stdev"]))
    print("   Success rate: %s" %(suc["prob"] * 100))
    print("   Hit rate: %s" %(bum["prob"] * 100))
    print("   Configuration specific:")
    sr = {"configs" : []}
    hr = {"configs" : []}
    for i in tim.keys():
        if i not in ["mean","stdev","from", "to"]:
            print("      %s:" %i)
            print("          Time: avg=%s, stdev=%s" %(tim[i]["mean"], tim[i]["stdev"]))
            print("          Success rate: %s" %(suc[i]["successrate"] * 100.0))
            print("          Bump rate: %s" %(bum[i]["hitrate"] * 100.0))
            if suc[i]["successrate"] < 1:
                sr["configs"].append(i)
            if bum[i]["hitrate"] > 0:
                hr["configs"].append(i)
    key = "%s_to_%s" %(suc["from"], suc["to"])
    if suc["prob"] < 1:
        sr["prob"] = suc["prob"]
        sr["darkness"] = dar["mean"]

        failed_edges[key] = sr
    if bum["prob"] > 0:
        hit_edges[key] = {"prob" : suc["prob"], "configs" : hr["configs"]}

print("Edges where we failed to get to the target at least once: ")
for i in failed_edges:
    print("%s succeeded with probability %s" %(i,failed_edges[i]["prob"]))
    print("  Failed under the configurations: %s" %failed_edges[i]["configs"])
    print("  BTW, it is this dark: %s" %failed_edges[i]["darkness"])

print("Edges where we hit something at least once: ")
for i in hit_edges:
    print("%s hit something with probability %s" %(i, hit_edges[i]["prob"]))
    print("  Hit in the following configurations: %s" %hit_edges[i]["configs"])
