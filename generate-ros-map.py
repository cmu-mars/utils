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
	parser.add_argument('-s', '--scale', type=int, default=10, help='The size of the image to scale to')
	parser.add_argument('-o', '--output_dir', help='The output directory for ROS map files')
	parser.add_argument('map_data', help='The JSON map file to use to base the ROS map on')
	parser.add_argument('ros_mapname', help='The prefix for map related ROS files')
	parser.add_argument('-c', '--create', action='store_true', help='Create output dir if it does not exist')
	parser.add_argument('-l' , '--line_width', type=int, default = 3, help='The width of wall lines')
	parser.add_argument('-v', '--visual_marker_data', help='THe file to output marker data to')
	parser.add_argument('-w', '--view', action='store_true', help="View the image (with markers) after processing")
	parser.add_argument('-b', '--obstacles', action='store_true', help="Generate obstacles on the map")
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
		l = (int (math.floor((tx + wall["p1"]["x"]) * scale)), int(math.floor((ty + wall["p1"]["y"]) * scale)), 
			int(math.floor((tx + wall["p2"]["x"]) * scale)), int(math.floor((ty + wall["p2"]["y"]) * scale)))
		draw.line (l, 
			fill = 'black', width=line_width)

def draw_obstacles(draw, map, scale, line_width, tx, ty):
	obstacles = map["worldobstacles"]
	for o in obstacles:
		draw.rectangle(
			[int(math.floor((tx + o["x"] - 0.2)*scale)),
			int(math.floor((ty + o["y"] - 0.2)*scale)),
			int(math.floor((tx + o["x"] + 0.2)*scale)),
			int(math.floor((ty + o["y"] + 0.2)*scale))],
			outline='black', fill='black')

def is_horizontal(wall):
	return math.fabs(wall["p1"]["y"] - wall["p2"].y) < 0.3

def inbounds(im, point):
	return point[0] >= 0 and point[0] <= im.width and point[1] >= 0 and point[1] <= im.height;

SOUTH = "south"
EAST = "east"
WEST = "west"
NORTH = "north"
MARKER_DISTANCE = 2.0

def construct_visual_marker_data(map_image, map_data, output, tx, ty, scale):
	corr_image = map_image.copy()
	# Assume origin is somewhere in a corridor
	ImageDraw.floodfill(corr_image, (tx * scale,ty * scale), (127, 127, 127))
	draw = ImageDraw.Draw(corr_image)
	marker_data = []
	mid = 0

	for wall in map_data["walls"]:
		dx = math.fabs(wall["p1"]["x"] - wall["p2"]["x"])
		dy = math.fabs(wall["p1"]["y"] - wall["p2"]["y"])
		numMarkers = int(math.floor(math.sqrt(dx*dx + dy*dy) / MARKER_DISTANCE) - 1);
		mm = [] # Contains the map coords of the markers
		mi = [] # Contains the image coords of the markers

		if numMarkers <= 0: # Wall is not enough for spacing markers, so place it in the middle
			p1 = [math.floor((wall["p1"]["x"] + tx)*scale), math.floor((wall["p1"]["y"] + ty)*scale)]
			p2 = [math.floor((wall["p2"]["x"] + tx)*scale), math.floor((wall["p2"]["y"] + ty)*scale)]

			mpi = (int(math.floor((p1[0] + p2[0])/2)), int(math.floor((p1[1] + p2[1])/2)))
			mpm = ((wall["p1"]["x"] + wall["p2"]["x"])/2, (wall["p1"]["y"] + wall["p2"]["y"])/2);
			mm.append(mpm)
			mi.append(mpi)
		else:
			incx = 0
			incy = 0
			# Add a marker close to the corner (0.25m away)
			sp = None
			ep = None
			if dy < 0.3:
				sp,ep = (wall["p1"],wall["p2"]) if wall["p1"]["x"] < wall["p2"]["x"] else (wall["p2"],wall["p1"])
				si = (int(math.floor((tx + sp["x"] + 0.35) * scale)), int(math.floor((ty + sp["y"]) * scale)))
				sm = (sp["x"] + 0.35, sp["y"])
				mm.append(sm)
				mi.append(si)

				ei = (int(math.floor((tx + ep["x"] - 0.35)*scale)), int(math.floor((ty + ep["y"])*scale)))
				em = (ep["x"] - 0.35, ep["y"])
				mm.append(em)
				mi.append(ei)
				incx = 1
			elif dx < 0.3:
				sp,ep = (wall["p1"],wall["p2"]) if wall["p1"]["y"] < wall["p2"]["y"] else (wall["p2"],wall["p1"])
				si = (int(math.floor((tx + sp["x"]) * scale)), int(math.floor((ty + sp["y"] + 0.35) * scale)))
				sm = (sp["x"], sp["y"] + 0.35)
				mm.append(sm)
				mi.append(si)

				ei = (int(math.floor((tx + ep["x"])*scale)), int(math.floor((ty + ep["y"] - 0.35)*scale)))
				em = (ep["x"], ep["y"] - 0.35)
				mm.append(em)
				mi.append(ei)
				incy = 1
			else:
				print ("Wall (%s,%s) (%s,%s) is neither vertical nor horizontal" %(wall["p1"]["x"],wall["p1"]["y"],wall["p2"]["x"],wall["p2"]["y"]))
			# Now add them along the wall
			for i in range(numMarkers):
				si = (int(math.floor((tx + sp["x"] + incx * MARKER_DISTANCE * (i+1))*scale)), 
					int(math.floor((ty + sp["y"] + incy * MARKER_DISTANCE * (i + 1))*scale)))
				sm = (sp["x"] + incx * MARKER_DISTANCE * (i + 1), sp["y"] + incy * MARKER_DISTANCE * (i + 1))
				mm.append(sm)
				mi.append(si)
		for idx, mpi in enumerate(mi):
			mpm = mm[idx]
			# Assume walls are vertical or horizontal for now
			
			if dy < 0.3:
				mpn = (mpi[0], mpi[1] +5)
				print(mpn)
				if (mpi[0] < 0 or mpi[0] > corr_image.width or mpi[1] + 5 > corr_image.height):
					continue
				if inbounds(corr_image, mpn):
					nr,ng,nb,na = corr_image.getpixel(mpn)
					if nr == 127:
						marker = {'id' : 'Marker%s' %mid, 'wall' : NORTH, 'x' : mpm[0], 'y' : mpm[1] + 0.1, 'translated' : True}
						marker_data.append(marker)
						mid = mid + 1
				mps = (mpi[0], mpi[1]-5)
				if inbounds(corr_image, mps):
					sr,sg,sb,sa = corr_image.getpixel(mps)
					if sr == 127:
						marker = {'id' : 'Marker%s' %mid, 'wall' : SOUTH, 'x' : mpm[0], 'y' : mpm[1] - 0.1, 'translated' : True}
						marker_data.append(marker)
						mid = mid + 1
			elif dx < 0.3:
				mpe = (mpi[0]+5, mpi[1])
				mpw = (mpi[0]-5, mpi[1])
				if inbounds(corr_image, mpe):
					r,g,b,a = corr_image.getpixel(mpe)
					if r == 127:
						marker = {'id' : 'Marker%s' %mid, 'wall' : WEST, 'x' : mpm[0] + 0.05, 'y' : mpm[1], 'translated' : True}
						marker_data.append(marker)
						mid = mid + 1
				if inbounds(corr_image, mpw):
					r,g,b,a = corr_image.getpixel(mpw)
					if r == 127:
						marker = {'id' : 'Marker%s' %mid, 'wall' : EAST, 'x' : mpm[0] - 0.125, 'y' : mpm[1], 'translated' : True}
						marker_data.append(marker)
						mid = mid + 1
			else:
				print("Warning: wall is neither horizontal or vertical")
				print(wall)
	return marker_data		


