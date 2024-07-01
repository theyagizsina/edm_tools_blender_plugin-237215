import re
from pyedm_platform_selector import pyedm
import bpy
import os.path
import pickle
import copy
from collections import namedtuple
from typing import List, Union, Dict, NamedTuple, Callable, Type
from abc import ABC, abstractmethod

import block_builder
from utils import md5, EDMPath, make_acro_map, make_socket_map
from enums import NodeGroupTypeEnum, NodeSocketInDefaultEnum, NodeSocketInDeckEnum, BpyShaderNode, NodeSocketCommonEnum, get_node_group_types
from serializer import SLink, SInput
from logger import log
from material_wrap import MaterialWrap, DefMaterialWrap, DeckMaterialWrap, GlassMaterialWrap, MirrorMaterialWrap, MaterialWrapCustomType, FakeOmniLightMaterialWrap, FakeSpotLightMaterialWrap
from mesh_storage import MeshStorage
from serializer_tools import MatDesc
from version_specific import InterfaceNodeSocket, get_version, IS_BLENDER_4, IS_BLENDER_3
from bpy.types import Object, ShaderNodeGroup, Material
from custom_sockets import TransparencyEnumItems, ShadowCasterEnumItems
from export_fake_lights import make_fake_omni_edm_mat_blocks, make_fake_spot_edm_mat_blocks


def get_first_socket_by_name(sockest_list: List[SInput], name: str) -> Union[SInput, None]:
    for socket in sockest_list:
        if socket.name == name:
            return socket
    return None

## base material class 
class Materials(ABC):
    """
    Common abstract class for all types of materials.
    """

    ## Material name. Look at 'NodeGroupTypeEnum' to see all possible materials.
    name: str = NotImplemented
    ## Relative path to .pickle file of serialised material.
    description_file_name: str = NotImplemented
    ## material wrapper of current material
    factory = NotImplemented
 
    @classmethod
    @abstractmethod
    def build_blocks(cls, obj: Object, wrap: MaterialWrap, storage: MeshStorage) -> pyedm.IRenderNode:
        """
        Create render node that can be imported to edm. 
        Once 'pyedm.IRenderNode' was created, you need to set control node to it and add render node to model. 
        """
        pass

    @classmethod
    @abstractmethod
    def process_links(cls, links: List[SLink], version: int, group_node_type_name: str)-> List[SLink]:
        pass

    @classmethod
    @abstractmethod
    def restore_defaults(cls, old_sockest: List[SInput], 
                         new_node_group: ShaderNodeGroup, old_version: int, material_name: str) -> None:
        pass

# --- implementation of materials --- #
# --- Omni 
class OmniFakeLightsMaterial(Materials):
    name = NodeGroupTypeEnum.FAKE_OMNI    
    description_file_name = 'data/EDM_Fake_Omni_Material.pickle'
    factory = FakeOmniLightMaterialWrap
    
    @classmethod
    def build_blocks(cls, obj, wrap, storage):
        return make_fake_omni_edm_mat_blocks(obj, wrap, storage)
    
    @classmethod
    def process_links(cls, old_links, version, group_node_type_name):
        return old_links
    
    @classmethod
    def restore_defaults(cls, old_sockest, new_node_group, old_version, material_name):
        pass

# --- Spot
class SpotFakeLightsMaterial(Materials):
    name = NodeGroupTypeEnum.FAKE_SPOT
    description_file_name = 'data/EDM_Fake_Spot_Material.pickle'
    factory = FakeSpotLightMaterialWrap
    
    @classmethod
    def build_blocks(cls, obj, wrap, storage):
        return make_fake_spot_edm_mat_blocks(obj, wrap, storage)
    
    @classmethod
    def process_links(cls, old_links, version, group_node_type_name):
        return old_links
    
    @classmethod
    def restore_defaults(cls, old_sockest, new_node_group, old_version, material_name):
        pass

