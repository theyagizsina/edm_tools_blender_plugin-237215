import bpy
from pathlib import Path
from typing import Union, List, Dict
import re
import serializer

from bpy.types import (
    Material,
    Node,
    NodeSocket,
    ShaderNode,
    ShaderNodeGroup,
    ShaderNodeTexImage,
    ShaderNodeUVMap,
    ShaderNodeTexCoord,
    ShaderNodeMapping,
    ShaderNodeOutputMaterial,
    NodeTree
)

from enums import (
    BpyNodeSocketType,
    BpyShaderNode,
    NodeGroupTypeEnum,
    NodeSocketCommonEnum,
    NodeSocketInDeckEnum,
    NodeSocketInDefaultEnum,
    NodeSocketInEmissiveEnum,
    NodeSocketInFakeOmniEnum,
    NodeSocketInFakeSpotEnum,
    NodeSocketInGlassEnum,
    NodeSocketInMirrorEnum,
    ShaderNodeTexImageOutParams,
    ShaderNodeMappingInParams
)

from logger import log
from utils import make_socket_map, make_acro_map, check_ex

def socket_have_in_links(socket: NodeSocket) -> bool:
    return socket and socket.links is not None and not len(socket.links) == 0

def get_node_from_socket(socket: NodeSocket, tt: type) -> Union[Node, None]:
    return socket.links[0].from_node if socket_have_in_links(socket) and type(socket.links[0].from_node) is tt else None

def node_have_in_links(node: ShaderNode) -> bool:
    return node and node.inputs is not None and socket_have_in_links(node.inputs[0])

def get_connected_node(node: ShaderNode, tt: type) -> Union[ShaderNode, None]:
    return get_node_from_socket(node.inputs[0], tt) if node_have_in_links(node) else None

def get_material_output_nodes(material: Material) -> List[ShaderNodeOutputMaterial]:
    use_nodes: bool = material.use_nodes and bool(material.node_tree)
    if not use_nodes:
        return []
    out_nodes_list: List[ShaderNodeOutputMaterial] = []
    for bpy_node in material.node_tree.nodes:
        if bpy_node.bl_idname == BpyShaderNode.OUTPUT_MATERIAL:
            out_nodes_list.append(bpy_node)
    return out_nodes_list

def get_material_output(material: Material) -> Union[ShaderNodeOutputMaterial, None]:
    if not material:
        return None
    out_nodes_list: List[ShaderNodeOutputMaterial] = get_material_output_nodes(material)
    if len(out_nodes_list) == 0:
        return None
    for bpy_node in out_nodes_list:
        if bpy_node.is_active_output:
            return bpy_node
    return None

def get_edm_node_group_from_node(bpy_node: Node, custom_group_name: str) -> Union[ShaderNodeGroup, None]:
    if not bpy_node:
        return None
    for socket in bpy_node.inputs:
        for link in socket.links:
            linked_node: Node = link.from_node
            if linked_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and linked_node.node_tree and linked_node.node_tree.name == custom_group_name:
                return linked_node
            for linked_node_socket in linked_node.inputs:
                for linked_node_link in linked_node_socket.links:
                    return get_edm_node_group_from_node(linked_node_link.from_node, custom_group_name)
    
    return None

def get_edm_node_group(material: Material, custom_group_name: str) -> Union[ShaderNodeGroup, None]:
    if not custom_group_name or not material:
        return None

    use_nodes: bool = material.use_nodes and bool(material.node_tree)
    if not use_nodes:
        return None
    
    material_output_node: ShaderNodeOutputMaterial = get_material_output(material)
    group_node_by_link: Union[ShaderNodeGroup, None] = get_edm_node_group_from_node(material_output_node, custom_group_name)
    if group_node_by_link:
        return group_node_by_link

    for bpy_node in material.node_tree.nodes:
        if bpy_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and bpy_node.node_tree and bpy_node.node_tree.name == custom_group_name:
            return bpy_node

    return None

def get_edm_node_group_from_node_re(bpy_node: Node, custom_group_regex) -> Union[ShaderNodeGroup, None]:
    if not bpy_node or not custom_group_regex:
        return None
    for socket in bpy_node.inputs:
        for link in socket.links:
            linked_node: Node = link.from_node
            if linked_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and linked_node.node_tree and re.match(custom_group_regex, linked_node.node_tree.name):
                return linked_node
            for linked_node_socket in linked_node.inputs:
                for linked_node_link in linked_node_socket.links:
                    return get_edm_node_group_from_node_re(linked_node_link.from_node, custom_group_regex)
    
    return None

