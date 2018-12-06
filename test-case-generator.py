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
# The template of the ready message to create a test start config
READY_TEMPLATE='{"start-configuration" : "<CONFIG>", "start-loc" : "<START>", "target-loc" : "<TARGET>", "use-adaptation" : <ADAPT>, "utility-function" : "<UTILITY>"}'

# A template for the perturb json for running planner-only experiments
PERTURB_TEMPLATE ='{"path" : <PATH>, "perturb-loc" : "<PERTURB_LOC>", "perturb" : "<PERTURB>", "dark" : <DARK>, "fix-paths" : <FIX_PATHS>, "max-reconfs" : <MAX_RECONFIGS>, "cost" : <COST>, "balanced" : <BALANCED>}'

# The set of valid configurations
CONFIGS = ['amcl-kinect', 'amcl-lidar', 'mrpt-lidar', 'mrpt-kinect', 'aruco-camera']

# The set of configuration-based perturbations
PERTURBS = ["node", "sensor", "nodeandsensor", "none"]

# The set of light perturbations: lights mean include lights, lightsonly means ignore other perturbations, nolights means don't perturb the light
LIGHT_PERTURBS = ["lights", "lightsonly", "nolights", "nolights", "nolights"]

# A selection of waypoints to pick from as the source and target. Restricted here to those that might be "intersting tests", i.e., near dark
# or obstacle-ridden paths
INTERESTING_SRCS = ['l7', 'l28', 'l36', 'l29', 'l4', 'l37', 'l14', 'l13', 'l19', 'l39', 'l26', 'l27', 'l25', 'l11']
INTERESTING_TGTS = ['l34', 'l8', 'l9', 'l56', 'l3', 'l2', 'l15', 'l16', 'l17', 'l18', 'l21', 'l38', 'l47', 'l56', 'l55', 'l45', 'l42','l12']

# The preference functions to choose from
UTILITIES = ['favor-timeliness', 'favor-efficiency', 'favor-safety']

# How to issue each perturbation
PERTURB_NODEFAIL = 'curl -X POST http://localhost:8000/perturb/nodefail -d \'{"id" : "<NODE>"}\' -H "Content-Type:application/json"'
PERTURB_SENSOR = 'curl -X POST http://localhost:8000/perturb/sensor -d \'{"id" : "<SENSOR>", "state" : false}\' -H "Content-Type:application/json"'
PERTURB_LIGHTS = 'curl -X POST http://localhost:8000/perturb/light -d \'{"id" : "<LIGHT>", "state" : false}\' -H "Content-Type:application/json"'

# How to observe each information
OBSERVE = 'curl http://localhost:8000/observe'

# How to start a test
START='curl -X POST http://localhost:8000/start'

# The template to use when generating the perturbation script
PERTURB_SH = """#!/bin/sh
#<LIGHTS>
#<NODE>
#<SENSOR>
"""

# Where are the instructions and map - used for generating tests
INSTRUCTIONS_ALL = os.path.expanduser('~/catkin_ws/src/cp3_base/instructions/instructions-all.json')
MAP=os.path.expanduser("~/catkin_ws/src/cp3_base/maps/cp3.json")

MAX_RECONFIGS=2

inst_db = instruction_db.InstructionDB(INSTRUCTIONS_ALL)
c_map = map_server.MapServer(MAP)

# The set of known configurations (so that we don't randomly pick duplicate test cases)
configurations = set()
configurations.add("dummy")

planner_only = False

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
    """
    Generates teh ready message for a selected test case
    """
    rep = {"<CONFIG>" : config, "<START>" : src, "<TARGET>" : tgt, "<UTILITY>" : utility, "<ADAPT>" : "true" if case=='c' else "false"}
    ready = multi_replace(READY_TEMPLATE, rep)
    return ready

