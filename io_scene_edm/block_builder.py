from typing import List, Union, Tuple, Union
from enum import Enum
from enums import ShaderNodeMappingInParams, EDMCustomEmissiveTypeInt, EdmTransparencySocketItemsEnum

import animation as anim
from bpy.types import Object

from objects_custom_props import get_edm_props, EDMPropsGroup
from pyedm_platform_selector import pyedm
from logger import log
from material_wrap import (DeckMaterialWrap, DefMaterialWrap, MaterialWrap, MirrorMaterialWrap, AttachedTextureStruct)
from mesh_storage import MeshStorage
import utils
from custom_sockets import ShadowCasterEnumItems, TransparencyEnumItems, EmissionEnumItems

def make_base_texture(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, texture: AttachedTextureStruct) -> pyedm.BaseBlock:
    edm_base_bock = pyedm.BaseBlock()
    
    albedo_uv_map_name: str = texture.get_uv_map(mesh_storage.uv_active)
    albedo_map_name: str = texture.texture_name
    uv_shift_animation_path: str = texture.uv_move_node.inputs[ShaderNodeMappingInParams.LOCATION].path_from_id('default_value') if mat_wrap.valid and texture.uv_move_node else None
    arg_n: int = utils.extract_arg_number(texture.uv_move_node.label) if texture.uv_move_node else -1

    edm_base_bock.setAlbedoMapUV(mesh_storage.uv[albedo_uv_map_name])
    edm_base_bock.setAlbedoMap(albedo_map_name)

    is_uv_shift_animated: bool = uv_shift_animation_path and anim.has_path_anim(mat_wrap.material.node_tree.animation_data, uv_shift_animation_path)
    if is_uv_shift_animated and arg_n != -1:
        key_list: anim.KeyFramePoints = anim.extract_anim_vec3(mat_wrap.material.node_tree.animation_data.action, uv_shift_animation_path, (0.0, 0.0, 0.0), lambda v: [v[0], 1.0 - v[1]])
        uv_shift_prop = pyedm.PropertyFloat2(arg_n, key_list)
        edm_base_bock.setAlbedoMapUVShift(uv_shift_prop)

    return edm_base_bock

def make_def_base_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.BaseBlock:
    if not (mat_wrap.values.blend_mode.value == EdmTransparencySocketItemsEnum.SUM_BLENDING_SI and mat_wrap.textures.emissive.texture):
        if not mat_wrap.textures.albedo.texture:
            if utils.cmp_vec4(mat_wrap.textures.albedo.default_color, (0.0, 0.0, 0.0, 1.0)):
                return None
    
    if mat_wrap.values.blend_mode.value == EdmTransparencySocketItemsEnum.SUM_BLENDING_SI and mat_wrap.textures.emissive.texture:
        edm_base_bock = make_base_texture(mesh_storage, mat_wrap, mat_wrap.textures.emissive.texture)
    elif mat_wrap.textures.albedo.texture:
        edm_base_bock = make_base_texture(mesh_storage, mat_wrap, mat_wrap.textures.albedo.texture)
    else:
        edm_base_bock = pyedm.ColorBaseBlock()
        base_color_path: str = mat_wrap.textures.albedo.color_anim_path
        is_color_value_animated: bool = base_color_path and anim.has_path_anim(mat_wrap.material.node_tree.animation_data, base_color_path)
        if is_color_value_animated and edm_props.COLOR_ARG != -1:
            arg_color_n: int = edm_props.COLOR_ARG
            key_color_list: anim.KeyFramePoints = anim.extract_anim_vec4(mat_wrap.material.node_tree.animation_data.action, base_color_path, (0.0, 0.0, 0.0, 1.0), lambda v: [v[0], v[1], v[2]])
            base_color_prop = pyedm.PropertyFloat3(arg_color_n, key_color_list)
            edm_base_bock.setColor(base_color_prop)
        else:
            base_color_prop = pyedm.PropertyFloat3((mat_wrap.textures.albedo.default_color[0], mat_wrap.textures.albedo.default_color[1], mat_wrap.textures.albedo.default_color[2]))
            edm_base_bock.setColor(base_color_prop)

    edm_base_bock.setPositions(mesh_storage.positions)
    edm_base_bock.setNormals(mesh_storage.normals)

    return edm_base_bock

