import os.path
import re
import uuid
import pickle

import bpy
from typing import List, Union, Dict, Sequence, Tuple, Optional
from version_specific import InterfaceNodeSocket, get_version

from bpy.types import Operator, Material, ShaderNodeGroup, Action, FCurve, NodeTree, NodeSocket, Node, ShaderNode
from typing import List, Union, Dict, NamedTuple, Callable, Type

from utils import print_node, EDMPath
from enums import BpyShaderNode, NodeSocketInDefaultEnum, NodeGroupTypeEnum, get_node_group_types
from logger import log
from materials import Materials, build_material_descriptions, filter_materials, filter_materials_re, check_md5, get_material
from serializer import SNode, SOutput, SInput, SLink
from serializer_tools import collect_nodetree_links, extract_group_inputs, MatDesc, serialize_group
from material_wrap import get_edm_node_group, get_edm_node_group_re, get_list_edm_node_group_re, get_list_free_edm_node_group_re
from edm_materials import EdmMatrialShaderNode

def move_version(node: Node, ver: int):
    v = node.inputs.get('Version')
    if v:
        v.default_value = ver

def replace_materials(materials: List[Material], edm_group_name: str, new_group: NodeTree):
    for material in materials:
        for bpy_node in material.node_tree.nodes:
            if bpy_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and bpy_node.node_tree and bpy_node.node_tree.name == edm_group_name:
                loc = bpy_node.location
                bpy_node.node_tree = new_group
                bpy_node.location = loc

def replace_materials_re(mats: List[Material], edm_group_regex, new_tree: NodeTree, new_mat_desc: MatDesc):
    right_mat_list: List[Material] = [m for m in mats if m.use_nodes and m.node_tree]
    for material in right_mat_list:
        temp_nodes: List[ShaderNode] = material.node_tree.nodes[:]
        for bpy_node in temp_nodes:
            if bpy_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and bpy_node.node_tree and re.match(edm_group_regex, bpy_node.node_tree.name):
                loc = bpy_node.location
                width = bpy_node.width
                sel = bpy_node.select

                old_node_group: ShaderNodeGroup = bpy_node
                old_group_name: str = old_node_group.name
                old_group_lbl: str = old_node_group.bl_label
                old_node_group.name = old_node_group.name + str(uuid.uuid4())
                # new_node_group: ShaderNodeGroup = material.node_tree.nodes.new(type = BpyShaderNode.NODE_GROUP)
                # new_node_group: EdmMatrialShaderNode = material.node_tree.nodes.new(type = BpyShaderNode.NODE_GROUP_EDM)
                if(new_mat_desc.name == NodeGroupTypeEnum.DEFAULT):
                    new_node_group: EdmMatrialShaderNode = material.node_tree.nodes.new(type = BpyShaderNode.NODE_GROUP_DEFAULT)
                elif(new_mat_desc.name == NodeGroupTypeEnum.DECK):
                    new_node_group: EdmMatrialShaderNode = material.node_tree.nodes.new(type = BpyShaderNode.NODE_GROUP_DECK)
                elif(new_mat_desc.name == NodeGroupTypeEnum.FAKE_OMNI):
                    new_node_group: EdmMatrialShaderNode = material.node_tree.nodes.new(type = BpyShaderNode.NODE_GROUP_FAKE_OMNI)
                elif(new_mat_desc.name == NodeGroupTypeEnum.FAKE_SPOT):
                    new_node_group: EdmMatrialShaderNode = material.node_tree.nodes.new(type = BpyShaderNode.NODE_GROUP_FAKE_SPOT)
                else:
                    break
                new_node_group.post_init(new_mat_desc)
                #new_node_group.node_tree = new_tree
                new_node_group.name = old_group_name
                #new_node_group.bl_label = old_group_lbl
                if material.node_tree.animation_data and material.node_tree.animation_data.action:
                    for input_no in range(0, len(old_node_group.inputs)):
                        old_input: NodeSocket = old_node_group.inputs[input_no]
                        if not old_input.name in new_node_group.inputs:
                            continue
                        new_input: NodeSocket = new_node_group.inputs[old_input.name]
                        old_fc_data_path: str = old_input.path_from_id('default_value')
                        new_fc_data_path: str = new_input.path_from_id('default_value')
                        fc_list: Sequence[FCurve] = get_fc_list(material.node_tree.animation_data.action, old_fc_data_path)
                        for fc in fc_list:
                            fc.data_path = new_fc_data_path

                material.node_tree.nodes.remove(bpy_node)
                new_node_group.location = loc
                new_node_group.width = width
                new_node_group.select = sel