def get_node_re(material: Material, node_name_regex) -> Union[ShaderNode, None]:
    if not node_name_regex or not material:
        return None

    use_nodes: bool = material.use_nodes and bool(material.node_tree)
    if not use_nodes:
        return None
    
    for bpy_node in material.node_tree.nodes:
        if re.match(node_name_regex, bpy_node.name):
            return bpy_node

    return None

def get_edm_node_group_re(material: Material, custom_group_regex) -> Union[ShaderNodeGroup, None]:
    if not custom_group_regex or not material:
        return None

    use_nodes: bool = material.use_nodes and bool(material.node_tree)
    if not use_nodes:
        return None
    
    material_output_node: ShaderNodeOutputMaterial = get_material_output(material)
    group_node_by_link: Union[ShaderNodeGroup, None] = get_edm_node_group_from_node_re(material_output_node, custom_group_regex)
    if group_node_by_link:
        return group_node_by_link

    for bpy_node in material.node_tree.nodes:
        if bpy_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and bpy_node.node_tree and re.match(custom_group_regex, bpy_node.node_tree.name):
            return bpy_node

    return None

def get_list_edm_node_group_re(custom_group_regex) -> List[NodeTree]:
    node_group_list: List[NodeTree] = []
    for node_tree in bpy.data.node_groups:
        if re.match(custom_group_regex, node_tree.name):
            node_group_list.append(node_tree)

    return node_group_list

def get_list_free_edm_node_group_re(custom_group_regex) -> List[NodeTree]:
    if not custom_group_regex:
        return []
    
    node_group_list: Dict[str, Material] = {}
    for mat in bpy.data.materials:
        use_nodes = mat.use_nodes and mat.node_tree
        if not use_nodes:
            continue
        for bpy_node in mat.node_tree.nodes:
            if bpy_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) and bpy_node.node_tree and re.match(custom_group_regex, bpy_node.node_tree.name):
                node_group_list[bpy_node.node_tree.name].append(mat)

    node_group_list: List[NodeTree] = []
    for node_tree in bpy.data.node_groups:
        if re.match(custom_group_regex, node_tree.name) and not node_tree.name in node_group_list:
            node_group_list[node_tree.name] = node_tree

    return node_group_list

g_missing_texture_name: str = '__EMPTY__'

class AttachedTextureStruct:
    @staticmethod
    def build_from_socket(node_socket: NodeSocket):
        node: ShaderNodeTexImage = get_node_from_socket(node_socket, ShaderNodeTexImage)
        if not node:
            return None
        return AttachedTextureStruct(node)
    
    def __init__(self, node: ShaderNodeTexImage) -> None:
        self.texture_node: ShaderNodeTexImage = node
        self.texture_socket: NodeSocket = self.texture_node.outputs[ShaderNodeTexImageOutParams.COLOR]
        self.attached: bool = False
        if node.image:
            self.attached = True
            self.texture_name: str = Path(Path(node.image.name).stem).stem
        else:
            self.texture_name: str = g_missing_texture_name
        self.uv_move_node: ShaderNodeMapping = get_connected_node(node, ShaderNodeMapping)
        self.uv_move_loc_anim_path: str = self.uv_move_node.inputs[ShaderNodeMappingInParams.LOCATION].path_from_id('default_value') if self.uv_move_node else None
        self.uv_move_rot_anim_path: str = self.uv_move_node.inputs[ShaderNodeMappingInParams.ROTATION].path_from_id('default_value') if self.uv_move_node else None
        self.uv_move_sc_anim_path: str = self.uv_move_node.inputs[ShaderNodeMappingInParams.SCALE].path_from_id('default_value') if self.uv_move_node else None
        self.uv_node: ShaderNodeUVMap = get_connected_node(node, ShaderNodeUVMap)
        if not self.uv_node:
            self.uv_node = get_connected_node(self.uv_move_node, ShaderNodeUVMap)
        self.uv_name: str = self.uv_node.uv_map if self.uv_node else None

    def get_uv_map(self, default_uv_map) -> str:
        return self.uv_node.uv_map if self.uv_node and self.uv_node.uv_map else default_uv_map
    
