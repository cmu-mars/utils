#! /user/bin/env python
'''
Given a BRASS map defined in JSON, add lights to the world using
either the waypoints in the map, or the lights defined by the map
'''
# Read in a map in the form of JSON and add a light at each waypoint
from __future__ import print_function

import argparse
from xml.dom.minidom import parse, parseString
import os
import sys
import json
import re
import math

wall_xml = """<link name='WALL_NAME'>
        <collision name='WALL_NAME_Collision'>
          <geometry>
            <box>
              <!-- <size>SIZE</size> -->
            </box>
          </geometry>
          <pose >0 0 1.25 0 -0 0</pose>
          <max_contacts>10</max_contacts>
          <surface>
            <contact>
              <ode/>
            </contact>
            <bounce/>
            <friction>
              <ode/>
            </friction>
          </surface>
        </collision>
        <visual name='WALL_NAME_Visual'>
          <pose >0 0 1.25 0 -0 0</pose>
          <geometry>
            <box>
              <!-- <size>SIZE</size> -->
            </box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
            <ambient>1 1 1 1</ambient>
          </material>
        </visual>
        <!-- <pose >POSE</pose> -->
        <self_collide>0</self_collide>
        <kinematic>0</kinematic>
        <gravity>1</gravity>
      </link>"""

def load_map(filename):
	f = open(filename)
	s = f.read()
	return json.loads(s)

def create_wall(id, x1, y1, x2, y2, origin=None, target=None):
	wall_dom = parseString(wall_xml)
	wall_id = "Wall_%s" %id
	if x1 > x2 or y1 > y2:
		xt = x1
		yt = y1
		x1 = x2
		y1 = y2
		y2 = yt
		x2 = xt
	x = math.sqrt((x2-x1)**2 + (y2-y1)**2)
	if x == 0 or math.isnan(x):
		return None

	if not target is None and not origin is None:
		wall_id = "Wall_%sto%s_%s" %(origin,target,id)
	link = wall_dom.getElementsByTagName("link")[0]
	link.setAttribute("name", wall_id)

	collision = wall_dom.getElementsByTagName("collision")[0]
	collision.setAttribute("name","%s_Collision" %wall_id)

	box = collision.getElementsByTagName("box")[0]
	size = wall_dom.createElement("size")

	z = 2.5
	y = 0.15

	size.appendChild(wall_dom.createTextNode("%s %s %s" %(x, y, z)))
	box.appendChild(size)

	visual = wall_dom.getElementsByTagName("visual")[0]
	visual.setAttribute("name", "%s_Visual" %wall_id)
	box = visual.getElementsByTagName("box")[0]
	size = wall_dom.createElement("size")

	size.appendChild(wall_dom.createTextNode("%s %s %s" %(x, y, z)))
	box.appendChild(size)

	pose = wall_dom.createElement("pose")
	z_angle = math.atan2(y2-y1, x2-x1)
	x_orig = (x1+x2)/2 + 4.95;
	y_orig = (y1+y2)/2;

#	if (z_angle == -math.pi or z_angle == math.pi):
#		x_orig = x1
#		y_orig = y1
	print ("%s has starting point (%s, %s) oriented %s deg with length %s"%(wall_id, x_orig, y_orig, math.degrees(z_angle), x))
	pose.appendChild(wall_dom.createTextNode("%s %s 0 0 0 %s" %(x_orig, y_orig,z_angle))) #((x1 + x2)/2, (y1 + y2)/2, z_angle)))
	link.appendChild(pose)
	return wall_dom

def get_walls_use_waypoints(map_json):
	waypoints = {}
	reverse_walls = []
	for wp in map_json["map"]:
		waypoint = {}
		waypoint["p"] = {}
		waypoint["p"]["x"] = wp["coord"]["x"]
		waypoint["p"]["y"] = wp["coord"]["y"]
		waypoint["connects"] = wp["connected-to"]
		waypoints[wp["node-id"]] = waypoint

	walls = []
	for wpo in waypoints:
		p1 = waypoints[wpo]["p"]
		for tl in waypoints[wpo]["connects"]:
			wpt = waypoints[tl]
			p2 = wpt["p"]
			key = "%s %s %s %s" %(p2["x"], p2["y"], p1["x"], p1["y"])
			if not  key in reverse_walls:
				reverse_walls.append("%s %s %s %s" %(p1["x"], p1["y"], p2["x"], p2["y"]))
				wall = {}
				wall["p1"] = p1
				wall["p2"] = p2
				wall["origin"] = wpo
				wall["target"] = tl
				walls.append(wall)

	return walls

def get_walls_from_map(map_json):
	walls = map_json["walls"]
	return walls

def process_world(models, append):
	cur_wall_id = 0

	room_model = None

	for model in models:
		for node in model.childNodes:
			if node.nodeName == "link":
				name = node.getAttribute("name")
				wall_result = re.match('Wall_([0-9]+)', name)
				if wall_result:
					room_model = model
					if not append:
						model.removeChild(node)
					else:
						wall_id = int(wall_result.group(1))
						if (wall_id > cur_wall_id):
							cur_wall_id = wall_id

	return cur_wall_id, room_model


parser = argparse.ArgumentParser()
parser.add_argument('-x', '--x-offset', type=float, default=-56.0, help='The x translation of coordinates in the map to the gazebo world')
parser.add_argument('-y', '--y-offset', type=float, default=-42.0, help='The y translation of coordinates in the map to the gazebo world')
parser.add_argument('-a', '--append', action='store_true', help='Append the walls rather than overwrite' )
parser.add_argument('-o', '--output', type=str, help='The output file to use')
parser.add_argument('map', help='The map file used to create the walls')
parser.add_argument('world', help='The gazebo file to use as the basis')

args = parser.parse_args()

args.map = os.path.expandvars(args.map)
args.world = os.path.expandvars(args.world)

if not hasattr(args, 'output'):
	args.output = args.map
else:
	args.output = os.path.expandvars(args.output)

# Check if input files exist
if not os.path.isfile(args.map):
	print("The provided map file does not exist")
	sys.exit()

if not os.path.isfile(args.world):
	print("The provided world file does not exist")
	sys.exit()

world_dom = parse(args.world)

models = world_dom.getElementsByTagName("model")

(cur_wall_id, room_model) = process_world(models, args.append)


map_json = load_map(args.map)

walls = get_walls_from_map(map_json)
walls_doms = []



for wall in walls:
	wall_dom = create_wall(cur_wall_id, wall["p1"]["x"] + args.x_offset, wall["p1"]["y"] + args.y_offset, wall["p2"]["x"] + args.x_offset, wall["p2"]["y"] + args.y_offset)
	if wall_dom is not None:
		cur_wall_id = cur_wall_id + 1
		room_model.appendChild(wall_dom.firstChild)


with open(args.output, 'w') as f:
	world_dom.writexml(f, indent='  ', addindent='  ', newl='\n')
	world_dom.unlink()