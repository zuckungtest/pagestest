import os
import json
from pathlib import Path


def read_everything(data_folder, folder_exclude):
	print('\nReading data folder...')
	obj, obj_path, obj_name = [], [], []

	# Get all text files
	text_files = []
	for root, dirs, files in os.walk(data_folder):
		# Apply directory exclusions
		for exclusion in folder_exclude:
			if exclusion in dirs:
				dirs.remove(exclusion)
		for file in files:
			if file.lower().endswith('.txt'):
				text_files.append(Path(root) / file)
				
	text_files.sort()

	for text_file in text_files:
		folder = text_file.parent.name
		file_name = text_file.name
		display_str = f" Reading: {folder}/{file_name}"
		padding = " " * max(0, 80 - len(display_str))
		print(display_str + padding, end='\r', flush=True)

		started = False
		txt, txt2, txt3 = "", "", ""

		with open(text_file, 'r', encoding='utf-8', errors='ignore') as source_file:
			lines = source_file.readlines()

		for line in lines:
			# Skip empty or full-comment lines
			if line.isspace() or line.lstrip().startswith('#'):
				continue

			# Remove inline comments (e.g. "outfit 'Laser' # comment")
			if '#' in line:
				pos = line.find('#')
				line = line[:pos].rstrip() + '\n'

			# Root-level node detection (no leading tab)
			if not line.startswith('\t'):
				if started and txt.strip():
					obj.append(txt)
					obj_path.append(txt2)
					obj_name.append(txt3.replace('\t', ' '))
				
				txt = line
				txt2 = str(text_file)
				txt3 = line.rstrip('\r\n')
				started = True
			else:
				if started:
					txt += line

		# FIX: Ensure the last node of the file is saved!
		if started and txt.strip():
			obj.append(txt)
			obj_path.append(txt2)
			obj_name.append(txt3.replace('\t', ' '))

	print('\n DONE')
	return obj, obj_path, obj_name


def build_full_es_data_json(obj_list, obj_path_list, obj_name_list, output_filename):
	"""
	Generates a complete JSON database containing all Endless Sky nodes.
	"""
	data_db = {}

	for code, raw_path, first_line in zip(obj_list, obj_path_list, obj_name_list):
		# 1. Clean path (strip everything preceding 'data/')
		path_str = str(raw_path).replace("\\", "/")
		if "data/" in path_str:
			rel_path = "data/" + path_str.split("data/", 1)[1]
		else:
			rel_path = path_str

		clean_path = Path(rel_path)
		
		# 2. Extract folder name as category/race
		category = clean_path.parent.name if clean_path.parent.name else "global"

		# 3. Extract node type and display name from first line
		clean_line = first_line.strip()
		parts = clean_line.split(" ", 1)
		
		node_type = parts[0].strip().lower() if len(parts) > 0 else "other"
		display_name = parts[1].strip().strip('"') if len(parts) > 1 else clean_line

		# Build nested dictionary hierarchy
		if category not in data_db:
			data_db[category] = {}
			
		if node_type not in data_db[category]:
			data_db[category][node_type] = {}

		# Save node entry
		data_db[category][node_type][display_name] = {
			"path": rel_path,
			"code": code.strip()
		}

	# Export formatted JSON database
	with open(output_filename, "w", encoding="utf-8") as f:
		json.dump(data_db, f, ensure_ascii=False, indent=2)

	print(f"Done! Saved {len(obj_list)} nodes into '{output_filename}'.")
	return data_db


if __name__ == '__main__':
	data_folder = 'd:/games/endless sky/data/'
	output_file = 'data.json'
	folder_exclude = []  # e.g., ['_deprecated', '_ui']
	
	obj, obj_path, obj_name = read_everything(data_folder, folder_exclude)
	build_full_es_data_json(obj, obj_path, obj_name, output_file)