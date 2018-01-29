#!/bin/bash

if [ "$#" -ne 3 ]; then
	echo "Usage: $0 <MAP_JSON_DATA> <SOURCE_WORLD> <OUTPUTDIR>"
	exit 1
fi

json=$1
world=$2
output=$3


if [ ! -e "$json" ]; then
	echo "The file '$json' does not exist"
	exit 1
fi

if [ ! -e "$world" ]; then
	echo "The file '$world' does not exist"

if [ ! -d "$output" ]; then
	echo "The directory '$output' does not exist"
	exit 1
fi

python generate-walls.py -o /tmp/wall-world.world $json $world && \
python generate-lights.py --output-world $world $json /tmp/wall-world.world && \
python generate-ros-map.py -s 10 -l 1 -v $output/maps/markers.json -o $output/maps $data cp3

rm /tmp/wall-world.world

  

