#!/usr/bin/env python3

import argparse
import glob
import sys

from pathlib import Path

def eprint(args):
	print(args, file=sys.stderr)

def get_all_import(filename):
	with open(filename, 'rt') as f:
		lines = f.readlines()

	import_lines = []
	for line in lines:
		if line.strip().startswith('import'):
			try:
				# remove import
				new_line = line[len('import')+1:].strip()
				# remove static
				if new_line.startswith('static'):
					new_line = new_line[len('static')+1:].strip()
			except:
				pass

			if len(new_line) > 1:
				import_lines.append(new_line[:-1])

	return import_lines

length_dict = {}

def build_length_dict():
	length_dict['jenkins'] = 1
	length_dict['org'] = 2
	length_dict['com'] = 2
	length_dict['io'] = 2
	length_dict['hudson'] = 2
	length_dict['javax'] = 2

excluded_list = ['jenkins', 'kohsuke', 'mockito', 'slf4j']
def cut_package_names(targets):
	to_be_returned = []
	included_dict = {}
	for target in targets:
		_continue = False
		for excluded in excluded_list:
			if excluded in target:
				_continue = True
		if 'jenkins' in target and (not target.startswith('jenkins')):
			_continue = False
		if _continue:
			continue
		assert len(target) > 0
		split = target.split('/')
		if (not 'mockito' in target) and len(split) > 1:
			if split[0] in length_dict:
				cut_length = length_dict[split[0]]
				if len(split) > cut_length:
					target_package = '/'.join(split[:cut_length]) + '/'
					if not target_package in included_dict:
						to_be_returned.append(target_package)
						included_dict[target_package] = 1
				else:
					if not target in included_dict:
						to_be_returned.append(target)
						included_dict[target] = 1
			eprint(split)
		else:
			if not target in included_dict:
				to_be_returned.append(target)
				included_dict[target] = 1
	return list(set(to_be_returned))

def get_instrument_target_list(imports):
	# exclude
	excluded_list = [	'org/team_atlanta',	# our binary argument loader
						'java/',			# java core classes
					]
	instrument_targets = []
	included_dict = {}
	for import_line in imports:
		# replace . to /
		slash_import_line = '/'.join(import_line.split('.'))
		# remove *
		if slash_import_line[-1] == '*':
			slash_import_line = slash_import_line[:-1]
		excluded = False
		for excluded_item in excluded_list:
			if slash_import_line.startswith(excluded_item):
				excluded = True
		if not excluded:
			target = slash_import_line
			if not target in included_dict:
				instrument_targets.append(target)
				included_dict[target] = 1


	return cut_package_names(instrument_targets)

def parse_args():
	parser = argparse.ArgumentParser(description='Concolic Executor for Jazzer')
	parser.add_argument('-c', '--harness-class',
						type=str, help='harness class')
	parser.add_argument('-d', '--harness-directory',
						type=str, help="directory that contains harness")

	return parser.parse_args()

def main():
	args = parse_args()
	build_length_dict()

	harness_class_directory = Path(args.harness_directory)
	harness_all_directory = harness_class_directory.parent.absolute()
	harness_class = args.harness_class

	eprint(f'harness_class_directory : {harness_class_directory}')
	eprint(f'harness_class : {harness_class}')
	eprint(f'harness_all_directory : {harness_all_directory}')

	glob_string = f'{harness_all_directory}/**/{harness_class}.java'
	g = glob.glob(f'{harness_all_directory}/**/{harness_class}.java', recursive=True)
	eprint(f'glob_string {glob_string}')
	java_files = list(g)
	eprint(java_files)

	assert len(java_files) > 0

	java_file = java_files[0]

	imports = get_all_import(java_file)
	instrument_targets = get_instrument_target_list(imports)

	print(':'.join(instrument_targets))


if __name__ == '__main__':
	main()