def move_links(mat: Material) -> List[SLink]:
    links: List[SLink] = []
    collect_nodetree_links(mat.node_tree, links)
    mat.node_tree.links.clear()
    return links

def restore_links(mat: Material, links: List[SLink]):
    for link in links:
        link.create(mat.node_tree, mat.node_tree.nodes)

def get_actual_version(node_group: ShaderNodeGroup) -> int:
    if not node_group:
        return 0
    version_socket: NodeSocket = node_group.inputs.get('Version')
    if not version_socket:
        return 0
    
    return version_socket.default_value

def get_mat_version(node_group_name: NodeGroupTypeEnum) -> int:
    node_tree: NodeTree = bpy.data.node_groups.get(node_group_name)
    if node_tree:
        return get_version(node_tree)
    else:
        return 0

def update_tree(old_tree: NodeTree, material_desc: MatDesc, is_version_check: bool) -> NodeTree:
    if not old_tree and material_desc:
        #return material_desc.create()
        return material_desc.create_custom()
    version: int = get_version(old_tree)
    if is_version_check and version == material_desc.version:
        log.info("- Tree has same version: " + material_desc.name + " of " + str(version))
        return None

    old_tree.name = old_tree.name + str(uuid.uuid4())
    #new_group: NodeTree = material_desc.create()
    new_group: NodeTree = material_desc.create_custom()
    return new_group

def get_fc_list(action: Action, path: str) -> Sequence[FCurve]:
    result: Sequence[FCurve] = [fc for fc in action.fcurves if fc.data_path == path]
    return result

def replace_group(old_node_tree: NodeTree, new_node_tree: NodeTree, new_mat_desc: MatDesc, group_node_type_name: NodeGroupTypeEnum):
    if not new_node_tree:
        return
    node_tree_regex = re.compile(f'[A-Za-z0-9_-]*{str(group_node_type_name.value)[3:]}[A-Za-z0-9_.-]*')
    mats: List[Material] = filter_materials_re(node_tree_regex)

    log.info("+ Tree: " + str(group_node_type_name.value) + " has " + str(len(mats)) + " materials")

    mat_links_map: Dict[str, List[SLink]] = {}
    mat_input_map: Dict[str, List[SInput]] = {}
    for material in mats:
        links: List[SLink] = move_links(material)
        mat_links_map[material.name] = links
        old_node_group: ShaderNodeGroup = get_edm_node_group_re(material, node_tree_regex)
        input_list: List[SInput] = extract_group_inputs(old_node_group)
        mat_input_map[material.name] = input_list
    
    replace_materials_re(mats, node_tree_regex, new_node_tree, new_mat_desc)

    # restore connections
    for material in mats:
        log.info("+ Tree " + str(group_node_type_name.value) + " process " + material.name + " material")

        links: List[SLink] = mat_links_map[material.name]
        inputs: List[SInput] = mat_input_map[material.name]
        mat_fx: Materials = get_material(group_node_type_name)
        if mat_fx:
            links = mat_fx.process_links(links, get_version(old_node_tree), group_node_type_name)
            #old_node_group: ShaderNodeGroup = get_edm_node_group_re(material, node_tree_regex)
            new_node_group: ShaderNodeGroup = get_edm_node_group(material, group_node_type_name)
            mat_fx.restore_defaults(inputs, new_node_group, get_version(old_node_tree), group_node_type_name)
        try:
            restore_links(material, links)
        except:
            if old_node_tree:
                log.info(f'=== Old: {old_node_tree.name} ===\n')
            print_node(old_node_tree)
            log.info(f'\n=== New: {new_node_tree.name} ===\n')
            print_node(new_node_tree)