def remove_item(collection, item):
     item_in = collection[item.name]
     collection.remove(item_in)

def remove_item_by_name(collection, name: str):
     item_in = collection.get(name)
     if item_in:
        collection.remove(item_in)

def search_out_socket(node_group: ShaderNodeGroup, name: str, type: str) -> Union[NodeSocket, None]:
    for out_socket in node_group.outputs:
        if out_socket.name == name and out_socket.bl_idname == type:
            return out_socket
    return None

def search_in_socket(node_group: ShaderNodeGroup, name: str, type: str) -> Union[NodeSocket, None]:
    for in_socket in node_group.inputs:
        if in_socket.name == name and in_socket.bl_idname == type:
            return in_socket
    return None

class TextureDesk:
    def __init__(self, node_group: ShaderNodeGroup, socket_name: str, socket_type: str) -> None:
        self.socket_name: str = socket_name
        self.socket_type: str = socket_type
        self.apply(node_group)
        self.update()

    def apply(self, node_group: ShaderNodeGroup):
        self.socket: NodeSocket = search_in_socket(node_group, self.socket_name, self.socket_type)

    def update(self):
        self.texture = AttachedTextureStruct.build_from_socket(self.socket)
        if self.socket_type == BpyNodeSocketType.COLOR:
            self.default_color = serializer.type_helper(self.socket.default_value) if self.socket else (0.0, 0.0, 0.0, 1.0)
        elif self.socket_type == BpyNodeSocketType.FLOAT:
            self.default_color = (0.0, 0.0, 0.0, serializer.type_helper(self.socket.default_value)) if self.socket else (0.0, 0.0, 0.0, 1.0)
        else:
            self.default_color = serializer.type_helper(self.socket.default_value) if self.socket else (0.0, 0.0, 0.0, 1.0)
        self.color_anim_path: str = self.socket.path_from_id('default_value') if self.socket else None

class ValueDesk:
    def __init__(self, node_group: ShaderNodeGroup, socket_name: NodeSocketInDefaultEnum, socket_type: BpyNodeSocketType, def_value) -> None:
        self.node_group: ShaderNodeGroup = node_group
        self.socket_map: Dict[str, Dict[str, str]] = make_socket_map(node_group)
        self.socket_acro_map: Dict[str, str] = make_acro_map(node_group)
        self.tree_name: str = node_group.node_tree.name
        self.socket_name: str = socket_name.value
        self.socket_type: str = socket_type.value
        if check_ex(self.socket_map, self.tree_name, self.socket_name):
            if node_group.bl_idname in (BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT):
                # enum_name: str = self.socket_map[self.tree_name][socket_name]
                prop_name: str = self.socket_acro_map.get(socket_name.value)
                #prop_name: str = socket_name.value
                self.def_value = getattr(node_group, prop_name)
                self.anim_path: str = ''
                # if node_group.bl_idname == BpyShaderNode.NODE_GROUP_DEFAULT:
                #     self.def_value = getattr(node_group, prop_name)
                #     self.anim_path: str = ''
                # elif node_group.bl_idname == BpyShaderNode.NODE_GROUP_DECK:
                #     pass
                # elif node_group.bl_idname == BpyShaderNode.NODE_GROUP_FAKE_OMNI:
                #     pass
                # elif node_group.bl_idname == BpyShaderNode.NODE_GROUP_FAKE_SPOT:
                #     pass
            else:
                enum_name: str = self.socket_map[self.tree_name][socket_name]
                self.def_value = getattr(node_group, enum_name)
                self.anim_path: str = ''
        else:
            self.apply(node_group)
            self.def_value = serializer.type_helper(self.socket.default_value) if self.socket and self.socket.default_value else def_value
            self.anim_path: str = self.socket.path_from_id('default_value') if self.socket else None
        self.update()

    def apply(self, node_group: ShaderNodeGroup):
        self.socket: NodeSocket = search_in_socket(node_group, self.socket_name, self.socket_type)

    def update(self):
        if hasattr(self.node_group, self.socket_type):
            if self.node_group.bl_idname in (BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT):
                prop_name: str = self.socket_acro_map.get(self.socket_name)
                self.value = getattr(self.node_group, prop_name)
            else:
                self.value = getattr(self.node_group, self.socket_type)
        else:
            self.value = self.socket.default_value if self.socket and self.socket.default_value else self.def_value

