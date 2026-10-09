import js
import json
import asyncio
from pyodide.http import pyfetch
from pyodide.ffi import create_proxy

ALL_LICENSES = [
	"Avgi Atomics", "Avgi Torch", "Carrier", "City-Ship", "Coalition", "Cruiser",
	"Gegno Civilian", "Gegno Driller", "Heliarch", "Hicemus Conflict", "High Houses",
	"Militia", "Navy Auxiliary", "Navy Carrier", "Navy Cruiser", "Navy", "Pilot's",
	"Remnant Capital", "Remnant", "Scin Adjutant", "Scin Architect", "Scin Hoplologist",
	"Successor", "Twilight Guard", "Vi Centurion", "Vi Evocati", "Vi Lord", "Wanderer",
	"Wanderer Military", "Wanderer Outfits"
]

raw_content = ""
file_name = "savegame.txt"
current_ship_index = None
json_root_dict = {}
extracted_ships_by_cat = {}
all_global_ships = {}

state = {
	"pilotname": "", "date": "", "system": "", "planet": "",
	"prev_system": "", "prev_planet": "", "entry_method": "",
	"credits": 0, "reputations": {}, "licenses": set(), "ships": [], "plugins": []
}

def extract_ships_from_json(data_tree):
	categories = {}
	global all_global_ships
	all_global_ships = {}

	if not isinstance(data_tree, dict):
		return categories

	for cat_name, cat_content in data_tree.items():
		if not isinstance(cat_content, dict):
			continue

		ship_node = cat_content.get("ship")
		if isinstance(ship_node, dict):
			cat_ships = {}
			for ship_key, ship_data in ship_node.items():
				if isinstance(ship_data, dict) and "code" in ship_data:
					code_str = ship_data["code"]
					cat_ships[ship_key] = code_str
					all_global_ships[ship_key] = code_str
			
			if cat_ships:
				categories[cat_name] = cat_ships

	return categories

async def load_remote_ship_data():
	global json_root_dict, extracted_ships_by_cat
	cat_select = js.document.getElementById("add-ship-category")
	target_url = "https://raw.githubusercontent.com/zuckung/ES-DataParser/main/page/data.json"
	
	try:
		response = await pyfetch(target_url)
		if response.status == 200:
			json_root_dict = await response.json()
			extracted_ships_by_cat = extract_ships_from_json(json_root_dict)

			cat_select.innerHTML = '<option value="">-- Select Category / Race --</option>'
			for cat_key in sorted(extracted_ships_by_cat.keys()):
				opt = js.document.createElement("option")
				opt.value = cat_key
				opt.textContent = cat_key.replace('"', '')
				cat_select.appendChild(opt)
		else:
			cat_select.innerHTML = f'<option value="">Error {response.status} loading JSON</option>'
	except Exception as e:
		print(f"Fehler beim Laden der JSON: {e}")
		cat_select.innerHTML = '<option value="">Error loading data.json</option>'

def on_category_changed(event):
	cat_key = js.document.getElementById("add-ship-category").value
	model_select = js.document.getElementById("add-ship-model")
	add_btn = js.document.getElementById("add-ship-btn")
	preview_area = js.document.getElementById("add-ship-preview")
	
	model_select.innerHTML = '<option value="">-- Select Ship Model --</option>'
	preview_area.value = ""
	add_btn.disabled = True

	if not cat_key or cat_key not in extracted_ships_by_cat:
		model_select.disabled = True
		return

	ships_in_cat = extracted_ships_by_cat[cat_key]

	for ship_name in sorted(ships_in_cat.keys()):
		opt = js.document.createElement("option")
		opt.value = ship_name
		opt.textContent = ship_name.replace('"', '')
		model_select.appendChild(opt)

	model_select.disabled = False