def check_materials_validity() -> None: 
    broken_mat_regex_map = {}
    for node_tree_name in NodeGroupTypeEnum:
        #broken_mat_regex_map[node_tree_name] = re.compile(f'[A-Za-z0-9_-]*{str(node_tree_name.value)[3:]}[A-Za-z0-9_.-]+')
        broken_mat_regex_map[node_tree_name] = re.compile(f'[A-Za-z0-9_-]*{node_tree_name.value}[A-Za-z0-9_.-]+')

    for node_tree_name in NodeGroupTypeEnum:
        mat_regex = broken_mat_regex_map.get(node_tree_name)
        broken_mat_list: List[Material] = filter_materials_re(mat_regex)
        if broken_mat_list:
            for mat in broken_mat_list:
                node_group: ShaderNodeGroup = get_edm_node_group_re(mat, mat_regex)
                log.fatal(f"Material {mat.name} has broken custom group name. Expected name is {node_tree_name}, got {node_group.node_tree.name}. Please rename material!")

        mat_list: List[Material] = filter_materials(node_tree_name)

        if len(mat_list) > 0:
            pickle_file_name: str = os.path.join(EDMPath.full_plugin_path, get_material(node_tree_name).description_file_name)
            try:
                f = open(pickle_file_name, 'rb')
                ref_mat_desc = pickle.load(f)
            except:
                log.fatal(f'Could not open reference material to check md5: "{pickle_file_name}"')
            finally:
                f.close()

            for i in bpy.data.node_groups:
                if i.name == node_tree_name.value:
                    check_md5(node_tree_name, ref_mat_desc)

        for material in mat_list:

            edm_shader_node_group: ShaderNodeGroup = get_edm_node_group(material, node_tree_name)
            current_mat_ver = get_version(edm_shader_node_group.node_tree)
            if edm_shader_node_group.bl_idname == BpyShaderNode.NODE_GROUP:
                log.fatal(f"Material {material.name} has old shader group node (Green RW). Expected shader group node in {BpyShaderNode.NODE_GROUP_DECK.value}, {BpyShaderNode.NODE_GROUP_DEFAULT.value}, {BpyShaderNode.NODE_GROUP_EDM.value}, {BpyShaderNode.NODE_GROUP_FAKE_OMNI.value}, {BpyShaderNode.NODE_GROUP_FAKE_SPOT}. Please update materials!")
            if current_mat_ver < ref_mat_desc.version:
                log.fatal(f"Material {material.name} has old version. Expected version is {ref_mat_desc.version}, got {current_mat_ver}. Please update materials!")
            if current_mat_ver > ref_mat_desc.version:
                log.fatal(f"Material {material.name} has newer version. Expected version is {current_mat_ver}, got {ref_mat_desc.version}. Please update edm plugin!")

def check_plugin_version(ref_mat_desc_map: Dict[str, MatDesc]) -> None:
    mat_regex_map = {}
    for node_tree_name in NodeGroupTypeEnum:
        mat_regex_map[node_tree_name] = re.compile(f'[A-Za-z0-9_-]*{str(node_tree_name.value)[3:]}[A-Za-z0-9_.-]*')

    for node_tree_name in NodeGroupTypeEnum:
        ref_mat_desc: MatDesc = ref_mat_desc_map.get(node_tree_name)
        if not ref_mat_desc:
            continue
        mat_regex = mat_regex_map.get(node_tree_name)
        mat_list: List[Material] = filter_materials_re(mat_regex)
        for material in mat_list:
            edm_shader_node_group: ShaderNodeGroup = get_edm_node_group_re(material, mat_regex)
            current_mat_ver = get_version(edm_shader_node_group.node_tree)
            if current_mat_ver > ref_mat_desc.version:
                log.fatal(f"Material {material.name} has newer version. Expected version is {current_mat_ver}, got {ref_mat_desc.version}. Please update edm plugin!")

