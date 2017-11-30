# utils
scripts that don't quite fit anywhere else -- be careful when adding something to this that you shouldn't be really making a new repo!

## generate-lights.py
This script takes a BRASS maps file and a Gazebo world corresponding
to the map, and adds point lights 2 meters above the ground plane. 
The lights to add can be taken from the lights attribute in the map file,
or generated to be above the waypoints. The world file (and map file) are
overwritten with the new data (unless the --output-x arguments are used)

```
usage: generate-lights.py [-h] [-x X_OFFSET] [-y Y_OFFSET] [-w] [-u]
                          [--output-map OUTPUT_MAP]
			  [--output-world OUTPUT_WORLD]
			  map world

positional arguments:
        map                   The map file to use or update
	world                 The gazebo world file to update

optional arguments:
	-h, --help            show this help message and exit
        -x X_OFFSET, --x-offset X_OFFSET
	  		      The x translation of coordinates in the map to the
	           	      gazebo world
	-y Y_OFFSET, --y-offset Y_OFFSET
	                      The y translation of coordinates in the map to the 
	                      gazebo world
        -w, --use-waypoints   Use the waypoints to create the lights, otherwise use
	                      the light definitions in the map
	-u, --update-map      After placing the lights, update the map
	--output-map OUTPUT_MAP
	                      When updating the map, put it in this file
	--output-world OUTPUT_WORLD
	                      When updating the world, put it in this file
```

