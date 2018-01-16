#! /user/bin/env python

from __future__ import print_function

import argparse
from xml.dom.minidom import parse
import os
import sys
import json
import math

def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, help='Write the new world to this file instead of overwriting "world"')
    parser.add_argument('world', type=str, help='The world file to update')
    parser.add_argument('data', type=str, help='The visual marker data')
    args = parser.parse_args()

    args.world = os.path.expandvars(args.world)
    args.data = os.path.expandvars(args.data)

    if not os.path.isfile(args.world):
        print('The provided world file "%s" does not exist' %args.world)
        sys.exit()

    if not os.path.isfile(args.data):
        print('The provided marker data file "%s" does not exist' %args.data)
        sys.exit()

    if args.output is None:
        args.output = args.world
    else:
        args.output = os.path.expandvars(args.output)


    return args

def create_marker(mid, dom, marker_json, height):
    markerXML = dom.createElement("model")
    markerXML.setAttribute("name", "Marker%s" %mid)
    static = dom.createElement("static")
    markerXML.appendChild(static)
    static.appendChild(dom.createTextNode("1"))
    link = dom.createElement("link")
    markerXML.appendChild(link)
    link.setAttribute("name", "link")

    visual = dom.createElement("visual")
    visual.setAttribute("name", "visual")
    link.appendChild(visual)

    geometry = dom.createElement("geometry")
    visual.appendChild(geometry)

    mesh = dom.createElement("mesh")
    geometry.appendChild(mesh)

    uri = dom.createElement("uri")
    uri.appendChild(dom.createTextNode("model://marker%s/meshes/Marker%s.dae" %(mid, mid)))
    mesh.appendChild(uri)

    self_collide = dom.createElement("self_collide")
    self_collide.appendChild(dom.createTextNode("0"))
    link.appendChild(self_collide)

    kinematic = dom.createElement("kinematic")
    kinematic.appendChild(dom.createTextNode("0"))
    link.appendChild(kinematic)

    on_wall = marker_json["wall"]
    # on_wall is the side of the corridor the wall in on, so if the wall is north
    # then the marker needs to be on the south side and twisted south so that it is
    # facing into the corridor

    x = marker_json["x"]
    y = marker_json["y"]
    z = height
    translate = "translated" not in keys or not marker_json["translated"]
    w = 0

    if on_wall == "north":
        if translate:
            y = y + 0.1
        w = -math.pi / 2
    elif on_wall == "south":
        if translate:
            y = y - 0.1
        w = math.pi / 2
    elif on_wall == "east":
        if translate:   
            x = x - 0.125
        w = math.pi
    elif on_wall == "west":
        if translate:
            x = x + 0.05
        w = 0
    else:
        print("Marker is not on a wall!?")

    pose_text = "%s %s %s 0 0 %s" %(x,y,z,w)
    pose = dom.createElement("pose")
    pose.setAttribute("frame", "")
    pose.appendChild(dom.createTextNode(pose_text))
    markerXML.appendChild(pose)

    # stateXML = dom.createElement("model")
    # pose = dom.createElement("pose")
    # stateXML.appendChild(pose)
    # pose.appendChild(dom.createTextNode(pose_text))

    # scale = dom.createElement("scale")
    # scale.appendChild(dom.createTextNode("1 1 1"))
    # stateXML.appendChild(scale)

    # link = dom.createElement('link')
    # link.setAttribute('name', 'link')
    # stateXML.appendChild(link)

    # pose = dom.createElement("pose")
    # pose.setAttribute('frame', '')
    # link.appendChild(pose)
    # pose.appendChild(dom.createTextNode(pose_text))

    # velocity = dom.createElement("velocity")
    # link.appendChild(velocity)
    # velocity.appendChild(dom.createTextNode("0 0 0 0 0 0"))
    # accel = dom.createElement("accelaration")
    # link.appendchild(accel)
    # accel.appendChild(dom.createTextNode("0 0 0 0 0 0"))
    # wrench = dom.createElement("") 

    return markerXML, None

def remove_old_markers(world, state):
    for child in world.childNodes:
        if child.nodeName == "model" and child.getAttribute("name").startswith("Marker"):
            world.removeChild(child)

    for child in state.childNodes:
        if child.nodeName == "model" and child.getAttribute("name").startswith("Marker"):
            state.removeChild(child)

def load_json(filename):
    f = open(filename)
    s = f.read()
    return json.loads(s)

if __name__ == '__main__':
    args = process_args()

    world_dom = parse(args.world)
    markers = load_json(args.data)

    world = world_dom.getElementsByTagName("world")[0]
    state = world_dom.getElementsByTagName("state")[0]

    remove_old_markers(world, state)

    mid = 0
    for marker in markers:
        vmm, vms = create_marker(mid, world_dom, marker, 0.75)
        mid = mid + 1
        world.appendChild(vmm)
        if mid > 50:
             break
        #state.appendChild(vms)

    world_dom.writexml(open(args.output, 'w'), indent='  ', addindent='  ', newl='\n')
    world_dom.unlink()