def make_def_rmo_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.AormsBlock:
    if not mat_wrap.textures.rmo.texture:
        return None
    
    edm_aorms_block = pyedm.AormsBlock()

    aorms_uv_map_name: str = mat_wrap.textures.rmo.texture.get_uv_map(mesh_storage.uv_active)
    edm_aorms_block.setAormsMapUV(mesh_storage.uv[aorms_uv_map_name])

    aorms_map_name: str = mat_wrap.textures.rmo.texture.texture_name
    edm_aorms_block.setAormsMap(aorms_map_name)

    return edm_aorms_block

def make_def_normal_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.NormalBlock:
    if not mat_wrap.textures.normal.texture:
        return None
    
    edm_normals_block = pyedm.NormalBlock()

    normals_uv_map_name: str = mat_wrap.textures.normal.texture.get_uv_map(mesh_storage.uv_active)
    edm_normals_block.setNormalMapUV(mesh_storage.uv[normals_uv_map_name])

    normal_map_name: str = mat_wrap.textures.normal.texture.texture_name
    edm_normals_block.setNormalMap(normal_map_name)

    return edm_normals_block

def make_def_ao_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.AoBlock:
    if not mat_wrap.textures.light_map.texture:
        return None
    
    ao_block = pyedm.AoBlock()

    ao_uv_name: str = mat_wrap.textures.light_map.texture.get_uv_map(mesh_storage.uv_active)
    ao_block.setAoMapUV(mesh_storage.uv[ao_uv_name])

    ao_map_name: str = mat_wrap.textures.light_map.texture.texture_name
    ao_block.setAoMap(ao_map_name)

    uv_shift_animation_path: str = mat_wrap.textures.light_map.texture.uv_move_loc_anim_path if mat_wrap.valid and mat_wrap.textures.light_map.texture.uv_move_node else None
    is_uv_shift_animated: bool = uv_shift_animation_path and anim.has_path_anim(mat_wrap.material.node_tree.animation_data, uv_shift_animation_path)
    arg_n: int = utils.extract_arg_number(mat_wrap.textures.light_map.texture.uv_move_node.label) if is_uv_shift_animated else -1
    if is_uv_shift_animated and arg_n != -1:
        key_list: anim.KeyFramePoints = anim.extract_anim_vec3(mat_wrap.material.node_tree.animation_data.action, uv_shift_animation_path, (0.0, 0.0, 0.0), lambda v: [v[0], 1.0 - v[1]])
        uv_shift_prop = pyedm.PropertyFloat2(arg_n, key_list)
        ao_block.setAoShift(uv_shift_prop)

    return ao_block
    
def check_emissive_texture_eq_rule(mat_wrap: DefMaterialWrap) -> None:
    if not mat_wrap.textures.emissive.texture or not mat_wrap.textures.emissive_mask.texture:
        return
    if not mat_wrap.textures.emissive.texture.texture_name == mat_wrap.textures.emissive_mask.texture.texture_name:
        log.fatal(f"Emissive texture has different alpha source on material {mat_wrap.name}. Emissive texure is {mat_wrap.textures.emissive.texture.texture_name} and alpha mask is {mat_wrap.textures.emissive_mask.texture.texture_name}")

