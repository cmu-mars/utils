""" utility functions for working with waypoints and maps """
### imports
from __future__ import with_statement
import json

class InstructionDB:

	def __init__(self, instruction_db):
		with open(instruction_db) as db:
			data = json.load(db)
			self.db = data

	def __form_key(self, wp_src, wp_tgt):
		key = "%s_to_%s" %(wp_src, wp_tgt)
		return key

	def get_path(self, wp_src, wp_tgt, config):
		key = self.__form_key(wp_src, wp_tgt)
		if key not in self.db:
			return None
		if config is None:
			config='amcl-kinect'
		return self.db[key][config]["path"]

	def get_instructions(self, wp_src, wp_tgt, config):
		key = self.__form_key(wp_src, wp_tgt)
		if key not in self.db:
			return None
		if config is None:
			config='amcl-kinect'
		return self.db[key][config]["instructions"]

	def get_predicted_duration(self, wp_src, wp_tgt, config):
		key = self.__form_key(wp_src, wp_tgt)
		if key not in self.db:
			return -1
		if config is None:
			config='amcl-kinect'
		return self.db[key][config]["time"]

	def get_start_heading(self, wp_src, wp_tgt, config):
		key = self.__form_key(wp_src, wp_tgt)
		if key not in self.db:
			return 0
		if config is None:
			config='amcl-kinect'
		return self.db[key][config]["start-dir"]