def build_ship_syntax(selected_key, cat_key="", custom_name=""):
	raw_code = ""
	if cat_key and cat_key in extracted_ships_by_cat:
		raw_code = extracted_ships_by_cat[cat_key].get(selected_key, "")

	if not raw_code and selected_key in all_global_ships:
		raw_code = all_global_ships[selected_key]

	if not raw_code:
		return ""

	lines = raw_code.splitlines()
	first_line = lines[0] if lines else f'ship "{selected_key}"'

	# Prüfen, ob es sich um eine Variante handelt (z.B. ship "argosy" "argosy missiles")
	parts = first_line.split()
	base_ship_name = None
	if len(parts) > 2:
		base_ship_name = parts[1].strip('"')

	final_lines = []

	if base_ship_name and base_ship_name in all_global_ships:
		# Varianten-Logik: Hole das Basisschiff und ersetze den Header durch das reine Basisschiff
		base_code = all_global_ships[base_ship_name]
		base_lines = base_code.splitlines()
		
		# Verwende strikt den Header des Basisschiffs (ohne Varianten-Zusatz)
		final_lines.append(f'ship "{base_ship_name}"')
		
		# Name-Zeile
		if custom_name.strip():
			final_lines.append(f'\tname "{custom_name.strip()}"')
		else:
			final_lines.append('\tname ""')

		# Übernehme Zeilen des Basisschiffs und überschreibe/ergänze mit Varianten-Zeilen
		for line in base_lines[1:]:
			if line.strip().startswith("name "):
				continue
			final_lines.append(line)

		for line in lines[1:]:
			if line.strip().startswith("name "):
				continue
			final_lines.append(line)
	else:
		# Normales Schiff
		final_lines.append(first_line)
		
		if custom_name.strip():
			final_lines.append(f'\tname "{custom_name.strip()}"')
		else:
			final_lines.append('\tname ""')

		for line in lines[1:]:
			if line.strip().startswith("name "):
				continue
			final_lines.append(line)

	# Standort anhängen
	if state["system"]:
		final_lines.append(f'\tsystem "{state["system"]}"')
	if state["planet"]:
		final_lines.append(f'\tplanet "{state["planet"]}"')

	return "\n".join(final_lines)

def update_ship_preview(event=None):
	cat_key = js.document.getElementById("add-ship-category").value
	model_key = js.document.getElementById("add-ship-model").value
	custom_name = js.document.getElementById("add-ship-name").value
	preview_area = js.document.getElementById("add-ship-preview")
	add_btn = js.document.getElementById("add-ship-btn")

	if not model_key:
		preview_area.value = ""
		add_btn.disabled = True
		return

	code_preview = build_ship_syntax(model_key, cat_key, custom_name)
	preview_area.value = code_preview
	add_btn.disabled = False

def add_new_ship(event):
	global current_ship_index
	cat_key = js.document.getElementById("add-ship-category").value
	model_key = js.document.getElementById("add-ship-model").value
	custom_name = js.document.getElementById("add-ship-name").value
	
	if not model_key:
		return
		
	ship_code_block = build_ship_syntax(model_key, cat_key, custom_name)
	state["ships"].append(ship_code_block)
	
	render_ships_dropdown()
	new_index = len(state["ships"]) - 1
	js.document.getElementById("ship-select").value = str(new_index)
	
	current_ship_index = new_index
	js.document.getElementById("ship-code").value = ship_code_block
	js.document.getElementById("ship-details").style.display = "block"
	
	# HINWEIS: Dropdowns werden hier bewusst NICHT resettet, Positionen bleiben erhalten.
	js.document.getElementById("add-ship-name").value = ""
	js.document.getElementById("add-ship-preview.value") # no-op

def format_filesize(size_in_bytes):
	if size_in_bytes < 1024:
		return f"{size_in_bytes} B"
	elif size_in_bytes < 1024 * 1024:
		return f"{size_in_bytes / 1024:.1f} KB"
	else:
		return f"{size_in_bytes / (1024 * 1024):.2f} MB"