def make_def_emissive_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.EmissiveBlock:
    if not mat_wrap.textures.emissive.texture and utils.cmp_vec4(mat_wrap.textures.emissive.default_color, (0.0, 0.0, 0.0, 1.0)):
        return None

    check_emissive_texture_eq_rule(mat_wrap)
    
    edm_emissive_block = pyedm.EmissiveBlock()
    
    if mat_wrap.textures.emissive.texture:
        edm_emissive_block.setEmissiveType(int(EDMCustomEmissiveTypeInt.DEFAULT))

        emissive_uv_map_name: str = mat_wrap.textures.emissive.texture.get_uv_map(mesh_storage.uv_active)
        edm_emissive_block.setEmissiveMapUV(mesh_storage.uv[emissive_uv_map_name])
    
        emissive_map_name: str = mat_wrap.textures.emissive.texture.texture_name
        edm_emissive_block.setEmissiveMap(emissive_map_name)
    else:
        edm_emissive_block.setEmissiveType(int(EDMCustomEmissiveTypeInt.SELF_ILLUMINATION))

        emissive_color_path: str = mat_wrap.textures.emissive.color_anim_path
        is_emissive_color_animated: bool = emissive_color_path and anim.has_path_anim(mat_wrap.material.node_tree.animation_data, emissive_color_path)
        if is_emissive_color_animated and edm_props.EMISSIVE_COLOR_ARG != -1:
            arg_color_n: int = edm_props.EMISSIVE_COLOR_ARG
            key_color_list: anim.KeyFramePoints = anim.extract_anim_vec4(mat_wrap.material.node_tree.animation_data.action, emissive_color_path, (0.0, 0.0, 0.0, 1.0), lambda v: [v[0], v[1], v[2]])
            emissive_color_prop = pyedm.PropertyFloat3(arg_color_n, key_color_list)
        else:
            emissive_color: Tuple[float, float, float] = (mat_wrap.textures.emissive.default_color[0], mat_wrap.textures.emissive.default_color[1], mat_wrap.textures.emissive.default_color[2])
            emissive_color_prop = pyedm.PropertyFloat3(emissive_color)
            
        edm_emissive_block.setColor(emissive_color_prop)

        if mat_wrap.textures.emissive_mask.texture:
            emissive_mask_uv_map_name: str = mat_wrap.textures.emissive_mask.texture.get_uv_map(mesh_storage.uv_active)
            edm_emissive_block.setEmissiveMapUV(mesh_storage.uv[emissive_mask_uv_map_name])

            emissive_mask_map_name: str = mat_wrap.textures.emissive_mask.texture.texture_name
            edm_emissive_block.setEmissiveMap(emissive_mask_map_name)
        
    emissive_value: float = mat_wrap.values.emissive_value.value
    emissive_value_prop = pyedm.PropertyFloat(emissive_value)
    emissive_value_anim_path: str = mat_wrap.values.emissive_value.anim_path if mat_wrap.valid else None
    is_emissive_value_animated: bool = emissive_value_anim_path and anim.has_path_anim(mat_wrap.material.node_tree.animation_data, emissive_value_anim_path)
    if is_emissive_value_animated and edm_props.EMISSIVE_ARG != -1:
        key_list: anim.KeyFramePoints = anim.extract_anim_float(mat_wrap.material.node_tree.animation_data.action, emissive_value_anim_path)
        arg_n: int = edm_props.EMISSIVE_ARG
        emissive_value_prop = pyedm.PropertyFloat(arg_n, key_list)
    edm_emissive_block.setAmount(emissive_value_prop)

    if mat_wrap.values.blend_mode.value == EdmTransparencySocketItemsEnum.SUM_BLENDING_SI:
        if not mat_wrap.textures.albedo.texture and not utils.cmp_vec4(mat_wrap.textures.emissive.default_color, (0.0, 0.0, 0.0, 1.0)):
            edm_emissive_block.setEmissiveType(int(EDMCustomEmissiveTypeInt.ADDITIVE_SELF_COLOR_ILLUMINATION))
        elif mat_wrap.textures.albedo.texture and mat_wrap.textures.emissive.texture:
            edm_emissive_block.setEmissiveType(int(EDMCustomEmissiveTypeInt.ADDITIVE_SELF_TEX_ILLUMINATION))
        else:
            edm_emissive_block.setEmissiveType(int(EDMCustomEmissiveTypeInt.ADDITIVE_SELF_ILLUMINATION))

    return edm_emissive_block

def make_def_flir_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.FlirBlock:
    if not mat_wrap.textures.flir.texture:
        return None
    
    edm_flir_block = pyedm.FlirBlock()

    flir_name: str = mat_wrap.textures.flir.texture.texture_name
    edm_flir_block.setFlirMap(flir_name)

    return edm_flir_block