class MaterialWrap:
    def __init__(self, material: Material, node_group_type: NodeGroupTypeEnum, node_group_output: str) -> None:
        self.node_group_output: str = node_group_output
        self.material: Material = material
        self.name: Material = material.name
        self.node_group_type = node_group_type
        self.node_group = get_edm_node_group(material, node_group_type)
        self.valid = not self.node_group == None

    def is_valid(self):
        return self.valid
    
    def apply_group(self, node_group: ShaderNodeGroup, texture_type: type, value_type: type):
        self.node_group = node_group
        self.valid = not self.node_group == None
        if not self.valid:
            return
        
        if not 'textures' in self.__dict__ or self.textures == None:
            if not texture_type == None:
                self.textures = texture_type(self.node_group)
        else:
            for attr in self.textures.__dict__.keys():
                getattr(self.textures, attr).apply(node_group)

        if not 'values' in self.__dict__ or self.values == None:
            if not value_type == None:
                self.values = value_type(self.node_group)
        else:
            for attr in self.values.__dict__.keys():
                getattr(self.values, attr).apply(node_group)
        
    def update_linked_resources(self):
        for i in self.textures.__dict__.keys():
            getattr(self.textures, i).update()

        for i in self.values.__dict__.keys():
            getattr(self.values, i).update()
    
class DefMaterialWrap(MaterialWrap):
    class Textures:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.albedo         = TextureDesk(node_group, NodeSocketInDefaultEnum.BASE_COLOR, BpyNodeSocketType.COLOR)
            self.decal          = TextureDesk(node_group, NodeSocketInDefaultEnum.DECAL_COLOR, BpyNodeSocketType.COLOR)
            self.rmo            = TextureDesk(node_group, NodeSocketInDefaultEnum.ROUGH_METAL, BpyNodeSocketType.COLOR)
            self.light_map      = TextureDesk(node_group, NodeSocketInDefaultEnum.LIGHTMAP, BpyNodeSocketType.COLOR)
            self.normal         = TextureDesk(node_group, NodeSocketInDefaultEnum.NORMAL, BpyNodeSocketType.COLOR)
            self.emissive       = TextureDesk(node_group, NodeSocketInDefaultEnum.EMISSIVE, BpyNodeSocketType.COLOR)
            self.emissive_mask  = TextureDesk(node_group, NodeSocketInDefaultEnum.EMISSIVE_MASK, BpyNodeSocketType.FLOAT)
            self.flir           = TextureDesk(node_group, NodeSocketInDefaultEnum.FLIR, BpyNodeSocketType.COLOR)
            self.damage_color   = TextureDesk(node_group, NodeSocketInDefaultEnum.DAMAGE_COLOR, BpyNodeSocketType.COLOR)
            self.damage_normal  = TextureDesk(node_group, NodeSocketInDefaultEnum.DAMAGE_NORMAL, BpyNodeSocketType.COLOR)
            self.damage_mask    = TextureDesk(node_group, NodeSocketInDefaultEnum.DAMAGE_MASK, BpyNodeSocketType.COLOR)
            self.damage_alpha   = TextureDesk(node_group, NodeSocketInDefaultEnum.DAMAGE_ALPHA, BpyNodeSocketType.COLOR)

    class Values:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.alpha              = ValueDesk(node_group, NodeSocketInDefaultEnum.BASE_ALPHA, BpyNodeSocketType.FLOAT, 1.0)
            self.decal_alpha        = ValueDesk(node_group, NodeSocketInDefaultEnum.DECAL_ALPHA, BpyNodeSocketType.FLOAT, 1.0)
            self.ao                 = ValueDesk(node_group, NodeSocketInDefaultEnum.AO_VALUE, BpyNodeSocketType.FLOAT, 1.0)
            self.light_map_value    = ValueDesk(node_group, NodeSocketInDefaultEnum.LIGHTMAP_VALUE, BpyNodeSocketType.FLOAT, 1.0)
            self.emissive_value     = ValueDesk(node_group, NodeSocketInDefaultEnum.EMISSIVE_VALUE, BpyNodeSocketType.FLOAT, 0.0)
            self.decal_id           = ValueDesk(node_group, NodeSocketInDefaultEnum.DECALID, BpyNodeSocketType.INTEGER, 0)
            self.blend_mode         = ValueDesk(node_group, NodeSocketInDefaultEnum.TRANSPARENCY, BpyNodeSocketType.TRANSPARENCY, 'OPAQUE')
            self.shadow_caster      = ValueDesk(node_group, NodeSocketInDefaultEnum.SHADOW_CASTER, BpyNodeSocketType.SHADOWCASTER, 'SHADOW_CASTER_YES')
            self.version            = ValueDesk(node_group, NodeSocketCommonEnum.VERSION, BpyNodeSocketType.INTEGER, -1)
            self.opacity_value      = ValueDesk(node_group, NodeSocketInDefaultEnum.OPACITY_VALUE, BpyNodeSocketType.FLOAT, 1.0)

    def __init__(self, material: Material) -> None:
        super().__init__(material, NodeGroupTypeEnum.DEFAULT, 'BSDF')
        self.textures: DefMaterialWrap.Textures = None
        self.values: DefMaterialWrap.Values = None
        self.apply_group(self.node_group, DefMaterialWrap.Textures, DefMaterialWrap.Values)
        
        if not self.valid:
            return
        self.update_linked_resources()

