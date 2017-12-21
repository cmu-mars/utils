#! /user/bin/env python
'''
Given a BRASS map defined in JSON, add lights to the world using
either the waypoints in the map, or the lights defined by the map
'''
# Read in a map in the form of JSON and add a light at each waypoint
from __future__ import print_function

import argparse
from xml.dom.minidom import parse
import os
import sys
import json

def load_map(filename):
    '''
    Loads a json map from file and returns JSON
    '''
    f = open(filename)
    s = f.read()
    return json.loads(s)

def translate_waypoints_to_lights(map):
    waypoints = map["map"]
    lights = []
    curr_id = 0
    for wp in waypoints:
        light_id = 'light%s' % curr_id
        curr_id = curr_id + 1
        light_coord = wp["coords"]
        light = {'light-id' : light_id, 'coord' : light_coord}
        lights.append(light)

    return lights

def translate_map_to_gazebo(coords, x, y):
    t = {}
    t["x"] = coords["x"] + x
    t["y"] = coords["y"] + y
    return t

def create_light(dom, light_json, xtrans, ytrans, for_world=True):
    light = dom.createElement("light")
    light.setAttribute("name", light_json["light-id"])
    pose = dom.createElement("pose")
    pose.setAttribute("frame", "")
    gazebo_coords = translate_map_to_gazebo(light_json["coord"], xtrans, ytrans)
    pose_text = "%s %s 2 0 0 0" %(str(gazebo_coords["x"]), str(gazebo_coords["y"]))
    pose_t = dom.createTextNode(pose_text)
    pose.appendChild(pose_t)
    light.appendChild(pose)

    if for_world:
        light.setAttribute("type", "point")
        diffuse = dom.createElement("diffuse")
        diffuse.appendChild (dom.createTextNode("0.5 0.5 0.5 1"))
        light.appendChild(diffuse)

        specular = dom.createElement('specular')
        specular.appendChild(dom.createTextNode("0.1 0.1 0.1 1"))
        light.appendChild(specular)

        attenuation = dom.createElement ('attenuation')
        light.appendChild(attenuation)

        rangE = dom.createElement("range")
        rangE.appendChild(dom.createTextNode("5"))
        attenuation.appendChild(rangE)

        constant = dom.createElement("constant")
        constant.appendChild(dom.createTextNode("0.5"))
        attenuation.appendChild(constant)

        linear = dom.createElement("linear")
        linear.appendChild(dom.createTextNode("0.1"))
        attenuation.appendChild(linear)

        quadratic = dom.createElement("quadratic")
        quadratic.appendChild(dom.createTextNode("0.03"))
        attenuation.appendChild(quadratic)

        cast = dom.createElement("cast_shadows")
        cast.appendChild(dom.createTextNode("0"))
        light.appendChild(cast)

        direction = dom.createElement ("direction")
        direction.appendChild(dom.createTextNode("0 0 -1"))
        light.appendChild(direction)

    return light


parser = argparse.ArgumentParser()
parser.add_argument('-x', '--x-offset', type=float, default=-0.0, help='The x translation of coordinates in the map to the gazebo world')
parser.add_argument('-y', '--y-offset', type=float, default=0.0, help='The y translation of coordinates in the map to the gazebo world')
parser.add_argument('-w', '--use-waypoints', help='Use the waypoints to create the lights, otherwise use the light definitions in the map', action='store_true')
parser.add_argument('-u', '--update-map', help='After placing the lights, update the map', action='store_true')
parser.add_argument('--output-map', type=str, help='When updating the map, put it in this file')
parser.add_argument("--output-world", type=str, help='When updating the world, put it in this file')
parser.add_argument('map', help='The map file to use or update')
parser.add_argument('world', help='The gazebo world file to update')

args = parser.parse_args()

args.map = os.path.expandvars(args.map)
args.world = os.path.expandvars(args.world)

if not hasattr(args, 'output_map'):
	args.output_map = args.map

if not hasattr(args, 'output_world'):
	args.output_world = args.world

#Check if input files exist
if not os.path.isfile(args.map):
	print("The provided map file does not exist")
	sys.exit()

if not os.path.isfile(args.world):
	print('The provided world file does not exist')
	sys.exit()

world_dom = parse(args.world)

map_json = load_map(args.map)


if not "lights" in map_json or args.use_waypoints:
    lights = translate_waypoints_to_lights(map_json)
elif "lights" in map_json:
    lights = map_json["lights"]
else:
    lights = translate_waypoints_to_lights(map_json)


state = world_dom.getElementsByTagName("state")
world = world_dom.getElementsByTagName("world")

# Remove old lights
for node in state:
    for child in node.childNodes:
        if child.nodeName == "light":
            node.removeChild(child)

for node in world:
    for child in node.childNodes:
        if child.nodeName == "light":
            node.removeChild(child)


# Add lights - only need to add to world
for l in lights:
    world_light = create_light(world_dom, l, args.x_offset, args.y_offset)
    world[0].appendChild(world_light)


# output the new world
world_dom.writexml(open(args.output_world, 'w'), indent='  ', addindent='  ', newl='\n')
world_dom.unlink()

if args.update_map:
    map_json["lights"] = lights
    with open(args.output_map, 'w') as mapfile:
        json.dump(map_json, mapfile, indent=4)