def make_def_decal_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.DecalBlock:
    if not mat_wrap.textures.decal.texture:
        return None
    
    edm_decal_block = pyedm.DecalBlock()

    decal_uv_map_name: str = mat_wrap.textures.decal.texture.get_uv_map(mesh_storage.uv_active)
    edm_decal_block.setDecalMapUV(mesh_storage.uv[decal_uv_map_name])

    decal_map_name: str = mat_wrap.textures.decal.texture.texture_name
    edm_decal_block.setDecalMap(decal_map_name)

    uv_shift_animation_path: str = mat_wrap.textures.decal.texture.uv_move_loc_anim_path if mat_wrap.valid and mat_wrap.textures.decal.texture.uv_move_node else None
    is_uv_shift_animated: bool = uv_shift_animation_path and anim.has_path_anim(mat_wrap.material.node_tree.animation_data, uv_shift_animation_path)
    arg_n: int = utils.extract_arg_number(mat_wrap.textures.decal.texture.uv_move_node.label) if is_uv_shift_animated else -1
    if is_uv_shift_animated and arg_n != -1:
        key_list: anim.KeyFramePoints = anim.extract_anim_vec3(mat_wrap.material.node_tree.animation_data.action, uv_shift_animation_path, (0.0, 0.0, 0.0), lambda v: [v[0], 1.0 - v[1]])
        uv_shift_prop = pyedm.PropertyFloat2(arg_n, key_list)
        edm_decal_block.setDecalShift(uv_shift_prop)

    return edm_decal_block

def make_def_damage_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.DamageBlock:
    if not mat_wrap.textures.damage_color.texture or not mat_wrap.textures.damage_mask.texture:
        return None
    
    if edm_props.DAMAGE_ARG < 0 and not mesh_storage.has_dmg_group:
        return None

    edm_damage_block = pyedm.DamageBlock()
    if mesh_storage.has_dmg_group:
        edm_damage_block.setPerVertexArguments(mesh_storage.damage_arguments)

    damage_color_uv_map_name: str = mat_wrap.textures.damage_color.texture.get_uv_map(mesh_storage.uv_active)
    edm_damage_block.setAlbedoMapUV(mesh_storage.uv[damage_color_uv_map_name])

    damage_color_map_name: str = mat_wrap.textures.damage_color.texture.texture_name
    edm_damage_block.setAlbedoMap(damage_color_map_name)

    if mat_wrap.textures.damage_normal.texture:
        damage_normal_uv_map_name: str = mat_wrap.textures.damage_normal.texture.get_uv_map(mesh_storage.uv_active)
        edm_damage_block.setNormalMapUV(mesh_storage.uv[damage_normal_uv_map_name])

        damage_normal_map_name: str = mat_wrap.textures.damage_normal.texture.texture_name
        edm_damage_block.setNormalMap(damage_normal_map_name)

    damage_mask_name: str = mat_wrap.textures.damage_mask.texture.texture_name
    edm_damage_block.setMaskRGBA(damage_mask_name)

    edm_damage_block.setArgument(edm_props.DAMAGE_ARG)

    return edm_damage_block

def make_def_bone_block(mesh_storage: MeshStorage, mat_wrap: DefMaterialWrap, edm_props: EDMPropsGroup) -> pyedm.BoneBlock:
    if not mesh_storage.armature:
        return None
    
    edm_bone_block = pyedm.BoneBlock()
    edm_bone_block.setBoneIndices(mesh_storage.bone_indices)
    edm_bone_block.setBoneWeights(mesh_storage.bone_weights)

    bone_names = list(mesh_storage.bones.items())
    bone_names.sort(key=lambda x : x[1])
    bone_names = [x[0] for x in bone_names]

    edm_bone_block.setBoneNames(bone_names)

    return edm_bone_block

BlockCustomType = Union[pyedm.BaseBlock, pyedm.AormsBlock, pyedm.NormalBlock, pyedm.AoBlock, pyedm.EmissiveBlock, pyedm.FlirBlock, pyedm.DecalBlock, pyedm.DamageBlock, pyedm.BoneBlock, None]
RenderNodeCustomType = Union[pyedm.PBRNode, pyedm.DeckNode, pyedm.MirrorNode, None]

BLOCK_FUNCTIONS = [
    make_def_base_block,
    make_def_rmo_block,
    make_def_normal_block,
    make_def_decal_block,
    make_def_emissive_block,
    make_def_ao_block,
    make_def_flir_block,
    make_def_damage_block,
    make_def_bone_block,
]

class BlockEnum(str, Enum):
    BT_Base     = 'BT_Base'
    BT_Normal   = 'BT_Normal'
    BT_Flir     = 'BT_Flir'
    BT_Damage   = 'BT_Damage'
    BT_Aorms    = 'BT_Aorms'
    BT_Bone     = 'BT_Bone'
    BT_Emissive = 'BT_Emissive'
    BT_Ao       = 'BT_Ao'
    BT_Decal    = 'BT_Decal'
    BT_Glass    = 'BT_Glass'