class DeckMaterialWrap(MaterialWrap):
    class Textures:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.base_tile_map      = TextureDesk(node_group, NodeSocketInDeckEnum.BASE_TILE_MAP, BpyNodeSocketType.COLOR)
            self.base_alpha         = TextureDesk(node_group, NodeSocketInDeckEnum.BASE_ALPHA, BpyNodeSocketType.COLOR)
            self.rmo_tile_map       = TextureDesk(node_group, NodeSocketInDeckEnum.RMO_TILE_MAP, BpyNodeSocketType.COLOR)
            self.normal_tile_map    = TextureDesk(node_group, NodeSocketInDeckEnum.NORMAL_TILE_MAP, BpyNodeSocketType.COLOR)
            self.decal_map          = TextureDesk(node_group, NodeSocketInDeckEnum.DECAL_BASE_COLOR, BpyNodeSocketType.COLOR)
            self.decal_alpha        = TextureDesk(node_group, NodeSocketInDeckEnum.DECAL_ALPHA, BpyNodeSocketType.COLOR)
            self.decal_rmo          = TextureDesk(node_group, NodeSocketInDeckEnum.DECAL_RMO, BpyNodeSocketType.COLOR)
            self.damage_color       = TextureDesk(node_group, NodeSocketInDeckEnum.DAMAGE_COLOR, BpyNodeSocketType.COLOR)
            self.damage_mask        = TextureDesk(node_group, NodeSocketInDeckEnum.DAMAGE_MASK, BpyNodeSocketType.COLOR)
            self.damage_normal      = TextureDesk(node_group, NodeSocketInDeckEnum.DAMAGE_NORMAL, BpyNodeSocketType.COLOR)
            self.damage_alpha       = TextureDesk(node_group, NodeSocketInDeckEnum.DAMAGE_ALPHA, BpyNodeSocketType.COLOR)
            self.rain_mask          = TextureDesk(node_group, NodeSocketInDeckEnum.RAIN_MASK, BpyNodeSocketType.COLOR)

    class Values:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.ao                 = ValueDesk(node_group, NodeSocketInDeckEnum.AO_VALUE, BpyNodeSocketType.FLOAT, 1.0)
            self.wetness            = ValueDesk(node_group, NodeSocketInDeckEnum.WETNESS, BpyNodeSocketType.FLOAT, 1.0)
            self.decal_id           = ValueDesk(node_group, NodeSocketInDeckEnum.DECALID, BpyNodeSocketType.INTEGER, 0)
            self.blend_mode         = ValueDesk(node_group, NodeSocketInDeckEnum.TRANSPARENCY, BpyNodeSocketType.TRANSPARENCY, 'OPAQUE')
            self.version            = ValueDesk(node_group, NodeSocketCommonEnum.VERSION, BpyNodeSocketType.INTEGER, -1)

    def __init__(self, material: Material) -> None:
        super().__init__(material, NodeGroupTypeEnum.DECK, 'Surface')
        self.textures: DeckMaterialWrap.Textures = None
        self.values: DeckMaterialWrap.Values = None
        self.apply_group(self.node_group, DeckMaterialWrap.Textures, DeckMaterialWrap.Values)
        if not self.valid:
            return
        self.update_linked_resources()

