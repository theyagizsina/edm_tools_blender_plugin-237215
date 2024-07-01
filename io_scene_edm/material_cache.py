from typing import Dict

from bpy.types import Material

from enums import BpyShaderNode
from material_wrap import MaterialWrapCustomType
from materials import get_material, Materials


class MaterialCache:
    def __init__(self) -> None:
        self.materials: Dict[Material, MaterialWrapCustomType] = {}

    def get(self, material: Material) -> MaterialWrapCustomType:
        if material in self.materials.keys():
            return self.materials[material]
        
        material_warp: MaterialWrapCustomType = get_material_wrap(material)
        self.materials[material] = material_warp

        return material_warp
    
def get_material_wrap(material: Material) -> MaterialWrapCustomType:
    if not material:
        return None
    
    use_nodes: bool = material.use_nodes and bool(material.node_tree)
    if not use_nodes:
        return None
    
    for bpy_node in material.node_tree.nodes:
        if not bpy_node.bl_idname in (BpyShaderNode.NODE_GROUP, BpyShaderNode.NODE_GROUP_EDM, BpyShaderNode.NODE_GROUP_DEFAULT, BpyShaderNode.NODE_GROUP_DECK, BpyShaderNode.NODE_GROUP_FAKE_OMNI, BpyShaderNode.NODE_GROUP_FAKE_SPOT) or not bpy_node.node_tree:
            continue

        mat: Materials = get_material(bpy_node.node_tree.name)
        if mat:
            return mat.factory(material)