def parse_savegame(content):
	pilotname = date_str = system = planet = prev_system = prev_planet = entry_method = ""
	reputations = {}
	licenses = set()
	ships = []
	plugins = []
	
	current_ship_lines = []
	active_block = None

	for line in content.splitlines():
		if line.startswith("pilot "):
			pilotname = line[6:].strip().strip('"')
			continue
		elif line.startswith("date "):
			date_str = line[5:].strip()
			continue
		elif line.startswith("system "):
			system = line[7:].strip().strip('"')
			continue
		elif line.startswith("planet "):
			planet = line[7:].strip().strip('"')
			continue
		elif line.startswith('"previous system" '):
			prev_system = line[18:].strip().strip('"')
			continue
		elif line.startswith('"previous planet" '):
			prev_planet = line[18:].strip().strip('"')
			continue
		elif line.startswith('"system entry method" '):
			entry_method = line[22:].strip().strip('"')
			continue

		if line.startswith('"reputation with"') or line.startswith("reputation"):
			active_block = "reputation"
			continue
		elif line.startswith("licenses"):
			active_block = "licenses"
			continue
		elif line.startswith("# What you own:"):
			active_block = "ships"
			continue
		elif line.startswith("plugins"):
			active_block = "plugins"
			continue

		if not line.startswith("\t") and not line.startswith("ship ") and line.strip() != "":
			if active_block == "ships" and current_ship_lines:
				ships.append("\n".join(current_ship_lines))
				current_ship_lines = []
			active_block = None

		if active_block == "reputation" and line.startswith("\t"):
			parts = line.strip().rsplit(" ", 1)
			if len(parts) == 2:
				try:
					reputations[parts[0].strip('"')] = float(parts[1])
				except ValueError:
					pass

		elif active_block == "licenses" and line.startswith("\t"):
			licenses.add(line.strip().strip('"'))

		elif active_block == "plugins" and line.startswith("\t"):
			plugins.append(line.strip())

		elif active_block == "ships":
			if line.startswith("ship ") or line.startswith("\t"):
				if line.startswith("ship ") and current_ship_lines:
					ships.append("\n".join(current_ship_lines))
					current_ship_lines = []
				current_ship_lines.append(line)

	if current_ship_lines:
		ships.append("\n".join(current_ship_lines))

	credits_val = 0
	for line in content.splitlines():
		if line.startswith("\tcredits "):
			try:
				credits_val = int(line.strip().split(" ")[1])
			except (IndexError, ValueError):
				pass
			break

	return {
		"pilotname": pilotname, "date": date_str, "system": system, "planet": planet,
		"prev_system": prev_system, "prev_planet": prev_planet, "entry_method": entry_method,
		"credits": credits_val, "reputations": reputations, "licenses": licenses, 
		"ships": ships, "plugins": plugins
	}

async def process_file(event):
	global raw_content, file_name, state, current_ship_index
	
	file_list = event.target.files
	if file_list.length == 0:
		return
	
	file = file_list.item(0)
	file_name = file.name
	raw_content = await file.text()
	
	js.document.getElementById("file-name-display").textContent = file_name
	
	state = parse_savegame(raw_content)
	current_ship_index = None

	js.document.getElementById("info-pilot").textContent = state["pilotname"] or "N/A"
	js.document.getElementById("info-date").textContent = state["date"] or "N/A"
	js.document.getElementById("info-system").textContent = state["system"] or "N/A"
	js.document.getElementById("info-planet").textContent = state["planet"] or "N/A"
	js.document.getElementById("info-prev-system").textContent = state["prev_system"] or "N/A"
	js.document.getElementById("info-prev-planet").textContent = state["prev_planet"] or "N/A"
	js.document.getElementById("info-entry-method").textContent = state["entry_method"] or "N/A"
	js.document.getElementById("info-filesize").textContent = format_filesize(file.size)

	js.document.getElementById("credits-input").value = state["credits"]

	render_licenses_grid()
	render_reputations_tables()
	render_ships_dropdown()
	render_plugins_list()

	js.document.getElementById("status-container").style.display = "block"
	js.document.getElementById("editor-section").style.display = "block"
	js.document.getElementById("download-section").style.display = "none"

