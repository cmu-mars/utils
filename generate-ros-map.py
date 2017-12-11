#!/usr/bin/env python

from __future__ import print_function

import argparse
import errno
import os
import sys
import json
import math
from PIL import Image, ImageDraw

from map_utils import load_map


def get_map_bounding_box(map):
	ox = sys.maxint
	oy = sys.maxint
	tr_x = -sys.maxint - 1
	tr_y = tr_x

	walls = map["walls"]

	for wall in walls:
		p1 = wall["p1"]
		p2 = wall["p2"]
		ox = min(ox, float(p1["x"]), float(p2["x"]))
		oy = min(oy, float(p1["y"]), float(p2["y"]))
		tr_x = max(tr_x, float(p1["x"]), float(p2["x"]))
		tr_y = max(tr_y, float(p1["y"]), float(p2["y"]))

	tr_x = tr_x - ox
	tr_y = tr_y - oy

	print ("transpose %s, %s size=%s, %s" %(ox, oy, tr_x, tr_y))

	return int(math.ceil(-ox)), int(math.ceil(-oy)), int(math.ceil(tr_x)), int(math.ceil(tr_y))

def process_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-s', '--scale', type=int, default=1, help='The size of the image to scale to')
	parser.add_argument('-o', '--output_dir', help='The output directory for ROS map files')
	parser.add_argument('map_data', help='The JSON map file to use to base the ROS map on')
	parser.add_argument('ros_mapname', help='The prefix for map related ROS files')
	parser.add_argument('-c', '--create', action='store_true', help='Create output dir if it does not exist')
	parser.add_argument('-l' , '--line_width',default = 3, help='The width of wall lines')
	args = parser.parse_args()

	args.map_data = os.path.expandvars(args.map_data)

	if not hasattr(args, 'output_dir') or args.output_dir is None:
		args.output_dir = '.'

	args.output_dir = os.path.expandvars(args.output_dir)

	if not os.path.isfile(args.map_data):
		print('The provided map "%s" does not exist.' %args.map_data)
		sys.exit()

	if not os.path.isdir(args.output_dir) and not args.create:
		print('The output directory "%s" does not exist. Use -c to create it.' %args.output_dir)
		sys.exit()
	elif not os.path.isdir(args.output_dir):
		try:
			os.makedirs(args.output_dir)
		except OSError as exc:
			if exc.errno == errno.EEXIST and os.path.isdir(args.output_dir):
				pass
			else:
				raise
	return args

def draw_walls(draw, map, scale, line_width, tx, ty):
	walls = map["walls"]
	for wall in walls:
		l = (int (math.floor(tx + float(wall["p1"]["x"]))) * scale, int(math.floor(ty + float(wall["p1"]["y"]))) * scale, 
			int(math.floor(tx + float(wall["p2"]["x"]))) * scale, int(math.floor(ty + float(wall["p2"]["y"]))) * scale)
		draw.line (l, 
			fill = 'black', width=line_width)

		

args = process_args()

map_json = load_map(args.map_data)

tx, ty, width, height = get_map_bounding_box(map_json)
print ("transpose %s, %s size=%s %s" %(str(tx), str(ty), str(width), str(height)))

args.line_width = 3

im = Image.new ('RGBA', (width * args.scale + args.line_width * args.scale, height*args.scale + args.line_width * args.scale), (255, 255, 255))
draw = ImageDraw.Draw(im)

draw_walls (draw, map_json, args.scale, args.line_width, tx, ty)
del draw
im = im.transpose(Image.FLIP_TOP_BOTTOM)
im.save (args.output_dir + "/%s.png" %args.ros_mapname, "PNG")

# Save map.yaml too
with open(args.output_dir + "/map.yaml", 'w') as mapfile:
	print('image: %s.png' %args.ros_mapname, file=mapfile)
	print('resolution: %s' %float(1.0/args.scale), file=mapfile)
	print('origin: [%s, %s, 0]' 
		%(map_json["origin"][0]["x"] * args.scale, map_json["origin"][0]["y"] * args.scale), 
		file=mapfile)
	print('occupied_thresh: 0.65', file=mapfile)
	print('free_thresh: 0.196', file=mapfile)
	print('negate: 0', file=mapfile)