class FakeOmniLightMaterialWrap(MaterialWrap):
    class Textures:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.emissive_map       = TextureDesk(node_group, NodeSocketInFakeOmniEnum.EMISSIVE, BpyNodeSocketType.COLOR)

    class Values:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.luminance          = ValueDesk(node_group, NodeSocketInFakeOmniEnum.LUMINANCE, BpyNodeSocketType.FLOAT, 1.0)
            self.min_size_pixels    = ValueDesk(node_group, NodeSocketInFakeOmniEnum.MIN_SIZE_PIXELS, BpyNodeSocketType.FLOAT, 4.0)
            self.max_distance       = ValueDesk(node_group, NodeSocketInFakeOmniEnum.MAX_DISTANCE, BpyNodeSocketType.FLOAT, 1000.0)
            self.shift_to_camera    = ValueDesk(node_group, NodeSocketInFakeOmniEnum.SHIFT_TO_CAMERA, BpyNodeSocketType.FLOAT, 0.0)
            self.version            = ValueDesk(node_group, NodeSocketCommonEnum.VERSION, BpyNodeSocketType.INTEGER, -1)

    def __init__(self, material: Material) -> None:
        super().__init__(material, NodeGroupTypeEnum.FAKE_OMNI, 'Surface')
        self.textures: FakeOmniLightMaterialWrap.Textures = None
        self.values: FakeOmniLightMaterialWrap.Values = None
        self.apply_group(self.node_group, FakeOmniLightMaterialWrap.Textures, FakeOmniLightMaterialWrap.Values)
        if not self.valid:
            return
        self.update_linked_resources()

class FakeSpotLightMaterialWrap(MaterialWrap):
    class Textures:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.emissive   = TextureDesk(node_group, NodeSocketInFakeSpotEnum.EMISSIVE, BpyNodeSocketType.COLOR)

    class Values:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.luminance          = ValueDesk(node_group, NodeSocketInFakeSpotEnum.LUMINANCE, BpyNodeSocketType.FLOAT, 1.0)
            self.min_size_pixels    = ValueDesk(node_group, NodeSocketInFakeSpotEnum.MIN_SIZE_PIXELS, BpyNodeSocketType.FLOAT, 4.0)
            self.max_distance       = ValueDesk(node_group, NodeSocketInFakeSpotEnum.MAX_DISTANCE, BpyNodeSocketType.FLOAT, 1000.0)
            self.shift_to_camera    = ValueDesk(node_group, NodeSocketInFakeSpotEnum.SHIFT_TO_CAMERA, BpyNodeSocketType.FLOAT, 0.0)
            self.phi                = ValueDesk(node_group, NodeSocketInFakeSpotEnum.PHI, BpyNodeSocketType.FLOAT, 45.0)
            self.theta              = ValueDesk(node_group, NodeSocketInFakeSpotEnum.THETA, BpyNodeSocketType.FLOAT, 25.0)
            self.version            = ValueDesk(node_group, NodeSocketCommonEnum.VERSION, BpyNodeSocketType.INTEGER, -1)

    def __init__(self, material: Material) -> None:
        super().__init__(material, NodeGroupTypeEnum.FAKE_SPOT, 'Surface')
        self.textures: FakeSpotLightMaterialWrap.Textures = None
        self.values: FakeSpotLightMaterialWrap.Values = None
        self.apply_group(self.node_group, FakeSpotLightMaterialWrap.Textures, FakeSpotLightMaterialWrap.Values)
        if not self.valid:
            return
        self.update_linked_resources()