# --- Default
class DefaultMaterial(Materials):
    name = NodeGroupTypeEnum.DEFAULT    
    description_file_name = 'data/EDM_Default_Material.pickle'
    factory = DefMaterialWrap
    
    @classmethod    
    def build_blocks(cls, obj, wrap, storage):
        return block_builder.make_def_edm_mat_blocks(obj, wrap, storage)
    
    @classmethod
    def process_links(cls, old_links, old_version, group_node_type_name):
        new_links: List[SLink] = []
        
        if old_version == 0 or old_version == 1:
            for link in old_links:
                if link.to_type == 'ShaderNodeGroup':
                    # TODO: 'Normal  (Non-Color)' - looks strange, it has 2 spaces. is it ok?
                    if link.to_socket == 'Normal' or link.to_socket == 'Normal  (Non-Color)' or link.to_socket == 'Normal (Non color)':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDefaultEnum.NORMAL
                new_links.append(link)
        elif old_version <= 11:
            for link in old_links:
                if link.to_type == 'ShaderNodeGroup':
                    if link.to_socket == 'Damage Color':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDefaultEnum.DAMAGE_COLOR
                    elif link.to_socket == 'Damage Map':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDeckEnum.DAMAGE_MASK
                    elif link.to_socket == 'Damage Map (Non-Color)':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDeckEnum.DAMAGE_MASK
                    elif link.to_socket == 'Damage Normal':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDefaultEnum.DAMAGE_NORMAL
                new_links.append(link)
        else:
            for link in old_links:
                new_links.append(link)

        return new_links
    
    @classmethod 
    def restore_defaults(cls, old_sockest, new_node_group, old_version, material_name):
        version_new: int = get_version(new_node_group.node_tree)
        if old_version == 0:
            return
        if old_version < 8:
            for new_socket in new_node_group.inputs:
                old_socket_wrp: SInput = get_first_socket_by_name(old_sockest, new_socket.name)
                if not old_socket_wrp:
                    continue
                if new_socket.name == NodeSocketInDefaultEnum.SHADOW_CASTER and (old_socket_wrp.bl_socket_idname == 'NodeSocketUndefined' or not old_socket_wrp.instance_value):
                    new_socket.default_value = ShadowCasterEnumItems[0][0]
                    continue
                if new_socket.name == NodeSocketInDefaultEnum.SHADOW_CASTER:
                    new_socket.default_value = ShadowCasterEnumItems[old_socket_wrp.instance_value][0]
                    continue
                if new_socket.name == NodeSocketInDefaultEnum.TRANSPARENCY and (old_socket_wrp.bl_socket_idname == 'NodeSocketUndefined' or not old_socket_wrp.instance_value):
                    new_socket.default_value = TransparencyEnumItems[0][0]
                    continue
                if new_socket.name == NodeSocketInDefaultEnum.TRANSPARENCY:
                    new_socket.default_value = TransparencyEnumItems[old_socket_wrp.instance_value][0]
                    continue
                if new_socket.name == NodeSocketCommonEnum.VERSION:
                    new_socket.default_value = version_new
                    continue
                if hasattr(old_socket_wrp, 'instance_value'):
                    new_socket.default_value = old_socket_wrp.instance_value
        elif old_version >= 8:
            socket_map: Dict[str, Dict[str, str]] = make_socket_map(new_node_group)
            socket_acro_map: Dict[str, str] = make_acro_map(new_node_group)
            if socket_map.get(material_name):
                for socket_name in socket_map[material_name].keys():
                    if new_node_group.bl_idname in (BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT):
                        prop_name: str = socket_acro_map.get(socket_name)
                        old_socket_wrp: SInput = get_first_socket_by_name(old_sockest, socket_name)
                        if hasattr(old_socket_wrp, 'instance_value'):
                            setattr(new_node_group, prop_name, old_socket_wrp.instance_value)
                    else:
                        enum_name: str = socket_map[material_name][socket_name]
                        old_socket_wrp: SInput = get_first_socket_by_name(old_sockest, socket_name)
                        if old_socket_wrp and hasattr(old_socket_wrp, 'instance_value'):
                            setattr(new_node_group, enum_name, old_socket_wrp.instance_value)
            for new_socket in new_node_group.inputs:
                old_socket_wrp: SInput = get_first_socket_by_name(old_sockest, new_socket.name)
                if not old_socket_wrp:
                    continue
                if new_socket.name == NodeSocketCommonEnum.VERSION:
                    new_socket.default_value = version_new
                    continue
                if old_socket_wrp.instance_value:
                    if IS_BLENDER_3:
                        new_socket.default_value = old_socket_wrp.instance_value
                    elif IS_BLENDER_4:
                        if new_socket.name not in (NodeSocketInDefaultEnum.TRANSPARENCY, NodeSocketInDefaultEnum.SHADOW_CASTER):
                            new_socket.default_value = old_socket_wrp.instance_value