def count_materials_to_update(ref_mat_desc_map: Dict[str, MatDesc]) -> None:
    tree_ct: int = 0
    mat_ct: int = 0
    tree_list: List[str] = []
    mat_map: Dict[str, int] = {}

    node_group_types = get_node_group_types()
    for k in node_group_types:
        material = get_material(k)
        material_desc: MatDesc = ref_mat_desc_map.get(material.name)
        if not material_desc:
            continue
        old_node_tree: NodeTree = bpy.data.node_groups.get(material.name)
        if not old_node_tree:
            continue
        version: int = get_version(old_node_tree)
        if version == material_desc.version:
            continue
        tree_ct = tree_ct + 1
        tree_list.append(material.name.value)
        node_tree_regex = re.compile(f'[A-Za-z0-9_-]*{str(material.name.value)[3:]}[A-Za-z0-9_.-]*')
        mats: List[Material] = filter_materials_re(node_tree_regex)
        current_mat_count: int = len(mats)
        mat_ct = mat_ct + current_mat_count
        mat_map.update({material.name.value : current_mat_count})
    log.info("Blend file has " + str(tree_ct) + " old NodeTrees and " + str(mat_ct) + " materials to update.")
    for tree_name in tree_list:
        kv_mat_ct: int = mat_map.get(tree_name)
        if kv_mat_ct:
            log.info("Blend file has " + tree_name + " tree and " + str(kv_mat_ct) + " materials with it to update.")
        else:
            log.info("Blend file has " + tree_name + " tree and zero materials with it ti update.")

def has_old_rw_group(material_name: str) -> bool:
    node_tree_regex = re.compile(f'[A-Za-z0-9_-]*{material_name[3:]}[A-Za-z0-9_.-]*')
    mat_list: List[Material] = filter_materials_re(node_tree_regex)
    for material in mat_list:
        edm_shader_node_group: ShaderNodeGroup = get_edm_node_group_re(material, node_tree_regex)
        if not edm_shader_node_group.bl_idname in (BpyShaderNode.NODE_GROUP_EDM,  BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT):
            return True
    return False

class EDM_PT_import_materials(Operator):
    bl_idname = "edm.import_matrials"
    bl_label = "Update EDM materials"
    bl_description = "Update EDM materials to the latest version"

    def __init__(self) -> None:
        super().__init__()
        self.material_descs: Dict[str, MatDesc] = build_material_descriptions()

    def execute(self, context):
        check_plugin_version(self.material_descs)
        count_materials_to_update(self.material_descs)

        node_group_types = get_node_group_types()
        for k in node_group_types:
            material = get_material(k)
            log.info("Processing tree: " + material.name)

            material_desc: MatDesc = self.material_descs.get(material.name)
            if not material_desc:
                log.info("- Tree: " + material.name + " has no material description.")
                continue
            
            # здесь вроде есть проблема - если используются старые материалы(Олины) типа ED_Default_Material8 то материал не обновиться
            old_node_tree: NodeTree = bpy.data.node_groups.get(material.name)
            if not old_node_tree:
                log.info("- Blend file has no tree for " + material.name)

            is_version_check: bool = not has_old_rw_group(material.name)
            new_node_tree: NodeTree = update_tree(old_node_tree, material_desc, is_version_check)
            if not new_node_tree:
                log.info("- Tree update break: " + material.name)
                continue
            else:
                log.info("+ Tree update succeeded: " + material.name)

            replace_group(old_node_tree, new_node_tree, material_desc, material.name)

            if old_node_tree:
                bpy.data.node_groups.remove(old_node_tree)
            new_node_tree.name = material.name

        return {'FINISHED'}
    
class EDM_PT_export_materials(Operator):
    bl_idname = "edm.export_matrials" 
    bl_label = "Export EDM materials"
    bl_description = "Export reference materials to pickle file"

    def execute(self, context):
        for bpy_material in (m for m in bpy.data.materials if m.use_nodes and m.node_tree.nodes['Group']):
            file_name = bpy_material.name + '.pickle'
            blend_file_name = bpy_material.name + '.blend'
            full_file_path = os.path.join(EDMPath.full_plugin_path, 'data', file_name)
            full_blend_file_path = os.path.join(EDMPath.full_plugin_path, 'data', blend_file_name)
            with open(full_file_path, 'wb') as f:
                buf: bytes = serialize_group(bpy_material.node_tree.nodes['Group'], full_blend_file_path)
                f.write(buf)    

        return {'FINISHED'}

tool_classes = (
    EDM_PT_import_materials,
    EDM_PT_export_materials,
)

def get_material_tool_classes():
    return tool_classes
