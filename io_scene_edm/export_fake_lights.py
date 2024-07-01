import math 
import numpy as np
import re

from typing import List, Union, Tuple, Union, Sequence, Callable
from enums import ObjectTypeEnum, NodeGroupTypeEnum, EDMPropsSpecialTypeStr

import animation as anim
import bpy
from bpy.types import Object, Mesh, MeshVertex, MeshVertices
from mathutils import Vector, Quaternion, Matrix

from objects_custom_props import get_edm_props
from pyedm_platform_selector import pyedm
from logger import log
from material_wrap import (FakeOmniLightMaterialWrap, FakeSpotLightMaterialWrap, g_missing_texture_name)
from mesh_storage import MeshStorage
from math_tools import RIGHT_TRANSFORM_MATRIX
import utils

from objects_custom_props import EDMPropsGroup
from mesh_builder import get_mesh

FakeLightIndex = int
FakeLightDelay = float
FakeLightIdxToFrameList = List[Tuple[FakeLightIndex, anim.KeyFramePoints]]

def is_fake_light(object: bpy.types.Object) -> bool:
    edm_props = get_edm_props(object)
    if object.type == ObjectTypeEnum.MESH and edm_props.SPECIAL_TYPE in ('FAKE_LIGHT'):
        return True
    return False

def get_delay_anim_list(lights_anim_delay_list: List[FakeLightDelay], key_list: anim.KeyFramePoints) -> FakeLightIdxToFrameList:
    fake_lights_anim_list: List[FakeLightIndex, anim.KeyFramePoints] = []
    if not key_list:
        return fake_lights_anim_list
    first_key_frame: anim.KeyFramePoint = key_list[0]
    for fake_light_index in range(0, len(lights_anim_delay_list)):
        delay: float = lights_anim_delay_list[fake_light_index]
        new_key_frame_points: anim.KeyFramePoints = []
        for key_frame_index in range(0, len(key_list)):
            key_frame: anim.KeyFramePoint = key_list[key_frame_index]
            #old_key_fame_time = key_frame[0]
            old_key_fame_time = key_frame[0] - first_key_frame[0]
            old_key_fame_point = key_frame[1]
            new_key_fame_time: float = np.clip(old_key_fame_time + delay, -1.0, 1.0)
            #new_key_fame_time_normalized: float = (new_key_fame_time + 1.0) * 0.5
            new_key_fame_time_normalized: float = new_key_fame_time * 0.5
            new_key: anim.KeyFrameTime = new_key_fame_time_normalized
            new_key_frame_points.append((new_key, old_key_fame_point))
        fake_lights_anim_list.append((fake_light_index, new_key_frame_points))
    return fake_lights_anim_list

def get_pos(vertex: MeshVertex) -> Tuple[float, float, float]:
    pos_x: float = vertex.co[0]
    pos_y: float = vertex.co[1]
    pos_z: float = vertex.co[2]
    return pos_x, pos_y, pos_z

def get_pos_list(vertices_list: MeshVertices) -> List[Tuple[float, float, float]]:
    pos_list: List[Tuple[float, float, float]] = []
    for vertex in vertices_list:
        pos1 = get_pos(vertex)
        pos_list.append(pos1)
    return pos_list

ObjectCheckFn = Callable[[Object], bool]

fake_light_dir_re_c = re.compile(r'^([Ll]ight_[Dd]ir(ection)?|[Ll][Dd])')
def fake_light_obj_test(obj: Object) -> bool:
    is_type_match: bool = obj.type == ObjectTypeEnum.EMPTY
    is_name_match: bool = re.match(fake_light_dir_re_c, obj.name)
    return is_type_match and is_name_match

def get_first_children(object_children: Sequence[Object], obj_fn: ObjectCheckFn) -> Union[Object, None]:
    if not object_children:
        return None
    for child_obj in object_children:
        is_obj_match: bool = obj_fn(child_obj)
        if is_obj_match:
            return child_obj
    return None

def get_children(object_children: Sequence[Object], obj_fn: ObjectCheckFn) -> List[Object]:
    result: List[Object] = []
    if not object_children:
        return result
    for child_obj in object_children:
        is_obj_match: bool = obj_fn(child_obj)
        if is_obj_match:
            result.append(child_obj)
    return result

