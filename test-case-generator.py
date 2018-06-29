# test-<UUID>
#   - docker-compose-no-th.yml
#   - start
#       - ready.json
#   - logs
#   - roslogs
#   - perturb_killnode.sh
#   - perturb_killsensor.sh
#   - perturb_offlights.sh
#   - run_experiment.py

# PYTHON 3
import os
import stat
import sys
import uuid
import random
import re
import shutil

import instruction_db
import map_server
import argparse


def touch(fname, mode=0o666, dir_fd=None, **kwargs):
    flags = os.O_CREAT | os.O_APPEND
    with os.fdopen(os.open(fname, flags=flags, mode=mode, dir_fd=dir_fd)) as f:
        os.utime(f.fileno() if os.utime in os.supports_fd else fname,
            dir_fd=None if os.supports_fd else dir_fd, **kwargs)

READY_TEMPLATE='{"start-configuration" : "<CONFIG>", "start-loc" : "<START>", "target-loc" : "<TARGET>", "use-adaptation" : <ADAPT>, "utility-function" : "<UTILITY>"}'
CONFIGS = ['amcl-kinect', 'amcl-lidar', 'mrpt-lidar', 'mrpt-kinect', 'aruco-camera']
PERTURBS = ["node", "sensor", "nodeandsensor"]
LIGHT_PERTURBS = ["lights", "lightsonly", "nolights", "nolights", "nolights"]
INTERESTING_SRCS = ['l7', 'l28', 'l36', 'l29', 'l4', 'l37', 'l14', 'l13', 'l19', 'l39', 'l26', 'l27', 'l25', 'l11']
INTERESTING_TGTS = ['l34', 'l8', 'l9', 'l56', 'l3', 'l2', 'l15', 'l16', 'l17', 'l18', 'l21', 'l38', 'l47', 'l56', 'l55', 'l45', 'l42','l12']
UTILITIES = ['favor-timeliness', 'favor-efficiency', 'favor-safety']

PERTURB_NODEFAIL = 'curl -X POST http://localhost:8000/perturb/nodefail -d \'{"id" : "<NODE>"}\' -H "Content-Type:application/json"'
PERTURB_SENSOR = 'curl -X POST http://localhost:8000/perturb/sensor -d \'{"id" : "<SENSOR>", "state" : false}\' -H "Content-Type:application/json"'
PERTURB_LIGHTS = 'curl -X POST http://localhost:8000/perturb/light -d \'{"id" : "<LIGHT>", "state" : false}\' -H "Content-Type:application/json"'

OBSERVE = 'curl http://localhost:8000/observe'
START='curl -X POST http://localhost:8000/start'
PERTURB_SH = """#!/bin/sh
#<LIGHTS>
#<NODE>
#<SENSOR>
"""
INSTRUCTIONS_ALL = os.path.expanduser('~/catkin_ws/src/cp3_base/instructions/instructions-all.json')
MAP=os.path.expanduser("~/catkin_ws/src/cp3_base/maps/cp3.json")

inst_db = instruction_db.InstructionDB(INSTRUCTIONS_ALL)
c_map = map_server.MapServer(MAP)

configurations = set()
configurations.add("dummy")

def multi_replace(string, replacements, ignore_case=False):
    """
    Given a string and a dict, replaces occurrences of the dict keys found in the 
    string, with their corresponding values. The replacements will occur in "one pass", 
    i.e. there should be no clashes.
    :param str string: string to perform replacements on
    :param dict replacements: replacement dictionary {str_to_find: str_to_replace_with}
    :param bool ignore_case: whether to ignore case when looking for matches
    :rtype: str the replaced string
    """
    rep_sorted = sorted(replacements, key=lambda s: len(s[0]), reverse=True)
    rep_escaped = [re.escape(replacement) for replacement in rep_sorted]
    pattern = re.compile("|".join(rep_escaped), re.I if ignore_case else 0)
    return pattern.sub(lambda match: replacements[match.group(0)], string)

def get_ready(config,src,tgt,utility,case):
    rep = {"<CONFIG>" : config, "<START>" : src, "<TARGET>" : tgt, "<UTILITY>" : utility, "<ADAPT>" : "true" if case=='c' else "false"}
    ready = multi_replace(READY_TEMPLATE, rep)
    return ready

def get_config_info(only_lights=False):
    configuration = "dummy"
    config = None
    perturbs = None
    src = None
    tgt = None
    utility = None
    path = None
    light_perturbs = "nolights"
    while configuration in configurations or (path is None or len(path) == 0):
        config = random.choice(CONFIGS)
        perturbs = random.choice(PERTURBS)
        if only_lights:
            light_perturbs = "lightsonly"
            perturbs = "none"
            config='aruco-camera'
        else:
            light_perturbs = random.choice(LIGHT_PERTURBS)
            if light_perturbs == "lightsonly":
                perturbs = "none"
        src = random.choice(INTERESTING_SRCS)
        tgt = random.choice(INTERESTING_TGTS)
        utility = random.choice(UTILITIES)
        path = inst_db.get_path(src,tgt, utility + "-" + config)


        configuration = "%s-%s-%s-%s-%s-%s" %(config,perturbs,light_perturbs,src,tgt,utility)

    configurations.add(configuration)
    return configuration, config, perturbs, light_perturbs, src, tgt, utility, path