def create_blocks(mesh_storage: MeshStorage, material_wrap: MaterialWrap, edm_props: EDMPropsGroup) -> List[BlockCustomType]:
    blocks: List[BlockCustomType] = []
    for block_function in BLOCK_FUNCTIONS:
        block = block_function(mesh_storage, material_wrap, edm_props)
        if block:
            blocks.append(block)

    return blocks

def get_transparency_value(transparency_value) -> int:
    if transparency_value == TransparencyEnumItems[0][0]:
        return 0
    elif transparency_value == TransparencyEnumItems[1][0]:
        return 1
    elif transparency_value == TransparencyEnumItems[2][0]:
        return 2
    elif transparency_value == TransparencyEnumItems[3][0]:
        return 3
    elif transparency_value == TransparencyEnumItems[4][0]:
        return 3
    elif transparency_value == TransparencyEnumItems[5][0]:
        return 6
    else:
        return 0

def get_shadow_caster_value(shadow_caster_value) -> int:
    if shadow_caster_value == ShadowCasterEnumItems[0][0]:
        return 0
    elif shadow_caster_value == ShadowCasterEnumItems[1][0]:
        return 1
    elif shadow_caster_value == ShadowCasterEnumItems[2][0]:
        return 2
    else:
        return 0


def make_def_edm_mat_blocks(object: Object, material_wrap: DefMaterialWrap, mesh_storage: MeshStorage) -> pyedm.PBRNode:
    edm_props = get_edm_props(object)
    edm_render_node = pyedm.PBRNode(object.name, material_wrap.material.name)
    edm_render_node.setIndices(mesh_storage.indices)

    blocks = create_blocks(mesh_storage, material_wrap, edm_props)
    for block in blocks:
        edm_render_node.addBlock(block)
    
    decal_id: int = material_wrap.values.decal_id.value
    if(decal_id < 0 or decal_id > 8):
        log.fatal(f"{material_wrap.name} material has wrong value {str(decal_id)}. Decal id must be in 0 to 8 range.")
    edm_render_node.setDecalId(decal_id)
    
    transparency_mode: int = get_transparency_value(material_wrap.values.blend_mode.value)
    edm_render_node.setTransparentMode(transparency_mode)

    shadow_caster_type: int = get_shadow_caster_value(material_wrap.values.shadow_caster.value)
    edm_render_node.setShadowCaster(shadow_caster_type)

    opacity_value_path: str = material_wrap.values.opacity_value.anim_path
    is_color_value_animated: bool = opacity_value_path and anim.has_path_anim(material_wrap.material.node_tree.animation_data, opacity_value_path)
    if is_color_value_animated and edm_props.OPACITY_VALUE_ARG != -1:
        arg_opacity_value_n: int = edm_props.OPACITY_VALUE_ARG
        key_opacity_value_list: anim.KeyFramePoints = anim.extract_anim_float(material_wrap.material.node_tree.animation_data.action, opacity_value_path)
        opacity_value_prop = pyedm.PropertyFloat(arg_opacity_value_n, key_opacity_value_list)
        edm_render_node.setOpacityValue(opacity_value_prop)
    else:
        opacity_value_prop = pyedm.PropertyFloat(material_wrap.values.opacity_value.value)
        edm_render_node.setOpacityValue(opacity_value_prop)

    two_sided: bool = edm_props.TWO_SIDED
    edm_render_node.setTwoSided(two_sided)

    return edm_render_node

