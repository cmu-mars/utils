import time
import subprocess
import threading
import os
import random
OBSERVE = 'curl http://localhost:8000/observe'

start_time = time.time()


def file_contains(file, contents):
    if not os.path.isfile(file):
        return False
    with open(file, 'r') as f:
        for line in f:
            if contents in line:
                return True
    return False

def timed_out():
    to = time.time() - start_time > 30 * 60
    if to:
        with open('logs/th_error', 'a') as f:
            f.write('Test timed out without finishing: %s, %s, %s' %(start, time.time(), time.time()-start_time))
    return to

def start_and_perturb():
    perturbed = False
    while not perturbed and not timed_out():
        sleep = 5
        if (file_contains("logs/TA_access.log", "'status': 'live'")):
            with open('logs/th_log', 'a') as so, open('logs/th_error', 'a') as se:
                print('starting experiment')
                s = subprocess.Popen(["curl", "-X", "POST", "http://localhost:8000/start"], stdout=so, stderr=se)
                s.wait()
            if os.path.isfile("./perturb.sh"):
                sleep = random.randint(5,121)
                print("Waiting %s seconds to perturb" %sleep)
                time.sleep(sleep)
                print('perturbing experiment')
                with open('logs/th_log', 'a') as so, open('logs/th_error', 'a') as se:
                    s = subprocess.Popen('./perturb.sh', shell=True, stdout=so, stderr=se)
                    s.wait()
            else:
                print("Not perturbing")
            perturbed = True
        time.sleep(1)

def wait_for_finish():
    done = False
    while not done and not timed_out():
        if (file_contains("logs/TA_access.log", "Done message is")):
            done = True
        with open('logs/th_log', 'a') as so, open('logs/th_error', 'a') as se:
            s = subprocess.Popen(["curl","http://localhost:8000/observe"], stdout=so,stderr=se)
            s.wait()
        time.sleep(1)
    with open("logs/th_log", "a") as so, open("logs/th_error", "w") as se:
        if done:
            so.write('Got done message, cleaning up')
        decompose = subprocess.Popen('TA_PORT=8000 START=/start/ready.json docker-compose -f docker-compose-no-th.yml down', shell=True, stdout=so, stderr=se)
        decompose.wait()
        decompose = subprocess.Popen('TA_PORT=8000 START=/start/ready.json docker-compose -f docker-compose-no-th.yml kill', shell=True, stdout=so, stderr=se)
        decompose.wait()
        time.sleep(30)


go = True
# launch docker compose
with open("logs/th_log", "a") as so, open("logs/th_error", "w") as se:
    try:
        compose = subprocess.Popen('TA_PORT=8000 START=/start/ready.json docker-compose -f docker-compose-no-th.yml up', shell=True, stdout=so, stderr=se)
        time.sleep(5)
        rcode = compose.poll()
        if rcode is not None and rcode != 0:
            print("Error in composition %s" %rcode)
            raise Exception()
        print("successfully called compose")
        time.sleep(30)
    except:
        go = False
        decompose = subprocess.Popen('TA_PORT=8000 START=/start/ready.json docker-compose -f docker-compose-no-th.yml down', shell=True, stdout=so, stderr=se)
        decompose.wait()
        decompose = subprocess.Popen('TA_PORT=8000 START=/start/ready.json docker-compose -f docker-compose-no-th.yml kill', shell=True, stdout=so, stderr=se)
        decompose.wait()
        time.sleep(30)
if go:
    print("Setting off threads")
    # launch thread to monitor ready (i.e., when the file contains the right message)
    start = threading.Thread(target=start_and_perturb)
    done = threading.Thread(target=wait_for_finish)
    start.start()
    done.start()

