from __future__ import print_function
import json

def load_map(filename):
    '''
    Loads a json map from file and returns JSON
    '''
    f = open(filename)
    s = f.read()
    return json.loads(s)