def generate_test_case(compose_file, path = ".", only_lights=False, cases=['c']):
    # get the configuration
    id,config,perturbs,light_perturbs,src,tgt,utility, route = get_config_info(only_lights)
    corridor = random.randint(1, len(route)-1)
    perturb_sleep = random.randint(1,inst_db.get_predicted_duration(src,tgt,config))

    for case in cases:
        # create directory structure
        test_directory = "%s/testcase-%s-%s/" %(path,id,case)
        os.makedirs(test_directory + "start")
        os.makedirs(test_directory + "logs/prism")
        os.makedirs(test_directory + "logs/alloy")
        os.makedirs(test_directory + "roslogs")
        os.chmod(test_directory + "logs", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        os.chmod(test_directory + "logs/prism", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        os.chmod(test_directory + "logs/alloy", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        os.chmod(test_directory + "roslogs", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        touch(test_directory + "logs/.INCLUDE_ME")
        touch(test_directory + "roslogs/.INCLUDE_ME")

        # create ready msg
        readyjson = get_ready(config,src,tgt,utility, case)
        with open("%s/start/ready.json" %test_directory, 'w') as f:
            f.write(readyjson)

        # copy the compose file
        shutil.copyfile(compose_file,test_directory + "/docker-compose-no-th.yml")
        with open(test_directory + "/run-test.py", 'w') as newf, open('run-test.py') as origf:
            for line in origf:
                newf.write(line.replace("random.randint(5,121)", "%s" %perturb_sleep))     
        #shutil.copyfile('run-test.py', test_directory+"/run-test.py")
        if case != 'a':
            # generate perturbation
            perturb_sh = PERTURB_SH
            if perturbs=="node":
                node=config.split('-')[0]
                noderep={"<NODE>" : node}
                node_perturb = multi_replace(PERTURB_NODEFAIL, noderep)
                perturb_sh = multi_replace(perturb_sh, {"#<NODE>" : node_perturb, "<SENSOR>" : "# NO SENSOR PERTURB"})
            elif perturbs=="sensor":
                node=config.split('-')[1]
                noderep={"<SENSOR>" : node}
                node_perturb = multi_replace(PERTURB_SENSOR, noderep)
                perturb_sh = multi_replace(perturb_sh, {"#<SENSOR>" : node_perturb, "<NODE>" : "# NO NODE PERTURB"})
            elif perturbs=="nodeandsensor":
                s = config.split('-')
                node=s[0]
                sensor=s[1]
                noderep={'#<NODE>' : node}
                node_perturb=multi_replace(PERTURB_NODEFAIL, noderep)
                srep={'#<SENSOR>' : sensor}
                sensor_perturb=multi_replace(PERTURB_SENSOR, srep)
                perturb_sh = multi_replace(perturb_sh, {"#<SENSOR>" : sensor_perturb, "#<NODE>" : node_perturb})
            if light_perturbs != "nolights":
                lights=c_map.lights_between_waypoints(route[corridor-1], route[corridor])
                light_p = ""
                for l in lights:
                    perturbation = multi_replace(PERTURB_LIGHTS, {'<LIGHT>' : l})
                    light_p = "%s\n%s" %(light_p,perturbation)
                perturb_sh = multi_replace(perturb_sh, {'#<LIGHTS>' : light_p})

            with open(test_directory + "/perturb.sh", 'w') as f:
                f.write(perturb_sh)
            os.chmod(test_directory + "/perturb.sh", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

parse_args = argparse.ArgumentParser()
parse_args.add_argument("-m", "--machines", type=int, help='Number of machines to spread across', default=1)
parse_args.add_argument("-i", "--ignore", nargs=1, action='append', help='Ignore the specified configuration')
parse_args.add_argument("-o", "--only", nargs=1, action='append', help='Generate only for for these specified configurations')
parse_args.add_argument('-l', "--lights", action="store_true", help='Force lights (for Aruco only)')
parse_args.add_argument('-r', "--reconfigs_none", action="store_true", help='Do not generate any reconfig perturbations')
parse_args.add_argument('-e', "--evaluation", action="store_true", help="Generated all test cases (A, B, C)")
parse_args.add_argument('num', type=int, help="number of tests (per machine) to generate")

args = parse_args.parse_args()

if args.ignore is not None:
    for c in args.ignore:
        for i in c:
            CONFIGS.remove(i)
if args.only is not None:
    del CONFIGS[:]
    for c in args.only:
        for i in c:
            CONFIGS.append(i)

if args.lights:
    LIGHT_PERTURBS=["lights"]

cases = ['a']

if args.evaluation:
    cases = ['a', 'b', 'c']

for m in range(args.machines):
    os.makedirs('machine%s' %m)
    for i in range(args.num):
        generate_test_case(os.path.expanduser('~/phase2/cmu-robotics/cp3/ta/docker-compose-no-th.yml'), path='machine%s' %m, only_lights=args.reconfigs_none, cases=cases)
    shutil.copyfile('run-all-tests.sh', 'machine%s/run-all-tests.sh' %m)
    os.chmod('run-all-tests.sh', stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)