def render_licenses_grid():
	container = js.document.getElementById("license-checkbox-container")
	container.innerHTML = ""

	for lic in ALL_LICENSES:
		label_elem = js.document.createElement("label")
		label_elem.className = "license-checkbox"

		chk = js.document.createElement("input")
		chk.type = "checkbox"
		chk.value = lic
		chk.checked = lic in state["licenses"]
		chk.addEventListener("change", create_proxy(on_license_toggle))

		span_elem = js.document.createElement("span")
		span_elem.textContent = lic

		label_elem.appendChild(chk)
		label_elem.appendChild(span_elem)
		container.appendChild(label_elem)

def on_license_toggle(event):
	lic_name = event.target.value
	if event.target.checked:
		state["licenses"].add(lic_name)
	else:
		state["licenses"].discard(lic_name)

def render_reputations_tables():
	t1 = js.document.getElementById("reputations-table-1")
	t2 = js.document.getElementById("reputations-table-2")
	t3 = js.document.getElementById("reputations-table-3")
	t1.innerHTML = ""
	t2.innerHTML = ""
	t3.innerHTML = ""
	
	items = list(state["reputations"].items())
	total = len(items)
	
	col1_size = (total + 2) // 3
	col2_size = (total - col1_size + 1) // 2
	
	for idx, (faction, val) in enumerate(items):
		tr = js.document.createElement("tr")
		
		td_faction = js.document.createElement("td")
		td_faction.className = "faction-cell"
		td_faction.textContent = faction
		
		td_val = js.document.createElement("td")
		inp = js.document.createElement("input")
		inp.type = "number"
		inp.step = "any"
		inp.value = str(val)
		inp.dataset.faction = faction
		inp.addEventListener("change", create_proxy(on_reputation_change))
		
		td_val.appendChild(inp)
		tr.appendChild(td_faction)
		tr.appendChild(td_val)
		
		if idx < col1_size:
			t1.appendChild(tr)
		elif idx < col1_size + col2_size:
			t2.appendChild(tr)
		else:
			t3.appendChild(tr)

def render_plugins_list():
	container = js.document.getElementById("plugins-list-container")
	container.innerHTML = ""
	
	if not state["plugins"]:
		li = js.document.createElement("li")
		li.textContent = "No active plugins found in this savegame."
		li.style.listStyleType = "none"
		container.appendChild(li)
		return

	for plugin in state["plugins"]:
		li = js.document.createElement("li")
		li.textContent = plugin
		container.appendChild(li)

def render_ships_dropdown():
	ship_select = js.document.getElementById("ship-select")
	ship_select.innerHTML = '<option value="">-- Select owned ship --</option>'
	
	for idx, ship_block in enumerate(state["ships"]):
		first_line = ship_block.splitlines()[0] if ship_block.splitlines() else "ship"
		ship_label = first_line.replace('ship ', '').replace('"', '')
		
		for s_line in ship_block.splitlines():
			if s_line.startswith('\tname '):
				parts = s_line.strip().split(' ', 1)
				if len(parts) > 1:
					custom_name = parts[1].strip('"')
					if custom_name:
						ship_label = f"{ship_label} ({custom_name})"
				break
		
		option = js.document.createElement("option")
		option.value = str(idx)
		option.textContent = f"{idx + 1}. {ship_label}"
		ship_select.appendChild(option)

def on_reputation_change(event):
	faction = event.target.dataset.faction
	try:
		state["reputations"][faction] = float(event.target.value)
	except ValueError:
		pass

def save_current_ship_code_to_state():
	global current_ship_index
	if current_ship_index is not None and current_ship_index < len(state["ships"]):
		code_value = js.document.getElementById("ship-code").value
		state["ships"][current_ship_index] = code_value

def on_ship_selected(event):
	global current_ship_index
	save_current_ship_code_to_state()

	selected_value = event.target.value
	ship_details = js.document.getElementById("ship-details")
	
	if selected_value != "":
		current_ship_index = int(selected_value)
		js.document.getElementById("ship-code").value = state["ships"][current_ship_index]
		ship_details.style.display = "block"
	else:
		current_ship_index = None
		ship_details.style.display = "none"

