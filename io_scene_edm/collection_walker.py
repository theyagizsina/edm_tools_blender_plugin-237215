import cProfile
import io
import os.path
import pstats
import sys
import traceback

import bpy
from mathutils import Matrix

import animation as anim
import logger
from objects_custom_props import get_edm_props
from pyedm_platform_selector import pyedm
from export_armature import export_armature, build_bone_id
from block_builder import BlockEnum
from edm_exception import EdmException
from enums import NodeGroupTypeEnum, ObjectTypeEnum
from export_lights import export_light, is_light
from export_connectors import export_connector, is_connector
from export_fake_lights import is_fake_light
from export_segments import create_segments_node, is_segment
from logger import LogCtx, log
from material_cache import MaterialCache
from materials import get_material, Materials
from math_tools import ROOT_TRANSFORM_MATRIX, get_aa_bb, IDENTITY_MATRIX
from mesh_builder import buld_mesh
from mesh_storage import get_armature_from_modifiers
from object_node import (DummyNode, LodLeaf, LodRoot, ObjectNodeCustomType, SceneRootNode)
from object_node_tree import ObjectNodeTree
from visibility_animation import extract_visibility_animation
from dev_mode import get_dev_mode_props
from arg_panel import get_arg_panel_props
import utils

def is_aa_bb(object: bpy.types.Object) -> bool:
    edm_props = get_edm_props(object)
    if object.type == ObjectTypeEnum.EMPTY and edm_props.SPECIAL_TYPE in ('USER_BOX', 'BOUNDING_BOX', 'LIGHT_BOX'):
        return True
    return False

def is_mesh(object: bpy.types.Object) -> bool:
    edm_props = get_edm_props(object)
    if object.type == ObjectTypeEnum.MESH and edm_props.SPECIAL_TYPE in ('UNKNOWN_TYPE'):
        return True
    return False

def is_shell(object: bpy.types.Object) -> bool:
    edm_props = get_edm_props(object)
    if object.type in (ObjectTypeEnum.MESH, ObjectTypeEnum.SURFACE) and edm_props.SPECIAL_TYPE in ('COLLISION_SHELL'):
        return True
    return False