def get_config_info(only_lights=False, existing=None):
    """
    Randomly picks a test configuration that hasn't been seen before
    If only_lights is try, perturbs will be none and light perturbs will be lights only
    and we force the configuration to be aruco-camera
    Returns:
      config - the start configuration
      perturbs - the selection from PERTURBS
      lights - the selection for LIGHT_PERTURBS
      src - the starting waypoint
      tgt - the target waypoint
      utility - the preference function to use
    """
    configuration = "dummy"
    config = None
    perturbs = None
    src = None
    tgt = None
    utility = None
    path = None
    light_perturbs = "nolights"
    while configuration in configurations or (path is None or len(path) == 0) or (existing is not None and os.path.exists(existing + "testcase-%s-c" %configuration)):
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

def generate_icse_test_cases_planner(src, tgt, path='.', dry_run=False, allcombos=False):
    """
    Generates a case for all instances unders src -> tgt
    i.e., all utilities and configurations
    For the case where ony the planner is run
    Randomly choosing perturb and perturb location
    """
    newly_generated = 0
    perturbs = random.choice(PERTURBS)
    light_perturbs = random.choice(LIGHT_PERTURBS)
    if light_perturbs == 'lightsonly':
        light_perturbs='lights'
    for perturbs in PERTURBS:
        for light_perturbs in ["lights", "nolights"]:
            for c in CONFIGS:
                if perturbs != "none" or (light_perturbs=="lights" and c == "aruco-camera"):
                    for u in UTILITIES:
                        route = inst_db.get_path(src, tgt, u + "-" + c)
                        if len(route) == 0:
                            print("Warning, cannot find path between %s and %s under %s for preference %s" %(src,tgt,c,u))
                            continue
                        ploci = 0; #random.randint(1, len(route)-2)
                        ploc = route[ploci]
                        for a in range(1,MAX_RECONFIGS):
                            newly_generated = newly_generated + gen_planner_case('c', '%s-%s-%s-%s-%s-%s-%s-cost' %(c,perturbs,light_perturbs,src,tgt,u,a), path, c, perturbs, light_perturbs, src, tgt, u, route,a,True, ploc=ploc, dry=dry_run)
                            newly_generated = newly_generated + gen_planner_case('c', '%s-%s-%s-%s-%s-%s-%s-nocost' %(c,perturbs,light_perturbs,src,tgt,u,a), path, c, perturbs, light_perturbs, src, tgt, u, route,a,False, ploc=ploc, dry=dry_run)
                            newly_generated = newly_generated + gen_planner_case('c', '%s-%s-%s-%s-%s-%s-%s-cost-1' %(c,perturbs,light_perturbs,src,tgt,u,a), path, c, perturbs, light_perturbs, src, tgt, u, route,a,True, False, ploc=ploc, dry=dry_run)
                            newly_generated = newly_generated + gen_planner_case('c', '%s-%s-%s-%s-%s-%s-%s-nocost-1' %(c,perturbs,light_perturbs,src,tgt,u,a), path, c, perturbs, light_perturbs, src, tgt, u, route,a,False,False, ploc=ploc, dry=dry_run)
                            newly_generated = newly_generated + gen_planner_case('c', '%s-%s-%s-%s-%s-%s-%s-cost-fp' %(c,perturbs,light_perturbs,src,tgt,u,a), path, c, perturbs, light_perturbs, src, tgt, u, route,a,True, fix_path=True, ploc=ploc, dry=dry_run)
                            newly_generated = newly_generated + gen_planner_case('c', '%s-%s-%s-%s-%s-%s-%s-nocost-fp' %(c,perturbs,light_perturbs,src,tgt,u,a), path, c, perturbs, light_perturbs, src, tgt, u, route,a,False, fix_path=True, ploc=ploc, dry=dry_run)
                            newly_generated = newly_generated + gen_planner_case('c', '%s-%s-%s-%s-%s-%s-%s-cost-1-fp' %(c,perturbs,light_perturbs,src,tgt,u,a), path, c, perturbs, light_perturbs, src, tgt, u, route,a,True, False, fix_path=True, ploc=ploc, dry=dry_run)
                            newly_generated = newly_generated + gen_planner_case('c', '%s-%s-%s-%s-%s-%s-%s-nocost-1-fp' %(c,perturbs,light_perturbs,src,tgt,u,a), path, c, perturbs, light_perturbs, src, tgt, u, route,a,False,False, fix_path=True, ploc=ploc, dry=dry_run)
                       
    return newly_generated


