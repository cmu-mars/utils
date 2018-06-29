""" utility functions for working with waypoints and maps """
### imports
from __future__ import with_statement
import json
import math

class MapServer():

    lights = None

    def __init__(self, map_file):
        with open(map_file) as wp:
            data = json.load(wp)
            self.waypoint_list = data["map"]
            if 'lights' in data:
                self.lights = data["lights"]
                self.light_db = {}


    def waypoint_to_coords(self, waypoint_id):
        """ given a way point, produce its coordinates """
        if not self.is_waypoint(waypoint_id):
            raise KeyError('The specified waypointID does not exist')
        waypoint_list = self.get_waypoint(waypoint_id)
        waypoint = waypoint_list[0]
        return waypoint['coord'] if 'coord' in waypoint  else waypoint['coords']

    def is_waypoint(self, waypoint_id):
        """ given a string, determine if it is actually a waypoint id """
        waypoint_list = self.get_waypoint(waypoint_id)
        if len(waypoint_list) > 1:
            raise ValueError('non-unique waypoint identifiers in the map file')
        return len(waypoint_list) == 1


    def get_waypoint(self, waypoint_id):
        l = [x for x in self.waypoint_list if x["node-id"]==waypoint_id]  #filter(lambda waypoint: waypoint["node-id"] == waypoint_id, self.waypoint_list)
        return l

    def __coords_on_line(self, x, y, sx, sy, ex, ey):
        tolerance = 2
        L2 = ( ((ex-sx) * (ex-sx)) + ((ey-sy) * (ey-sy)));
        if (L2 == 0):
            return False;
        r = (((x - sx) * (ex - sx)) + ((y - sy) * (ey - sy)))/L2;
        if (r < 0):
            return (math.sqrt(((sx - x) * (sx - x)) + ((sy - y) * (sy -y))) <= tolerance)
        elif ((0 <= r) and (r <= 1)):
            s = (((sy - y) * (ex - sx)) - ((sx - x) * (ey - sy))) / L2;
            return (math.fabs(s) * math.sqrt(L2) < tolerance);
        else:
            return (math.sqrt(((ex - x) * (ex-x)) + ((ey -y) * (ey-y))) <= tolerance);
        return False

    def lights_between_waypoints(self, wp1, wp2):
        if self.lights is None:
            return []

        waypoint = self.get_waypoint(wp1)
        if len(waypoint) == 0:
            return []
        waypoint = waypoint[0]

        if wp2 not in waypoint["connected-to"]:
            return []

        if wp1 + "_" + wp2 in self.light_db:
            return self.light_db[wp1 + "_" + wp2]
        elif wp2 + "_" + wp1 in self.light_db:
            return self.light_db[wp2 + "_" + wp1]
        else:
            lights = []
            waypoint2 = self.get_waypoint(wp2)
            if len(waypoint2) == 0:
                return []
            waypoint2 = waypoint2[0]
            for light in self.lights:
                if self.__coords_on_line(light["coord"]["x"], light["coord"]["y"],
                                    waypoint["coords"]["x"], waypoint["coords"]["y"],
                                    waypoint2["coords"]["x"], waypoint2["coords"]["y"]):
                    lights.append(light["light-id"])
            return lights

    def lights_on(self):
        if self.lights is None:
            return []
        off = []
        for light in self.lights:

            if "status" in light and light["status"]=="on":
                off.append(light["light-id"])
        return off

    def lights_off(self):
        if self.lights is None:
            return []
        off = []
        for light in self.lights:

            if "status" in light and light["status"]=="off":
                off.append(light["light-id"])
        return off

    def is_light(self,name):
        if self.lights is None:
            return False
        for light in self.lights:
            if light["light-id"] == name:
                return True
        return False