# Parses blender scene and builds wrapper tree to bypass it to collect meshes, materials, etc
# to build edm file.
# We have to build wrapper tree as we add lod nodes and visibility info.
class CollectionWalker:
    def __init__(self, context: bpy.types.Context, model: pyedm.Model) -> None: 
        self.profile = cProfile.Profile()
        self.context: bpy.types.Context = context
        self.model: pyedm.Model = model
        self.material_cache = MaterialCache()
        self.obj_tree = ObjectNodeTree(context)
        self.obj_tree.build()

        # Dict of all bones. Each bone has 'BoneNode' type.
        # Bone have list of children, and every children has reference to parent. 
        # This architecture will lead to cycle-dependancies,
        # that is why it is needed to call 'def destroy(self)' method after model has exported.
        self.bones = {} 

        self.skins = []
    
    def destroy(self):
        for key in self.bones:
            self.bones[key].destroy()
        del self.bones

        self.obj_tree.destroy()        
        del self.skins

    # Walks through children of obj.
    def enum_children(self, full_name, obj, node, current_armature, skin_box = None):
        if skin_box and len(obj.children) > 1:
            log.fatal(f'SKIN_BOX can not have more then one child, but {full_name} has {len(obj.children)} children.')
            return None

        for o in obj.children:
            self.enum_object(full_name, o, node, current_armature, skin_box)

    def export_aabb(self, object: bpy.types.Object):
        aa_bb = get_aa_bb(object)

        edm_props = get_edm_props(object)

        if edm_props.SPECIAL_TYPE == 'USER_BOX':
            self.model.setUserBox(aa_bb)
        elif edm_props.SPECIAL_TYPE == 'BOUNDING_BOX':
            self.model.setBBox(aa_bb)
        elif edm_props.SPECIAL_TYPE == 'LIGHT_BOX':
            self.model.setLightBox(aa_bb)
        
    def export_mesh(self, obj: bpy.types.Object, control_node: pyedm.Node, armature: bpy.types.Armature):
        mesh_storages = buld_mesh(obj, armature)
        nTriangles = 0
        edm_render_node = None

        edm_props = get_edm_props(obj)

        for mesh_storage in mesh_storages:
            material_wrap = self.material_cache.get(obj.material_slots[mesh_storage.material_index].material) if obj.material_slots else None
            if not material_wrap or not material_wrap.is_valid():
                log.warning(f"{obj.name} has no material.")
                continue

            nTriangles += mesh_storage.nTriangles

            mat_fx: Materials = get_material(material_wrap.node_group_type)
            if mat_fx:
                if material_wrap.node_group_type == NodeGroupTypeEnum.DEFAULT:
                    utils.print_parents(obj)
                    edm_render_node = mat_fx.build_blocks(obj, material_wrap, mesh_storage)
                    if not edm_render_node.hasBlock(BlockEnum.BT_Bone):
                        edm_render_node.setControlNode(control_node)
                        err = self.model.addRenderNode(edm_render_node)
                        if err:
                            log.error(err)
                    else:
                        edm_bone = pyedm.Bone('Fake Control Bone ' + control_node.getName(), obj.matrix_local)
                        edm_bone.setInvertedBaseBoneMatrix(IDENTITY_MATRIX)
                        control_node = control_node.addChild(edm_bone)
                        edm_render_node.setControlNode(control_node)
                        self.skins.append(edm_render_node)
                else:
                    edm_render_node = mat_fx.build_blocks(obj, material_wrap, mesh_storage, edm_props)
                    #edm_render_node.setControlNode(fake_control_node)
                    edm_render_node.setControlNode(control_node)
                    err = self.model.addRenderNode(edm_render_node)
                    if err:
                        log.error(err)


        return (nTriangles, control_node, edm_render_node)
    
    def export_fake_light(self, obj: bpy.types.Object, control_node: pyedm.Node):
        bpy_mesh: bpy.types.Mesh = obj.data
        nLights = len(bpy_mesh.vertices)
        material_wrap = self.material_cache.get(obj.material_slots[0].material) if obj.material_slots else None
        if not material_wrap or not material_wrap.is_valid():
            log.fatal(f"{obj.name} has no material.")
        
        mat_fx: Materials = get_material(material_wrap.node_group_type)
        if mat_fx:
            edm_render_node = mat_fx.build_blocks(obj, material_wrap, None)
            edm_render_node.setControlNode(control_node)
            err = self.model.addRenderNode(edm_render_node)
            if err:
                log.error(err)

        return (nLights, control_node)
    
    def export_shell(self, obj: bpy.types.Object, control_node: pyedm.Node):
        mesh_storages = buld_mesh(obj, None)
        nTriangles = 0
        for mesh_storage in mesh_storages:
            nTriangles += mesh_storage.nTriangles
            
            edm_shell_node = pyedm.ShellNode(obj.name)
            edm_shell_node.setIndices(mesh_storage.indices)
            edm_shell_node.setPositions(mesh_storage.positions)
            edm_shell_node.setControlNode(control_node)
            self.model.addShellNode(edm_shell_node)

        return (nTriangles, control_node)

    def enum_object(self, parent_object_path: str, obj: ObjectNodeCustomType, edm_parent_node: pyedm.Node, current_armature: bpy.types.Armature, skin_box):
        logger.LOG_CTX.obj = obj
        try:
            full_name = os.path.join(parent_object_path, obj.name)
            edm_node = None
            if type(obj) is DummyNode:
                edm_node = edm_parent_node.addChild(pyedm.Node(obj.name))
            elif type(obj) is SceneRootNode:
                edm_node = edm_parent_node.addChild(pyedm.Node(obj.name))
            elif type(obj) is LodRoot:
                levels = [x.dist for x in obj.children]
                edm_node = edm_parent_node.addChild(pyedm.Lod(obj.name, levels))
            elif type(obj) is LodLeaf:
                edm_node = edm_parent_node.addChild(pyedm.Node(obj.name))
            if edm_node:
                self.enum_children(full_name, obj, edm_node, current_armature)
                return

            if not obj.visible:
                self.enum_children(full_name, obj, edm_parent_node, current_armature)
                return

            o: bpy.types.Object = obj.obj

            dev_mode = get_dev_mode_props(self.context.scene)
            arg_panel_props = get_arg_panel_props(self.context.scene)
            allowed_args = None
            if dev_mode.EXPORT_CUR_ARG_ONLY and arg_panel_props.CURRENT_ARG >= 0:
                allowed_args = [get_arg_panel_props(self.context.scene).CURRENT_ARG]

            edm_node = extract_visibility_animation(edm_parent_node, o, allowed_args)        
            edm_node = anim.extract_transform_animation(edm_node, o, allowed_args)
            
            if o.parent_bone and current_armature:
                pbone = o.parent_bone
                bone_name = build_bone_id(current_armature.name, pbone)
                if bone_name in self.bones:
                    bn = self.bones[bone_name]
                    tn = pyedm.Transform(f'End Of {bn.name}', Matrix.LocRotScale((0, bn.bone.length ,0), None, None))
                    ebn = bn.edm_node.addChild(tn)
                    edm_node = ebn.addChild(edm_node)
                    log.debug(f'{o.parent_bone} --> {o.name}')
            
            sb = skin_box
            edm_props = get_edm_props(o)
            if is_light(o):
                l = export_light(o, edm_node)
                if l:
                    self.model.addLight(l)
                    log.info(f"{full_name} as {l}")
            elif is_aa_bb(o):
                self.export_aabb(o)
                log.info(f"{full_name} as {o.type} {edm_props.SPECIAL_TYPE}")
            elif edm_props.SPECIAL_TYPE == 'SKIN_BOX':
                sb = get_aa_bb(o)
                log.info(f"{full_name} as {o.type} {edm_props.SPECIAL_TYPE}")
            elif is_connector(o):
                c = export_connector(o, edm_node)
                if c:
                    self.model.addConnector(c)
                    log.info(f"{full_name} as {o.type} {edm_props.SPECIAL_TYPE}")
            elif is_fake_light(o):  
                nLights, edm_node = self.export_fake_light(o, edm_node)
                log.info(f"{full_name} as {o.type}. Control node: {edm_node.getName()}. N triangles: {nLights}.")
            elif is_mesh(o):
                nTriangles, edm_node, edm_render_node = self.export_mesh(o, edm_node, current_armature)
                if edm_render_node and isinstance(edm_render_node, pyedm.PBRNode):
                    boneBlock = edm_render_node.getBlock(BlockEnum.BT_Bone)
                    if sb and boneBlock:
                        boneBlock.setSkinBox(sb)
                        sb = None
                log.info(f"{full_name} as {o.type}. Control node: {edm_node.getName()}. N triangles: {nTriangles}.")
            elif is_shell(o):
                if get_armature_from_modifiers(o.modifiers):
                    log.fatal(f"Shell {obj.name} has bones.") # why?
                nTriangles, edm_node = self.export_shell(o, edm_node)
                log.info(f"{full_name} as {o.type} {nTriangles}")
            elif is_segment(o):
                segments_node = create_segments_node(o, obj.name, edm_node)
                self.model.addSegmentsNode(segments_node)
            elif o.type == ObjectTypeEnum.ARMATURE:
                current_armature = o
                edm_node = export_armature(o, edm_node, self.bones)
                log.info(f"{full_name} as {o.type}")
            else:
                log.info(f"{full_name} as {o.type}")
            self.enum_children(full_name, obj, edm_node, current_armature, sb)

        except EdmException as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            res = ''.join(traceback.format_tb(exc_traceback, limit=1))
            res += ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback, limit=2))
            log.error(str(e), res)
            
    def build_skin(self):
        for skin in self.skins:
            bb = skin.getBlock(BlockEnum.BT_Bone)
            bnames = bb.getBoneNames()
            bone_objs = []

            for b in bnames:
                # As name of bone in skin isn't real it's name of vertex group.
                if b in self.bones:
                    bone_objs.append(self.bones[b].edm_node)
                else:
                    log.fatal(f"Bone '{b}' doesn't exist, please remove vertex group with the same name.")
            bb.setBones(bone_objs)

            err = self.model.addRenderNode(skin)
            if err:
                log.error(f"Can't export skin node {skin.getName()}. Reason: {err}")

    def do(self) -> None:
        self.profile.enable()
        root = pyedm.Transform('', ROOT_TRANSFORM_MATRIX)
        self.model.getRootTransform().addChild(root)
        self.enum_object('', self.obj_tree.obj_tree, root, None, None)
        self.build_skin()
        self.profile.disable()

    def log_status(self) -> None:
        pass
        #ios = io.StringIO()
        #ps = pstats.Stats(self.profile, stream = ios).sort_stats(pstats.SortKey.CUMULATIVE)
        #ps.print_stats()
        #print(ios.getvalue())

def _write(context: bpy.types.Context, edm_file_path: str) -> bool:

    logger.LOG_CTX = LogCtx()

    model = pyedm.Model()
    try:
        walker = CollectionWalker(context, model)
        walker.do()
        walker.log_status()

        if not log.errors:
            result_str: str = model.save(edm_file_path, 10)
            if result_str:
                log.fatal(f"Can't save model {edm_file_path}. Reason: {result_str}")
    except Exception as e:
        logger.LOG_CTX = None
        raise e
    finally:
        walker.destroy()
        del model
        del walker
        
        nAlived = pyedm.get_num_alived_objects()
        if nAlived:
            log.warning(f"{nAlived} objects are still alive.")
    
    logger.LOG_CTX = None