def generate_icse_test_cases(src, tgt, compose_file, path='.', genab=True):
    """
    Generates a case for all instances unders src -> tgt
    i.e., all utilities and configurations
    For the case where the robot is run in simulation
    Randomly choosing perturb and perturb location
    """
    perturbs = random.choice(PERTURBS)
    light_perturbs = random.choice(LIGHT_PERTURBS)
    if light_perturbs == 'lightsonly':
        light_perturbs='lights'

    for c in CONFIGS:
        for u in UTILITIES:
            route = inst_db.get_path(src,tgt, u + "-" + c)
            if len(route) == 0:
                print("Warning, cannot find path between %s and %s under %s for preference %s" %(src,tgt,c,u))
                continue
            corridor=random.randint(1,len(route)-1)
            perturb_sleep = random.randint(1,inst_db.get_predicted_duration(src,tgt,"%s-%s" %(u,c)))
         
            for a in range(1,MAX_RECONFIGS):
                gen_case('c', '%s-%s-%s-%s-%s-%s-%s-cost' %(c,perturbs,light_perturbs,src,tgt,u,a),compose_file, path,
                    c, perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep,a,True)
                gen_case('c', '%s-%s-%s-%s-%s-%s-%s-nocost' %(c,perturbs,light_perturbs,src,tgt,u,a),compose_file, path,
                    c, perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep,a,False)
                gen_case('c', '%s-%s-%s-%s-%s-%s-%s-cost-1' %(c,perturbs,light_perturbs,src,tgt,u,a),compose_file, path,
                    c, perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep,a,True, False)
                gen_case('c', '%s-%s-%s-%s-%s-%s-%s-nocost-1' %(c,perturbs,light_perturbs,src,tgt,u,a),compose_file, path,
                    c, perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep,a,False, False)
                gen_case('c', '%s-%s-%s-%s-%s-%s-%s-cost-fp' %(c,perturbs,light_perturbs,src,tgt,u,a),compose_file, path,
                    c, perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep,a,True, fix_path=True)
                gen_case('c', '%s-%s-%s-%s-%s-%s-%s-nocost-fp' %(c,perturbs,light_perturbs,src,tgt,u,a),compose_file, path,
                    c, perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep,a,False, fix_path=True)
                gen_case('c', '%s-%s-%s-%s-%s-%s-%s-cost-1-fp' %(c,perturbs,light_perturbs,src,tgt,u,a),compose_file, path,
                    c, perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep,a,True, False,fix_path=True)
                gen_case('c', '%s-%s-%s-%s-%s-%s-%s-nocost-1-fp' %(c,perturbs,light_perturbs,src,tgt,u,a),compose_file, path,
                    c, perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep,a,False, False, fix_path=True)
            if genab:
                gen_case('a', "%s-%s-%s-%s-%s-%s" %(c,perturbs,light_perturbs,src,tgt,u),compose_file,path,
                    c,perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep)
                gen_case('b', "%s-%s-%s-%s-%s-%s" %(c,perturbs,light_perturbs,src,tgt,u),compose_file,path,
                    c,perturbs,light_perturbs,src,tgt,u,route,corridor,perturb_sleep)
           

def generate_test_case(compose_file, path = ".", only_lights=False, cases=['c'], existing=None):
    """
    Generates the test directories for a randomly selected test, in the specified cases
    At the end of this there will be a (set of) directory for each case that looks like
       + testcase-<config>/
       |--+start/
          |- ready.json
       |--+logs/
          |-- alloy/
          |-- prism/
       |--+roslogs/
       |--run-test.py (the test runner, BD TA)
       |--perturb.sh (the perturbation script)
    """
    # get the configuration
    id,config,perturbs,light_perturbs,src,tgt,utility, route = get_config_info(only_lights, existing)
    corridor = random.randint(1, len(route)-1)
    perturb_sleep = random.randint(1,inst_db.get_predicted_duration(src,tgt,"%s-%s" %(utility,config)))

    for case in cases:
        gen_case(case,id,compose_file,path,config,perturbs,light_perturbs,src,tgt,utility,route,corridor,perturb_sleep)