# --- Deck
class DeckMaterial(Materials):
    name = NodeGroupTypeEnum.DECK    
    description_file_name = 'data/EDM_Deck_Material.pickle'
    factory = DeckMaterialWrap

    @classmethod
    def build_blocks(cls, obj, wrap, storage):
        return block_builder.make_deck_edm_mat_blocks(obj, wrap, storage)

    @classmethod
    def process_links(cls, old_links, old_version, group_node_type_name):
        new_links: List[SLink] = []
        
        if old_version < 7:
            for link in old_links:
                if link.to_type == 'ShaderNodeGroup':
                    if link.to_socket == 'Damage Color':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDefaultEnum.DAMAGE_COLOR
                    elif link.to_socket == 'Damage Map':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDeckEnum.DAMAGE_MASK
                    elif link.to_socket == 'Damage Map (Non-Color)':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDeckEnum.DAMAGE_MASK
                    elif link.to_socket == 'Damage Normal':
                        link = copy.copy(link)
                        link.to_socket = NodeSocketInDeckEnum.DAMAGE_NORMAL
                new_links.append(link)
        else:
            for link in old_links:
                new_links.append(link)

        return new_links

    @classmethod    
    def restore_defaults(cls, old_sockest, new_node_group, old_version, material_name):
        version_new: int = get_version(new_node_group.node_tree)
        if old_version >= 1:
            for new_socket in new_node_group.inputs:
                old_socket_wrp: SInput = get_first_socket_by_name(old_sockest, new_socket.name)
                if not old_socket_wrp:
                    continue
                if new_socket.name == NodeSocketCommonEnum.VERSION:
                    new_socket.default_value = version_new
                    continue
                if old_socket_wrp.instance_value and new_socket.name not in (NodeSocketInDeckEnum.TRANSPARENCY): 
                    new_socket.default_value = old_socket_wrp.instance_value

## return material class corresponding to 'NodeGroupTypeEnum' enum.
def get_material(groupType: NodeGroupTypeEnum) -> Materials:    
    match groupType:
        case NodeGroupTypeEnum.DECK:
            return DeckMaterial
        case NodeGroupTypeEnum.DEFAULT:
            return DefaultMaterial
        case NodeGroupTypeEnum.FAKE_OMNI:
            return OmniFakeLightsMaterial
        case NodeGroupTypeEnum.FAKE_SPOT:
           return SpotFakeLightsMaterial
        case NodeGroupTypeEnum.GLASS:
           log.warning('GLASS material is not supported right now.')
           assert(False)
        case NodeGroupTypeEnum.MIRROR:
           log.warning('MIRROR material is not supported right now.')
           assert(False)
        case _:
            assert(False)


#-------------------------------------------------------------------------------------------------------------------
##  additional material methods 
def filter_materials(edm_group_name: str) -> List[Material]:
    out: List[Material] = []
    for mat in bpy.data.materials:
        use_nodes = mat.use_nodes and mat.node_tree
        if not use_nodes:
            continue

        for bpy_node in mat.node_tree.nodes:
            if bpy_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and bpy_node.node_tree and bpy_node.node_tree.name == edm_group_name:
                out.append(mat)
                
    return out

def filter_materials_re(edm_group_regex) -> List[Material]:
    out: List[Material] = []
    if not edm_group_regex:
        return out
    if not hasattr(bpy.data, "materials"):
        return out
    for mat in bpy.data.materials:
        use_nodes = mat.use_nodes and mat.node_tree
        if not use_nodes:
            continue

        for bpy_node in mat.node_tree.nodes:
            if bpy_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and bpy_node.node_tree and re.match(edm_group_regex, bpy_node.node_tree.name):
                out.append(mat)
                
    return out

def check_if_referenced_file(blend_file_name):
    bf = os.path.splitext(os.path.basename(blend_file_name))[0].lower()

    node_group_types = get_node_group_types()
    for m in node_group_types:
        if m.lower() == bf:
            return True
    return False

def check_md5(material_name: NodeGroupTypeEnum, material_desc: MatDesc):
    node_tree_name = re.compile(f'[A-Za-z0-9_.-]*{material_name.value}[A-Za-z0-9_.-]*')
    mat_list: List[Material] = filter_materials_re(node_tree_name)
    if mat_list:
        blend_file_name: str = 'data/' + str(material_name.value) + '.blend'
        blend_file_path: str = os.path.join(EDMPath.full_plugin_path, blend_file_name)
        blend_file_md5: str = md5(blend_file_path)
        if hasattr(material_desc, 'blend_file_md5') and material_desc.blend_file_md5 != blend_file_md5:
            log.fatal(f"Hash of material file {blend_file_path} is invalid.")
        
def build_material_descriptions() -> Dict[NodeGroupTypeEnum, MatDesc]:    
    material_descs: Dict[NodeGroupTypeEnum, MatDesc] = {}

    node_group_types = get_node_group_types()
    for name in node_group_types:
        mat = get_material(name)
        try:
            pickle_file_name: str = os.path.join(EDMPath.full_plugin_path, mat.description_file_name)
            with open(pickle_file_name, 'rb') as f:
                material_descs[name] = pickle.load(f)
            
        except OSError as e:
            log.error(f"Can't open material description file: {mat.description_file_name}. Reason: {e}.")
            continue
    return material_descs