def draw_markers(scale, draw, md):
	for m in md:
		x = m["x"]
		y = m["y"]
		w = m["wall"]
		r = [0, 0,10, 10]
		if w == NORTH:
			r = [math.floor((tx + x) * scale) - 2, math.floor((ty + y) * scale), math.floor((tx + x)* scale) + 2, math.floor((ty + y)*scale) + 4]
		elif w == SOUTH:
			r = [math.floor((tx + x) * scale) - 2, math.floor((ty + y) * scale) -4, math.floor((tx + x)* scale) + 2, math.floor((ty + y)*scale)]
		elif w == EAST:
			r = [math.floor((tx + x) * scale - 4), math.floor((ty + y) * scale) -2, math.floor((tx + x)* scale), math.floor((ty + y)*scale)+2]
		elif w == WEST:
			r = [math.floor((tx + x) * scale), math.floor((ty + y) * scale) - 2, math.floor((tx + x)* scale) + 4, math.floor((ty + y)*scale) + 2]

		draw.rectangle(r, fill='black')		

args = process_args()

map_json = load_map(args.map_data)

tx, ty, width, height = get_map_bounding_box(map_json)
print ("transpose %s, %s size=%s %s" %(str(tx), str(ty), str(width), str(height)))

im = Image.new ('RGBA', (width * args.scale + args.line_width * args.scale, height*args.scale + args.line_width * args.scale), (255, 255, 255))
draw = ImageDraw.Draw(im)

draw_walls (draw, map_json, args.scale, int(math.ceil(0.15 * args.scale)), tx, ty)
md = {}

if args.visual_marker_data is not None:
	md = construct_visual_marker_data(im, map_json, args.visual_marker_data, tx, ty, args.scale)
	
	print("Produced %s markers" %len(md))
	with open(args.visual_marker_data, 'w') as vm:
		json.dump(md, vm, indent=4)


if args.obstacles:
	draw_obstacles(draw, map_json, args.scale, int(math.ceil(0.15 * args.scale)), tx, ty)

del draw



vi = None

if args.view:
	if args.visual_marker_data is not None:
		mi = im.copy()
		d = ImageDraw.Draw(mi)
		draw_markers(args.scale, d, md)
		vi = mi.transpose(Image.FLIP_TOP_BOTTOM)
		del d
	else:
		vi = im.transpose(Image.FLIP_TOP_BOTTOM)

im = im.transpose(Image.FLIP_TOP_BOTTOM)
width, height = im.size

im.save (args.output_dir + "/%s.png" %args.ros_mapname, "PNG")
# Save map.yaml too
with open(args.output_dir + "/%s.yaml" % args.ros_mapname, 'w') as mapfile:
	print('# Generated with generate-ros-map.y %s' %sys.argv[1:], file=mapfile)
	print('image: %s.png' %args.ros_mapname, file=mapfile)
	print('resolution: %s' %float(1.0/args.scale), file=mapfile)
	print('origin: [%s, %s, 0]' 
		%(-tx, -ty), 
		file=mapfile) # Assumes this is in meters not pixels
	print('occupied_thresh: 0.65', file=mapfile)
	print('free_thresh: 0.196', file=mapfile)
	print('negate: 0', file=mapfile)

if vi is not None:
	vi.show()