class GlassMaterialWrap(MaterialWrap):
    class Textures:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.albedo         = TextureDesk(node_group, NodeSocketInGlassEnum.BASE_COLOR, BpyNodeSocketType.COLOR)
            self.decal          = TextureDesk(node_group, NodeSocketInGlassEnum.DECAL_COLOR, BpyNodeSocketType.COLOR)
            self.rmo            = TextureDesk(node_group, NodeSocketInGlassEnum.ROUGH_METAL, BpyNodeSocketType.COLOR)
            self.light_map      = TextureDesk(node_group, NodeSocketInGlassEnum.LIGHTMAP, BpyNodeSocketType.COLOR)
            self.normal         = TextureDesk(node_group, NodeSocketInGlassEnum.NORMAL, BpyNodeSocketType.COLOR)
            self.emissive       = TextureDesk(node_group, NodeSocketInGlassEnum.EMISSIVE, BpyNodeSocketType.COLOR)
            self.filter         = TextureDesk(node_group, NodeSocketInGlassEnum.FILTER_COLOR, BpyNodeSocketType.COLOR)
            self.flir           = TextureDesk(node_group, NodeSocketInGlassEnum.FLIR, BpyNodeSocketType.COLOR)
            self.damage_color   = TextureDesk(node_group, NodeSocketInGlassEnum.DAMAGE_COLOR, BpyNodeSocketType.COLOR)
            self.damage_normal  = TextureDesk(node_group, NodeSocketInGlassEnum.DAMAGE_NORMAL, BpyNodeSocketType.COLOR)
            self.damage_mask    = TextureDesk(node_group, NodeSocketInGlassEnum.DAMAGE_MASK, BpyNodeSocketType.COLOR)

    class Values:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.alpha              = ValueDesk(node_group, NodeSocketInDefaultEnum.BASE_ALPHA, BpyNodeSocketType.FLOAT, 1.0) 
            self.decal_alpha        = ValueDesk(node_group, NodeSocketInDefaultEnum.DECAL_ALPHA, BpyNodeSocketType.FLOAT, 1.0)
            self.ao                 = ValueDesk(node_group, NodeSocketInDefaultEnum.AO_VALUE, BpyNodeSocketType.FLOAT, 1.0)
            self.light_map_value    = ValueDesk(node_group, NodeSocketInDefaultEnum.LIGHTMAP_VALUE, BpyNodeSocketType.FLOAT, 1.0)
            self.emissive_value     = ValueDesk(node_group, NodeSocketInDefaultEnum.EMISSIVE_VALUE, BpyNodeSocketType.FLOAT, 1.0)
            self.decal_id           = ValueDesk(node_group, NodeSocketInDefaultEnum.DECALID, BpyNodeSocketType.INTEGER, 0)
            self.blend_mode         = ValueDesk(node_group, NodeSocketInDefaultEnum.TRANSPARENCY, BpyNodeSocketType.INTEGER, 0)
            self.shadow_caster      = ValueDesk(node_group, NodeSocketInDefaultEnum.SHADOW_CASTER, BpyNodeSocketType.INTEGER, 0)
            self.version            = ValueDesk(node_group, NodeSocketCommonEnum.VERSION, BpyNodeSocketType.INTEGER, -1)

    def __init__(self, material: Material) -> None:
        super().__init__(material, NodeGroupTypeEnum.DEFAULT, 'BSDF')
        self.textures: GlassMaterialWrap.Textures = None
        self.values: GlassMaterialWrap.Values = None
        self.apply_group(self.node_group, GlassMaterialWrap.Textures, GlassMaterialWrap.Values)
        
        if not self.valid:
            return
        self.update_linked_resources()

class MirrorMaterialWrap(MaterialWrap):
    class Textures:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.base_color     = TextureDesk(node_group, NodeSocketInMirrorEnum.BASE_COLOR, BpyNodeSocketType.COLOR)

    class Values:
        def __init__(self, node_group: ShaderNodeGroup) -> None:
            self.version            = ValueDesk(node_group, NodeSocketCommonEnum.VERSION, BpyNodeSocketType.INTEGER, -1)

    def __init__(self, material: Material) -> None:
        super().__init__(material, NodeGroupTypeEnum.MIRROR, 'Surface')
        self.textures: MirrorMaterialWrap.Textures = None
        self.values: MirrorMaterialWrap.Values = None
        self.apply_group(self.node_group, MirrorMaterialWrap.Textures, MirrorMaterialWrap.Values)
        if not self.valid:
            return
        self.update_linked_resources()
        
MaterialWrapCustomType = Union[DefMaterialWrap, DeckMaterialWrap, FakeOmniLightMaterialWrap, FakeSpotLightMaterialWrap, GlassMaterialWrap, MirrorMaterialWrap, None]