def on_ship_code_input(event):
	save_current_ship_code_to_state()

def switch_tab(section_id):
	save_current_ship_code_to_state()
	
	js.document.getElementById("section-ships").style.display = "none"
	js.document.getElementById("section-reputations").style.display = "none"
	js.document.getElementById("section-licenses").style.display = "none"
	js.document.getElementById("section-plugins").style.display = "none"
	
	js.document.getElementById(section_id).style.display = "block"

def apply_changes(event):
	global raw_content, file_name, state
	
	save_current_ship_code_to_state()
	state["credits"] = js.document.getElementById("credits-input").value

	lines = raw_content.splitlines()
	updated_lines = []
	skip_block = False

	for line in lines:
		if line.startswith("\tcredits "):
			updated_lines.append(f'\tcredits {state["credits"]}')
			continue

		if line.startswith("licenses"):
			skip_block = True
			updated_lines.append("licenses")
			for lic in sorted(state["licenses"]):
				updated_lines.append(f'\t"{lic}"')
			continue

		if line.startswith('"reputation with"') or line.startswith("reputation"):
			skip_block = True
			updated_lines.append('"reputation with"')
			for faction, value in state["reputations"].items():
				updated_lines.append(f'\t"{faction}" {value}')
			continue

		if line.startswith("# What you own:"):
			skip_block = True
			updated_lines.append("# What you own:")
			for ship_block in state["ships"]:
				updated_lines.append(ship_block)
			continue

		if skip_block and not line.startswith("\t") and not line.startswith("ship ") and line.strip() != "":
			skip_block = False

		if not skip_block:
			updated_lines.append(line)

	updated_content = "\n".join(updated_lines)

	blob = js.Blob.new([updated_content], {type: "text/plain"})
	url = js.URL.createObjectURL(blob)
	
	download_link = js.document.getElementById("download-link")
	download_link.href = url
	download_link.download = file_name
	
	js.document.getElementById("download-section").style.display = "flex"

def handle_textarea_tab(event):
	if event.key == "Tab":
		event.preventDefault()
		textarea = event.target
		start = textarea.selectionStart
		end = textarea.selectionEnd

		textarea.value = textarea.value[:start] + "\t" + textarea.value[end:]
		textarea.selectionStart = textarea.selectionEnd = start + 1
		save_current_ship_code_to_state()

# Event Listener Binding
js.document.getElementById("file-input").addEventListener("change", create_proxy(process_file))
js.document.getElementById("ship-select").addEventListener("change", create_proxy(on_ship_selected))
js.document.getElementById("ship-code").addEventListener("input", create_proxy(on_ship_code_input))
js.document.getElementById("ship-code").addEventListener("keydown", create_proxy(handle_textarea_tab))

js.document.getElementById("add-ship-category").addEventListener("change", create_proxy(on_category_changed))
js.document.getElementById("add-ship-model").addEventListener("change", create_proxy(update_ship_preview))
js.document.getElementById("add-ship-name").addEventListener("input", create_proxy(update_ship_preview))
js.document.getElementById("add-ship-btn").addEventListener("click", create_proxy(add_new_ship))

js.document.getElementById("show-ships-btn").addEventListener("click", create_proxy(lambda e: switch_tab("section-ships")))
js.document.getElementById("show-rep-btn").addEventListener("click", create_proxy(lambda e: switch_tab("section-reputations")))
js.document.getElementById("show-lic-btn").addEventListener("click", create_proxy(lambda e: switch_tab("section-licenses")))
js.document.getElementById("show-plug-btn").addEventListener("click", create_proxy(lambda e: switch_tab("section-plugins")))

js.document.getElementById("save-btn").addEventListener("click", create_proxy(apply_changes))

# JSON laden
asyncio.ensure_future(load_remote_ship_data())