def check_fake_light_direction(object: Object) -> None:
    chilren_dir: List[Object] = get_children(object.children, fake_light_obj_test)

    if len(chilren_dir) > 1:
        log.warning(f"{object.name} fake spot light has more then one child direction objects.")
        for chold_obj in chilren_dir:
            log.warning(f"{chold_obj.name} -- fake spot light child direction.")

def get_fake_light_direction(object: Object) -> Tuple[float, float, float]:
    light_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    check_fake_light_direction(object)
    light_dir_obj: Object = get_first_children(object.children, fake_light_obj_test)
    if light_dir_obj:
        world_matrix: Matrix = light_dir_obj.matrix_world
    else:
        world_matrix: Matrix = object.matrix_world
        
    loc, rot, sca = world_matrix.decompose()
    qrot: Quaternion = rot
    rot_mat = qrot.to_matrix()
    rot_mat = RIGHT_TRANSFORM_MATRIX.to_3x3() @ rot_mat.copy()
    trans_ld: Vector = rot_mat @ Vector(light_direction)
    return (trans_ld.x, trans_ld.y, trans_ld.z)

## convert normal vector from blender coordinate system to edm coordinate system
def convert_coordinates(normals: np.array, object: Object) -> Tuple[float, float, float]:
    
    normals = np.matmul(normals, np.array(RIGHT_TRANSFORM_MATRIX.to_3x3() @ object.matrix_world.to_3x3()))
    normals = [tuple(vec) for vec in normals]
    return normals
    