def set_up_directories(path,id,case,start,ros = True,dry=False):
    test_directory = "%s/testcase-%s-%s/" %(path,id,case)
    if os.path.exists(test_directory): return test_directory, True
    if dry:
        return test_directory, False
    os.makedirs(test_directory + start)
    os.makedirs(test_directory + "logs/prism")
    os.makedirs(test_directory + "logs/alloy")
    os.chmod(test_directory + "logs", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod(test_directory + "logs/prism", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod(test_directory + "logs/alloy", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    touch(test_directory + "logs/.INCLUDE_ME")

    if ros:
        os.makedirs(test_directory + "roslogs")
        os.chmod(test_directory + "roslogs", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        touch(test_directory + "roslogs/.INCLUDE_ME")
    return test_directory, False

def gen_planner_case(case, id, path, config, perturbs, light_perturbs, src, tgt, utility, route, num_adaptations=1,consider_cost=False,balanced_utility=True,fix_path=False, ploc=None, dry=False):
    test_directory, existed = set_up_directories(path, id, case, "params", False, dry)
    if existed: 
        return 0
    elif dry: 
        return 1
    readyjson = get_ready(config,src,tgt,utility,case)
    with open("%s/params/start.json" %test_directory, 'w') as f:
        f.write(readyjson)
    # PERTURB_TEMPLATE ='{"path" : <PATH>, "perturb-loc" : "<PERTURB_LOC>", "perturb" : "<PERTURB>", "dark" : <DARK>, "fix-paths" : <FIX_PATHS>, 
    # "max-reconfigs" : <MAX_RECONFIGS>, "cost" : <COST>, "balanced" : <BALANCED>}'
    rep={"<PATH>" : str(route), "<PERTURB_LOC>" : ploc, "<PERTURB>" : perturbs, "<DARK>" : "true" if light_perturbs == 'lights' else "false",
        "<FIX_PATHS>" : "true" if fix_path else "false", "<MAX_RECONFIGS>" : str(num_adaptations), "<COST>" : "true" if consider_cost else "false", "<BALANCED>" : "true" if balanced_utility else "false"}
    perturbjson = multi_replace(PERTURB_TEMPLATE, rep)
    with open("%s/params/perturb.json" %test_directory, 'w') as f:
        f.write(perturbjson)

    shutil.copyfile('icse.properties', '%s/params/properties.properties' %test_directory)
    return 1

def gen_case(case,id, compose_file, path,config,perturbs,light_perturbs,src,tgt,utility,route,corridor,perturb_sleep,num_adaptations=1,consider_cost=False, balanced_utility=True, fix_path=False):
    # create directory structure
    test_directory, existed = set_up_directories(path,id,case, "start")

    # create ready msg
    readyjson = get_ready(config,src,tgt,utility, case)
    with open("%s/start/ready.json" %test_directory, 'w') as f:
        f.write(readyjson)

    # copy the compose file
    # shutil.copyfile(compose_file,test_directory + "/docker-compose-no-th.yml")
    with open(compose_file) as origf, open(test_directory + "/docker-compose-no-th.yml",'w') as newf:
        for line in origf:
                newf.write(line)
                if 'ROS_MASTER_URI' in line:
                    newf.write('      - "MAX_RAINBOW_ADAPTATIONS=%s"\n' %num_adaptations)
                    newf.write('      - "CONSIDER_RECONFIGURATION_COST=%s"\n' %("false" if not consider_cost else "true"))
                    if not balanced_utility:
                        newf.write('      - "BALANCED_UTILITY=false"\n')
                    newf.write('      - "FIX_PATH=%s"\n' %("false" if not fix_path else "true"))
                if 'image: cmumars/p2-cp3' in line:
                    newf.write('    image: cmumars/p2-cp3:icse\n')

    # copy the test driver, but it currently ha a random wait for perturbation so fix it
    # here to ensure the same perturbation in b and c cases (otherwise the perturbs would happen 
    # at different times)
    with open(test_directory + "/run-test.py", 'w') as newf, open('run-test.py') as origf:
        for line in origf:
            newf.write(line.replace("random.randint(5,121)", "%s" %perturb_sleep))    
    

    if case != 'a':
        # generatecompose_file) as origf,  perturbation
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
            noderep={'<NODE>' : node}
            node_perturb=multi_replace(PERTURB_NODEFAIL, noderep)
            srep={'<SENSOR>' : sensor}
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
parse_args.add_argument('-d', "--existing", type=str, help='Do not duplicated the configuraionts in this directory')
parse_args.add_argument('-t', '--tasks', type=str, help="The file containing the lists of tasks (src,target) that should be generated")
parse_args.add_argument('--icse', action="store_true", help="Generate test cases for ICSE paper")
parse_args.add_argument('--planner-only', action="store_true", help='Generate scenarios to run the plan only')
parse_args.add_argument("--append", action="store_true", help='Append missing test cases to whatever exists, rather than overwriting')
parse_args.add_argument("--dry-run", action="store_true", help='Just report how many cases would be generated, but do not generate them')
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

if args.existing is not None:
    args.existing = os.path.expanduser(args.existing)

cases = ['a']

if args.evaluation:
    cases = ['a', 'b', 'c']

if args.tasks is not None:
    args.tasks = os.path.expanduser(args.tasks)
    with open(args.tasks) as f:
        content = f.readlines()
    tasks =[{'src' : s.split(',')[0].strip(), 'tgt': s.split(',')[1].strip()} for s in content]  
    if args.num == -1:
        args.num = len(tasks)   

if args.icse:
    if args.planner_only:
        created = 0
        for m in range(args.machines):
            if args.append and not os.path.exists('icse-planner%s' %m):
                os.makedirs('icse-planner%s' %m)
            elif not args.append:
                os.makedirs('icse-planner%s' %m)
            for i in range(args.num):
                created = created + generate_icse_test_cases_planner(tasks[0]['src'], tasks[0]['tgt'],path='icse-planner%s' %m, dry_run = args.dry_run)
                del tasks[0]
            if not args.dry_run:
                shutil.copyfile('run-icse-tests.sh', 'icse-planner%s/run-all-tests.sh' %m)
                os.chmod('icse-planner%s/run-all-tests.sh' %m, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            print("Created %s new test cases" %created)

    else:
        for m in range(args.machines):
            os.makedirs('icse-machine%s' %m)
            for i in range(args.num):
                generate_icse_test_cases (tasks[0]['src'], tasks[0]['tgt'], os.path.expanduser('~/phase2/cmu-robotics/cp3/ta/docker-compose-no-th.yml'), path='icse-machine%s' %m)
                del tasks[0]
            with open('run-all-tests.sh') as origf, open('icse-machine%s/run-all-tests.sh' %m,'w') as newf:
                for line in origf:
                    newf.write(line.replace("cmumars/p2-cp3", "cmumars/p2-cp3:icse")) 

            #shutil.copyfile('run-all-tests.sh', 'machine%s/run-all-tests.sh' %m)
            os.chmod('icse-machine%s/run-all-tests.sh' %m, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
else:
    for m in range(args.machines):
        os.makedirs('machine%s' %m)
        for i in range(args.num):
            generate_test_case(os.path.expanduser('~/phase2/cmu-robotics/cp3/ta/docker-compose-no-th.yml'), path='machine%s' %m, only_lights=args.reconfigs_none, cases=cases, existing=args.existing)
        shutil.copyfile('run-all-tests.sh', 'machine%s/run-all-tests.sh' %m)
        os.chmod('machine%s/run-all-tests.sh' %m, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)



