import os
import sys
import json
import math
import subprocess

args = sys.argv

# check arguments
if len(args) != 4:
    print("\nError: Wrong arguments.\n")
    exit()
BLENDER_PATH = args[1]
JSON_PATH = args[2]
OUTPUT_FILE = args[3]
if os.path.splitext(BLENDER_PATH)[1] != ".exe" or \
    os.path.splitext(JSON_PATH)[1] != ".json" or \
        os.path.splitext(OUTPUT_FILE)[1] != ".mvs":
    print("\nError: Wrong arguments. Try again.")
    print("It must be \"path_to_blender\\blender.exe path_to_input_file.json pah_to_output.mvs\"")
    exit()

## read json and run export
with open(JSON_PATH, 'r') as f:
    data = json.load(f)

edm_files = []
for block in data:
    blend_path = block['filename']
    file_name, file_ext  = os.path.splitext(blend_path)
    dir_name = os.path.dirname(blend_path)
    edm_path = os.path.join(dir_name, f'{file_name}.edm')
    
    # run export
    print(f'-->start export to {file_name}.blend to {file_name}.edm')
    try:
        subprocess.run([BLENDER_PATH, '--background', blend_path, 
                        '--python-expr', 'import bpy;bpy.ops.edm.import_matrials();bpy.ops.edm.fast_export_dummy()'])
    except:
        print(f'ERROR: could not export {file_name}')
        exit()

    if not os.path.exists(edm_path):
        print(f'ERROR: {file_name}.edm was not created')
        exit()
    
    edm_files.append(edm_path)

## prepare .mvs file
delta = 8.0
        
objects_count = len(edm_files)
width = math.floor(math.sqrt(objects_count))
data = []
for i, filepath in enumerate(edm_files):
    x = i // width
    z = i - x * width

    data.append({
        'ModelPath': filepath,
        'position': {
            "ppx": x * delta,
            "ppy": 10001.349609375,
            "ppz": z * delta,
            "pxx": 1,
            "pxy": 0,
            "pxz": 0,
            "pyx": 0,
            "pyy": 1,
            "pyz": 0,
            "pzx": 0,
            "pzy": 0,
            "pzz": 1
        }        
    })
loaded_modules = {'LoadedModels': data}

with open(OUTPUT_FILE, 'w') as f:
    json.dump(loaded_modules, f, indent=2)