## method returns dict of uv coordinates. 
def parse_uv_coords(bpy_mesh: Mesh, indxs_of_vertices: np.array):
    nVertex_in_face = 4
    uv_coords_dim = 2
    faces_count = len(bpy_mesh.polygons)
    
    # check texture layers names
    max_possible_layers = 2
    uv_layers = bpy_mesh.uv_layers
    if len(uv_layers) > max_possible_layers:
        log.fatal(f'Too much texture layers. {max_possible_layers} layers is maximum')
    
    is_two_side = False
    if len(uv_layers) == max_possible_layers:
        is_two_side = True

    # dict where values are texture map names from blender
    layers_uv_names = {}
    front_name = 'front' # key in the dict
    back_name = 'back' # 1) key in the dict 2) key word to search in uv_layers name
    if is_two_side:
        back_indx = [i for i, s in enumerate(uv_layers) if back_name in s.name.lower()]
        if len(back_indx) == 0:
            log.fatal(f'Cound not find texture layer for back side. Check the name of texture, it must contain f"{back_name}" suffix.')
        
        layers_uv_names[front_name] = uv_layers[max_possible_layers - back_indx[0] - 1].name        
        layers_uv_names[back_name] = uv_layers[back_indx[0]].name
    else:
        layers_uv_names[front_name] = uv_layers[0].name
    
    uvs = {}
    for uv_key, uv_name in layers_uv_names.items():
        uv_loop = uv_layers[uv_name]
        if len(uv_loop.uv) == 0:
            uvs[uv_key] = np.array([], dtype=np.float32)
            continue
        # maximum number of uv coords = faces_count * nVertex_in_face * uv_coords_dim, but it could be less in some cases.
        buf = np.empty(faces_count * nVertex_in_face * uv_coords_dim, dtype=np.float32)
        
        # parse uv coords values
        uv_loop.uv.foreach_get('vector', buf)
        buf = np.reshape(buf, (buf.size // uv_coords_dim, uv_coords_dim))

        uv_coords = np.zeros(shape=(faces_count, nVertex_in_face, uv_coords_dim),  dtype=np.float32)
        for j in range(nVertex_in_face):
            uv_coords[:, j, :] = buf[indxs_of_vertices[:, j]]

        res_map = np.zeros(shape=(faces_count, 2, uv_coords_dim), dtype=np.float32)
        # TODO: range(faces_count)... it is better to avoid loop trough faces
        for i in range(faces_count):
            x_min = np.min(uv_coords[i, :, 0], axis=0)
            x_max = np.max(uv_coords[i, :, 0], axis=0)
            y_min = np.min(uv_coords[i, :, 1], axis=0)
            y_max = np.max(uv_coords[i, :, 1], axis=0)

            res_map[i] = np.array([[x_min, y_min], [x_max, y_max]])
        
        uvs[uv_key] = res_map    
   
    return uvs

## parse faces of object and return center of each face, normal vectors, size of light.
def parse_faces(bpy_mesh: Mesh, object: Object):
    dim = 3
    faces_count = len(bpy_mesh.polygons)

    normals = np.empty(faces_count * dim, dtype=np.float32)
    bpy_mesh.polygons.foreach_get('normal', normals) 
    normals = np.reshape(normals, (faces_count, dim), order='C')

    normals = convert_coordinates(normals, object)

    centers = np.empty(faces_count * dim, dtype=np.float32)
    bpy_mesh.polygons.foreach_get('center', centers) 
    centers = np.reshape(centers, (faces_count, dim), order='C')

    # to apply texture we need to extract verticies
    vert_count = len(bpy_mesh.vertices)
    vertices = np.empty(vert_count * dim, dtype=np.float32)
    bpy_mesh.vertices.foreach_get('co', vertices) 
    vertices = np.reshape(vertices, (vert_count, dim), order='C')

    points_count = 4     # each face has 4 vertices (this is expected)
    # for each face get np.array with indxes of vertices in this face.
    indxs = np.empty(faces_count * points_count, dtype=np.int32)
    bpy_mesh.polygons.foreach_get('vertices', indxs)
    indxs_of_vertices = np.reshape(indxs, (faces_count, points_count), order='C')
    uvs = parse_uv_coords(bpy_mesh, indxs_of_vertices)

    # calculate diagonal of each polygon by finding light_sizes=maximum(|p0-p1|, |p0-p2|, |p0-p3|)
    indxs = np.reshape(indxs, (points_count, faces_count), order='F')
    sides_polygons = np.zeros(shape=(faces_count, 3))
    for i in range(0, points_count-1):
        sides_polygons[:, i] = np.linalg.norm(vertices[indxs[0]] - vertices[indxs[i+1]], axis=1)

    light_sizes = np.max(sides_polygons, axis=1)

    return centers, normals, light_sizes, uvs

def make_fake_omni_edm_mat_blocks(object: Object, material_wrap: FakeOmniLightMaterialWrap, mesh_storage: MeshStorage) -> pyedm.FakeOmniLights:
    if material_wrap.node_group_type != NodeGroupTypeEnum.FAKE_OMNI:
        log.warning(f"{object.name} has no fake omni material.")
        return None

    edm_props = get_edm_props(object)
    
    is_color_texture: bool = not material_wrap.textures.emissive_map.texture == None
    if is_color_texture:
        light_texture: str = material_wrap.textures.emissive_map.texture.texture_name
    else:
        light_texture: str = g_missing_texture_name
        log.warning(f"{object.name} fake omni must have emissive texture.")
    
    min_size_pixels: float = material_wrap.values.min_size_pixels.value
    max_distance: float = material_wrap.values.max_distance.value
    shift_to_camera: float = material_wrap.values.shift_to_camera.value
    luminance: float = material_wrap.values.luminance.value
    edm_luminance_prop = pyedm.PropertyFloat(luminance)
    luminance_animation_path: str = material_wrap.values.luminance.anim_path if material_wrap.valid else None
    is_luminance_animated: bool = luminance_animation_path and anim.has_path_anim(material_wrap.material.node_tree.animation_data, luminance_animation_path)
    brightness_animation_path: str = 'EDMProps.ANIMATED_BRIGHTNESS'
    is_brightness_animated: bool = anim.has_path_anim(object.animation_data, brightness_animation_path)
    brightness_arg_n: int = utils.extract_arg_number(object.animation_data.action.name) if is_brightness_animated else -1

    # only if surface mode is off
    if not edm_props.SURFACE_MODE:            
        uv_start: Tuple[float, float] = edm_props.UV_LB[0], edm_props.UV_LB[1]
        uv_end: Tuple[float, float] = edm_props.UV_RT[0], edm_props.UV_RT[1]
        light_size: float = edm_props.SIZE 
   
    fake_lights: List[pyedm.FakeOmniLight] = []
    is_vertex_group_set: bool = False
    
    if object.type == ObjectTypeEnum.MESH:
        bpy_mesh = get_mesh(object)

        if edm_props.SURFACE_MODE:  
            centers, normals, light_sizes, uv_layers = parse_faces(bpy_mesh, object)   
            uvs = uv_layers['front']

            for center, light_size, uv in zip(centers, light_sizes, uvs):
                ## create omni light
                edm_fake_omni = pyedm.FakeOmniLight()
                edm_fake_omni.setSize(float(light_size))
                edm_fake_omni.setPos(tuple(center))
                (pt1, pt2) = tuple(map(tuple, uv))
                edm_fake_omni.setUV(pt1, pt2)
                fake_lights.append(edm_fake_omni)      
        else:
            lights_anim_delay_list: List[FakeLightDelay] = []
            FakeLightIndex = 0
            for vertex in bpy_mesh.vertices:
                pos: Tuple[float, float, float] = get_pos(vertex)
                edm_fake_omni = pyedm.FakeOmniLight()
                edm_fake_omni.setSize(light_size)
                edm_fake_omni.setPos(pos)
                edm_fake_omni.setUV(uv_start, uv_end)
                fake_lights.append(edm_fake_omni)
                if len(vertex.groups) > 0:
                    is_vertex_group_set = True
                    lights_anim_delay_list.append(vertex.groups[0].weight)
                else:
                    lights_anim_delay_list.append(0.0)
                FakeLightIndex += 1
    elif object.type == ObjectTypeEnum.CURVE:
        pass

    if is_luminance_animated and edm_props.LUMINANCE_ARG != -1 and is_brightness_animated and brightness_arg_n != -1 and is_vertex_group_set:
        log.warning(f"{object.name} fake omni light has material and geometry luminamce animation. Only geometry luminamce animation exported!")
    if is_luminance_animated and edm_props.LUMINANCE_ARG == -1:
        log.warning(f"{object.name} fake omni light has material animation but LUMINANCE_ARG not set.")
    if is_brightness_animated and brightness_arg_n == -1 and is_vertex_group_set:
        log.warning(f"{object.name} fake omni light has geometry animation but brightness action name not has arg.")

    if is_luminance_animated and edm_props.LUMINANCE_ARG != -1:
        key_list: anim.KeyFramePoints = anim.extract_anim_float(material_wrap.material.node_tree.animation_data.action, luminance_animation_path)
        arg_n: int = edm_props.LUMINANCE_ARG
        edm_luminance_prop = pyedm.PropertyFloat(arg_n, key_list)
    
    if is_brightness_animated and brightness_arg_n != -1 and is_vertex_group_set:
        if object.type == edm_props.SURFACE_MODE:
            log.debug("vertex groups are not supported for surface mode right now.")
        else:
            edm_render_node = pyedm.AnimatedFakeOmniLight(object.name)
            key_list: anim.KeyFramePoints = anim.extract_anim_float(object.animation_data.action, brightness_animation_path)
            fake_lights_anim_list: List[FakeLightIndex, anim.KeyFramePoints] = get_delay_anim_list(lights_anim_delay_list, key_list)
            edm_render_node.setAnimationArg(brightness_arg_n)
            edm_render_node.setLightsAnimation(fake_lights_anim_list)
    elif is_brightness_animated and brightness_arg_n != -1 and not is_vertex_group_set:
        edm_render_node = pyedm.FakeOmniLights(object.name)
        key_list: anim.KeyFramePoints = anim.extract_anim_float(object.animation_data.action, brightness_animation_path)
        edm_luminance_prop = pyedm.PropertyFloat(brightness_arg_n, key_list)
    else:
        edm_render_node = pyedm.FakeOmniLights(object.name)

    edm_render_node.setMinSizeInPixels(min_size_pixels)
    edm_render_node.setShiftToCamera(shift_to_camera)
    edm_render_node.setLuminance(edm_luminance_prop)
    edm_render_node.setTexture(light_texture)
    edm_render_node.setMaxDistance(max_distance)
    edm_render_node.set(fake_lights)

    return edm_render_node

def make_fake_spot_edm_mat_blocks(object: Object, material_wrap: FakeSpotLightMaterialWrap, mesh_storage: MeshStorage) -> pyedm.FakeSpotLights:
    if material_wrap.node_group_type != NodeGroupTypeEnum.FAKE_SPOT:
        log.warning(f"{object.name} has no fake spot material.")
        return None
    
    edm_props = get_edm_props(object)

    is_color_texture: bool = not material_wrap.textures.emissive.texture == None
    if is_color_texture:
        light_texture: str = material_wrap.textures.emissive.texture.texture_name
    else:
        light_texture: str = g_missing_texture_name
        log.warning(f"{object.name} fake spot must have emissive texture.")
    
    min_size_pixels: float = material_wrap.values.min_size_pixels.value
    max_distance: float = material_wrap.values.max_distance.value
    shift_to_camera: float = material_wrap.values.shift_to_camera.value
    luminance: float = material_wrap.values.luminance.value
    
    luminance_animation_path: str =  material_wrap.values.luminance.anim_path if material_wrap.valid else None
    is_luminance_animated: bool = luminance_animation_path and anim.has_path_anim(material_wrap.material.node_tree.animation_data, luminance_animation_path)
    brightness_animation_path: str = 'EDMProps.ANIMATED_BRIGHTNESS'
    is_brightness_animated: bool = anim.has_path_anim(object.animation_data, brightness_animation_path)
    brightness_arg_n: int = utils.extract_arg_number(object.animation_data.action.name) if is_brightness_animated else -1
    
    edm_luminance_prop = pyedm.PropertyFloat(luminance)

    # spot light characteristics
    phi: float = material_wrap.values.phi.value
    theta: float = material_wrap.values.theta.value
    cone_setup: Tuple[float, float, float] = (
        math.cos(math.radians(theta)),  #cos of inner cone angle
        math.cos(math.radians(phi)),    #cos of outer cone angle
        0.05                            #min attenuation value
    )

    light_direction = None
    if not edm_props.SURFACE_MODE:
        two_sided: bool = edm_props.TWO_SIDED
        uv_start: Tuple[float, float] = edm_props.UV_LB[0], edm_props.UV_LB[1]
        uv_end: Tuple[float, float] = edm_props.UV_RT[0], edm_props.UV_RT[1]
        uv_start_back: Tuple[float, float] = edm_props.UV_LB_BACK[0], edm_props.UV_LB_BACK[1]
        uv_end_back: Tuple[float, float] = edm_props.UV_RT_BACK[0], edm_props.UV_RT_BACK[1]
        light_size: float = edm_props.SIZE 
        
        # single light direction   
        light_direction = get_fake_light_direction(object) #: Tuple[float, float, float]

    fake_lights: List[pyedm.FakeSpotLight] = []
    lights_anim_delay_list: List[FakeLightDelay] = [] # only for rabbit lights
    is_vertex_group_set: bool = False
    
    if object.type == ObjectTypeEnum.MESH:
        FakeLightIndex = 0
        bpy_mesh = get_mesh(object)

        if edm_props.SURFACE_MODE:
            centers, normals, light_sizes, uv_layers = parse_faces(bpy_mesh, object)
            # TODO add support for multiple light direction in cpp native code
            light_direction = normals[0]

            uvs_front = uv_layers['front']

            for i, (center, light_size, uv_f) in enumerate(zip(centers, light_sizes, uvs_front)):
                edm_fake_spot = pyedm.FakeSpotLight()
                edm_fake_spot.setSize(float(light_size))
                edm_fake_spot.setPos(tuple(center))
                (pt1, pt2) = tuple(map(tuple, uv_f))
                edm_fake_spot.setUV(pt1, pt2)         
                if len(uv_layers) > 1:
                    edm_fake_spot.setBackSide(True)
                    (pt1, pt2) = tuple(map(tuple, uv_layers['back'][i]))
                    edm_fake_spot.setBackUV(pt1, pt2)
                else:
                    edm_fake_spot.setBackSide(False)
                
                fake_lights.append(edm_fake_spot)

                # TODO: not sure this is needed for surface mode
                lights_anim_delay_list.append(0.0)
                FakeLightIndex += 1
        else:
            for vertex in bpy_mesh.vertices:
                pos: Tuple[float, float, float] = get_pos(vertex)
                edm_fake_spot = pyedm.FakeSpotLight()
                edm_fake_spot.setSize(light_size)
                edm_fake_spot.setPos(pos)
                edm_fake_spot.setUV(uv_start, uv_end)
                edm_fake_spot.setBackSide(two_sided)
                edm_fake_spot.setBackUV(uv_start_back, uv_end_back)
                fake_lights.append(edm_fake_spot)
                if len(vertex.groups) > 0:
                    is_vertex_group_set = True
                    lights_anim_delay_list.append(vertex.groups[0].weight)
                else:
                    lights_anim_delay_list.append(0.0)
                FakeLightIndex += 1
    elif object.type == ObjectTypeEnum.CURVE:
        pass

    if is_luminance_animated and edm_props.LUMINANCE_ARG != -1 and is_brightness_animated and brightness_arg_n != -1 and is_vertex_group_set:
        log.warning(f"{object.name} fake spot light has material and geometry luminamce animation. Only geometry luminamce animation exported!")
    if is_luminance_animated and edm_props.LUMINANCE_ARG == -1:
        log.warning(f"{object.name} fake spot light has material animation but LUMINANCE_ARG not set.")
    if is_brightness_animated and brightness_arg_n == -1 and is_vertex_group_set:
        log.warning(f"{object.name} fake spot light has geometry animation but brightness action name not has arg.")
    
    if is_luminance_animated and edm_props.LUMINANCE_ARG != -1:
        key_list: anim.KeyFramePoints = anim.extract_anim_float(material_wrap.material.node_tree.animation_data.action, luminance_animation_path)
        arg_n: int = edm_props.LUMINANCE_ARG
        edm_luminance_prop = pyedm.PropertyFloat(arg_n, key_list)

    # light animation: rabbit lights
    if is_brightness_animated and brightness_arg_n != -1 and is_vertex_group_set:
        edm_render_node = pyedm.AnimatedFakeSpotLight(object.name)
        key_list: anim.KeyFramePoints = anim.extract_anim_float(object.animation_data.action, brightness_animation_path)
        fake_lights_anim_list: List[FakeLightIndex, anim.KeyFramePoints] = get_delay_anim_list(lights_anim_delay_list, key_list)
        edm_render_node.setAnimationArg(brightness_arg_n)
        edm_render_node.setLightsAnimation(fake_lights_anim_list)
    # light animation: flashing lamp
    elif is_brightness_animated and brightness_arg_n != -1 and not is_vertex_group_set:
        edm_render_node = pyedm.FakeSpotLights(object.name)
        key_list: anim.KeyFramePoints = anim.extract_anim_float(object.animation_data.action, brightness_animation_path)
        edm_luminance_prop = pyedm.PropertyFloat(brightness_arg_n, key_list)
    # no animation
    else:
        edm_render_node = pyedm.FakeSpotLights(object.name)

    edm_render_node.setMinSizeInPixels(min_size_pixels)
    edm_render_node.setShiftToCamera(shift_to_camera)
    edm_render_node.setLuminance(edm_luminance_prop)
    edm_render_node.setConeSetup(cone_setup)
    edm_render_node.setDirection(light_direction)
    edm_render_node.setMaxDistance(max_distance)    
    edm_render_node.setTexture(light_texture)
    edm_render_node.set(fake_lights)

    return edm_render_node

class FakeLightChildPanel(bpy.types.Panel):
    bl_label = "Fake light type Properties"
    bl_idname = "OBJECT_PT_fake_light_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "OBJECT_PT_edm_data"

    @classmethod
    def poll(cls, context):
        if not utils.has_object(context):
            return

        object: Object = context.object
        props = get_edm_props(object)

        result = props.SPECIAL_TYPE in (EDMPropsSpecialTypeStr.FAKE_LIGHT) and not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP)
        return result

    def draw(self, context):
        if not utils.has_object(context):
            return

        layout = self.layout
        object: Object = context.object
        props = get_edm_props(object)
        
        box = layout.row()
        row = box.row()
        row.prop(props, "SURFACE_MODE")

        if not props.SURFACE_MODE:
            row = box.row()
            row.prop(props, "TWO_SIDED")

        row = layout.row()
        row.prop(props, "LUMINANCE_ARG")

        if not props.SURFACE_MODE:
            box = layout.box()

            row = box.row()
            row.prop(props, "UV_LB")

            row = box.row()
            row.prop(props, "UV_RT")

            if props.TWO_SIDED:
                row = box.row()
                row.prop(props, "UV_LB_BACK")

                row = box.row()
                row.prop(props, "UV_RT_BACK")

            row = layout.row()
            row.prop(props, "SIZE")
        
        row = layout.row()        
        row.prop(props, "ANIMATED_BRIGHTNESS")