def make_deck_edm_mat_blocks(object: Object, material_wrap: DeckMaterialWrap, mesh_storage: MeshStorage, edm_props: EDMPropsGroup) -> pyedm.DeckNode:
    edm_render_node = pyedm.DeckNode(object.name, material_wrap.material.name)
    edm_render_node.setPositions(mesh_storage.positions)
    edm_render_node.setNormals(mesh_storage.normals)
    edm_render_node.setIndices(mesh_storage.indices)

    transparency_mode: int = get_transparency_value(material_wrap.values.blend_mode.value)
    edm_render_node.setTransparentMode(transparency_mode)

    decal_id: int = material_wrap.values.decal_id.value
    if(decal_id < 0 or decal_id > 8):
        log.fatal(f"{material_wrap.name} material has wrong value {str(decal_id)}. Decal id must be in 0 to 8 range.")
    edm_render_node.setDecalId(decal_id)

    if material_wrap.textures.base_tile_map.texture:
        base_tile_uv_map_name: str = material_wrap.textures.base_tile_map.texture.get_uv_map(mesh_storage.uv_active)
        edm_render_node.setTiledUV(mesh_storage.uv[base_tile_uv_map_name])

        base_tile_map_name: str = material_wrap.textures.base_tile_map.texture.texture_name
        edm_render_node.setBaseTiledMap(base_tile_map_name)

    if material_wrap.textures.normal_tile_map.texture:
        normal_tile_map_name: str = material_wrap.textures.normal_tile_map.texture.texture_name
        edm_render_node.setNormalTiledMap(normal_tile_map_name)

    if material_wrap.textures.rmo_tile_map.texture:
        rmo_tile_map_name: str = material_wrap.textures.rmo_tile_map.texture.texture_name
        edm_render_node.setAormsTiledMap(rmo_tile_map_name)

    if material_wrap.textures.decal_map.texture:
        base_uv_map_name: str = material_wrap.textures.decal_map.texture.get_uv_map(mesh_storage.uv_active)
        edm_render_node.setRegularUV(mesh_storage.uv[base_uv_map_name])

        base_map_name: str = material_wrap.textures.decal_map.texture.texture_name
        edm_render_node.setBaseMap(base_map_name)

    if material_wrap.textures.decal_rmo.texture:
        rmo_map_name: str = material_wrap.textures.decal_rmo.texture.texture_name
        edm_render_node.setAormsMap(rmo_map_name)

    if material_wrap.textures.damage_color.texture:
        damage_map_name: str = material_wrap.textures.damage_color.texture.texture_name
        edm_render_node.setDamageMap(damage_map_name)

    if material_wrap.textures.damage_mask.texture:
        damage_mask_name: str = material_wrap.textures.damage_mask.texture.texture_name
        edm_render_node.setDamageMaskRGBA(damage_mask_name)

    if material_wrap.textures.rain_mask.texture:
        rain_mask_name: str = material_wrap.textures.rain_mask.texture.texture_name
        edm_render_node.setRainMask(rain_mask_name)

    edm_render_node.setArgument(edm_props.DAMAGE_ARG)

    return edm_render_node

def make_glass_edm_mat_blocks(object: Object, material_wrap: DefMaterialWrap, mesh_storage: MeshStorage) -> pyedm.PBRNode:
    edm_props = get_edm_props(object)
    edm_render_node = pyedm.PBRNode(object.name, material_wrap.material.name)
    edm_render_node.setIndices(mesh_storage.indices)

    blocks = create_blocks(mesh_storage, material_wrap, edm_props)
    for b in blocks:
        edm_render_node.addBlock(b)
    
    decal_id: int = material_wrap.values.decal_id.value
    if(decal_id < 0 or decal_id > 8):
        log.fatal(f"{material_wrap.name} material has wrong value {str(decal_id)}. Decal id must be in 0 to 8 range.")
    edm_render_node.setDecalId(decal_id)

    edm_render_node.setTransparentMode(int(material_wrap.blend_mode))
    edm_render_node.setShadowCaster(int(material_wrap.shadow_caster))

    two_sided: bool = edm_props.TWO_SIDED
    edm_render_node.setTwoSided(two_sided)

    return edm_render_node

def make_mirror_edm_mat_blocks(object: Object, material_wrap: MirrorMaterialWrap, mesh_storage: MeshStorage) -> pyedm.MirrorNode:
    edm_render_node = pyedm.MirrorNode(object.name, material_wrap.material.name)
    edm_render_node.setPositions(mesh_storage.positions)
    edm_render_node.setNormals(mesh_storage.normals)
    edm_render_node.setIndices(mesh_storage.indices)

    if material_wrap.textures.base_color.texture:
        base_color_uv_map_name: str = material_wrap.textures.base_color.texture.get_uv_map(mesh_storage.uv_active)
        edm_render_node.setTextureCoordinates(mesh_storage.uv[base_color_uv_map_name])

        base_color_name: str = material_wrap.textures.base_color.texture.texture_name
        edm_render_node.setTexture(base_color_name)

    return edm_render_node