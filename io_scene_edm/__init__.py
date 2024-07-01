import sys
import bpy
import os
import traceback

from typing import List, Dict, Tuple, Set

sys.path.append(bpy.utils.user_resource(resource_type='SCRIPTS', path="addons") + '\\' + __name__)

from pyedm_platform_selector import pyedm, native_bindings

from bpy.types import Operator, Panel, Context, AddonPreferences, Object, UILayout, Light
from bpy.props import StringProperty, BoolProperty, PointerProperty
from bpy_extras.io_utils import ExportHelper

from pathlib import Path
import shlex
import subprocess

from . import collection_walker
from objects_custom_props import get_edm_props, EDM_PropsEnumValues, EDMPropsGroup
from custom_sockets import get_custom_sockets_classes
from . import custom_shader_group as custom_sg

from objects_custom_props import get_objects_custom_props_classes

from edm_exception import EdmFatalException
from logger import log
from enums import ObjectTypeEnum, EDMPropsSpecialTypeStr, LampTypeEnum, NodeGroupTypeEnum
from edm_materials import get_material_classes, NODE_MT_EDM_Menu_add, NODE_MT_EDM_Dev_Menu_add
from arg_panel import get_arg_panel_classes, EDM_PT_set_argument, EDM_PT_mute_animations, EDM_PT_unmute_animations, EDM_PT_reset, EDMArgPropsGroup, get_arg_panel_props
from material_tools import get_material_tool_classes, EDM_PT_import_materials, EDM_PT_export_materials, check_materials_validity
from materials import check_if_referenced_file, build_material_descriptions
from serializer_tools import MatDesc
from dev_mode import get_dev_mode_classes, EDMDevModePropsGroup, get_dev_mode_props
from export_connectors import ConnectorChildPanel
from export_fake_lights import FakeLightChildPanel
from export_lights import LightChildPanel

from . import utils

# Unfortunately, parser of bl_info doesn't support variables as values.
bl_info = {
    'name': 'EDM 10.0 format', # 'EDM 10.0 format'
    'author': 'Eagle Dynamics (c) 2024',
    "version": (1, 0, 0),
    'blender': (3, 5, 0),
    'location': 'File > Export / Shader Editor > Add > EDM',
    'description': 'Export as EDM and compatible shading materials',
    'warning': '',
    'doc_url': "",
    'support': 'OFFICIAL',
    'category': 'Export',
}

def get_version_string():
    return str(bl_info['version'][0]) + '.' + str(bl_info['version'][1]) + '.' + str(bl_info['version'][2])

def has_scene(context):
    if not context.scene:
        return False

    return True

def get_all_objects_names() -> Set[str]:
    return {obj.name for obj in bpy.data.objects}

class EDMDataPanel(Panel):
    bl_label = "Object Properties"
    bl_idname = "OBJECT_PT_edm_data"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "EDM Export"

    @classmethod
    def poll(cls, context):
        if context.scene:
            return True
        
        if not context.object:
            return False
        
        return True
    
    def draw_scene_related(self, layout: UILayout, context: Context):
        if not has_scene(context):
            return

        row = layout.row()
        row.operator(EDM_PT_fast_export.bl_idname)

        layout.split()

        props = get_arg_panel_props(context.scene)

        row = layout.row()
        row.prop(props, "CURRENT_ARG")
        row.operator(EDM_PT_set_argument.bl_idname)
        row = layout.row()
        row.operator(EDM_PT_mute_animations.bl_idname)
        row.operator(EDM_PT_unmute_animations.bl_idname)
        row = layout.row()
        row.operator(EDM_PT_reset.bl_idname)

        layout.split()

        if not check_if_referenced_file(bpy.context.blend_data.filepath):
            row = layout.row()
            row.operator(EDM_PT_import_materials.bl_idname)
        else:
            row = layout.row()
            row.operator(EDM_PT_export_materials.bl_idname)

        layout.split()

        if pyedm.dev_mode():
            dev_props = get_dev_mode_props(context.scene)
            row = layout.row()
            row.prop(dev_props, "EXPORT_CUR_ARG_ONLY")

    def draw_object_related(self, layout: UILayout, context: Context):
        if not utils.has_object(context):
            return
        
        object: Object = context.object
        props = get_edm_props(object)

        row = layout.row()
        row.prop(object, "VISIBLE", event=True)

        if not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP):
            row = layout.row()
            row.prop(props, "SPECIAL_TYPE")

        return
        
    def draw(self, context):
        layout = self.layout

        self.draw_scene_related(layout, context)
        layout.split()
        self.draw_object_related(layout, context)

class UnknownChildPanel(bpy.types.Panel):
    bl_label = "Unknown type Properties"
    bl_idname = "OBJECT_PT_unknown_child_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "OBJECT_PT_edm_data"

    @classmethod
    def poll(cls, context):
        if not utils.has_object(context):
            return

        object: Object = context.object
        props = get_edm_props(object)

        result = props.SPECIAL_TYPE in (EDMPropsSpecialTypeStr.UNKNOWN_TYPE) and not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP)
        return result

    def draw(self, context):
        if not utils.has_object(context):
            return

        layout = self.layout
        object: Object = context.object
        props = get_edm_props(object)

        if object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP:
            box = layout.box()
            row = box.row()
            row.label(text='Light Arguments')

            row = box.row()
            row.prop(props, "LIGHT_COLOR_ARG")
            row.prop(props, "LIGHT_POWER_ARG")

            row = box.row()
            row.prop(props, "LIGHT_SPECULAR_ARG")
            row.prop(props, "LIGHT_DISTANCE_ARG")

            row = box.row()
            row.prop(props, "LIGHT_SOFTNESS_ARG")

            blender_lamp: Light = object.data
            if blender_lamp.type == LampTypeEnum.SPOT:
                row = box.row()
                row.prop(props, "LIGHT_PHY_ARG")
                row.prop(props, "LIGHT_THETA_ARG")

        else:
            row = layout.row()
            row.prop(props, "TWO_SIDED")

            row = layout.row()
            row.prop(props, "DAMAGE_ARG")

            row = layout.row()
            row.prop(props, "COLOR_ARG")

            row = layout.row()
            row.prop(props, "EMISSIVE_ARG")

            row = layout.row()
            row.prop(props, "EMISSIVE_COLOR_ARG")

            row = layout.row()
            row.prop(props, "OPACITY_VALUE_ARG")

class UserBoxChildPanel(bpy.types.Panel):
    bl_label = "UserBox type Properties"
    bl_idname = "OBJECT_PT_user_box_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "OBJECT_PT_edm_data"

    @classmethod
    def poll(cls, context):
        # don't show the panel, until there is data to display. We leave the class so we don’t have to write it again later
        return False
        if not utils.has_object(context):
            return

        object: Object = context.object
        props = get_edm_props(object)

        result = props.SPECIAL_TYPE in (EDMPropsSpecialTypeStr.USER_BOX) and not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP)
        return result

    def draw(self, context):
        if not utils.has_object(context):
            return

class BoundingBoxChildPanel(bpy.types.Panel):
    bl_label = "BoundingBox type Properties"
    bl_idname = "OBJECT_PT_bounding_box_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "OBJECT_PT_edm_data"

    @classmethod
    def poll(cls, context):
        # don't show the panel, until there is data to display. We leave the class so we don’t have to write it again later
        return False
        if not utils.has_object(context):
            return

        object: Object = context.object
        props = get_edm_props(object)

        result = props.SPECIAL_TYPE in (EDMPropsSpecialTypeStr.BOUNDING_BOX) and not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP)
        return result

    def draw(self, context):
        if not utils.has_object(context):
            return

        layout = self.layout
        object: Object = context.object
        props = get_edm_props(object)

class CollisionLineChildPanel(bpy.types.Panel):
    bl_label = "Collision line type Properties"
    bl_idname = "OBJECT_PT_collision_line_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "OBJECT_PT_edm_data"

    @classmethod
    def poll(cls, context):
        # don't show the panel, until there is data to display. We leave the class so we don’t have to write it again later
        return False
        if not utils.has_object(context):
            return

        object: Object = context.object
        props = get_edm_props(object)

        result = props.SPECIAL_TYPE in (EDMPropsSpecialTypeStr.COLLISION_LINE) and not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP)
        return result

    def draw(self, context):
        if not utils.has_object(context):
            return

        layout = self.layout
        object: Object = context.object
        props = get_edm_props(object)

class CollisionShellChildPanel(bpy.types.Panel):
    bl_label = "Collision shell type Properties"
    bl_idname = "OBJECT_PT_collision_shell_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "OBJECT_PT_edm_data"

    @classmethod
    def poll(cls, context):
        # don't show the panel, until there is data to display. We leave the class so we don’t have to write it again later
        return False
        if not utils.has_object(context):
            return

        object: Object = context.object
        props = get_edm_props(object)

        result = props.SPECIAL_TYPE in (EDMPropsSpecialTypeStr.COLLISION_SHELL) and not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP)
        return result

    def draw(self, context):
        if not utils.has_object(context):
            return

class LightBoxChildPanel(bpy.types.Panel):
    bl_label = "LightBox type Properties"
    bl_idname = "OBJECT_PT_lightbox_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "OBJECT_PT_edm_data"

    @classmethod
    def poll(cls, context):
        # don't show the panel, until there is data to display. We leave the class so we don’t have to write it again later
        return False
        if not utils.has_object(context):
            return

        object: Object = context.object
        props = get_edm_props(object)

        result = props.SPECIAL_TYPE in (EDMPropsSpecialTypeStr.LIGHT_BOX) and not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP)
        return result

    def draw(self, context):
        if not utils.has_object(context):
            return

        layout = self.layout
        object: Object = context.object
        props = get_edm_props(object)

class NumberTypeChildPanel(bpy.types.Panel):
    bl_label = "Number type Properties"
    bl_idname = "OBJECT_PT_number_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "OBJECT_PT_edm_data"

    @classmethod
    def poll(cls, context):
        if not utils.has_object(context):
            return

        object: Object = context.object
        props = get_edm_props(object)

        result = props.SPECIAL_TYPE in (EDMPropsSpecialTypeStr.NUMBER_TYPE) and not(object.type == ObjectTypeEnum.LIGHT or object.type == ObjectTypeEnum.LAMP)
        return result

    def draw(self, context):
        if not utils.has_object(context):
            return

        layout = self.layout
        object: Object = context.object
        props = get_edm_props(object)

        box = layout.box()
        row = box.row()
        row.prop(props, "NUMBER_CONTROLS")


def add_node_button(self, context):
    self.layout.menu(NODE_MT_EDM_Menu_add.__name__, text = "EDM Materials")
    is_dev_env: bool = utils.get_is_dev_env()
    is_reference_file: bool = check_if_referenced_file(bpy.context.blend_data.filepath)
    if is_dev_env or is_reference_file:
        self.layout.menu(NODE_MT_EDM_Dev_Menu_add.__name__, text = "Dev EDM Materials")

class EDMAddonParams(AddonPreferences):
    bl_idname = __name__

    working_dir: StringProperty(
        name="Working directory",
        subtype='DIR_PATH',
    )

    run_viewer_flag: BoolProperty(
        name = "Run viewer after model export",
        default = False,
    )

    executable_path: StringProperty(
        name="Executable path",
        subtype='FILE_PATH',
        default='H:\\lockon\\LockOnExe\\bin\\x86_64\\vc143.debug-ad-mt\\ModelViewer2.exe'
    )

    arguments: StringProperty(
        name="Arguments",
        default="--reload --single s $FILE$"
    )
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="This is a preferences view for our add-on")
        layout.prop(self, "run_viewer_flag")
        layout.prop(self, "working_dir")
        layout.prop(self, "arguments")
        layout.prop(self, "executable_path")

def run_edm_export(file_path: str, context: Context, operator: Operator, run_model_viewer: bool = True):
    abs_file_path: str = os.path.abspath(file_path)    
    try:
        if not native_bindings:
            raise EdmFatalException(f"\nError: couldn't proceed edm export because it's python dummy plugin, not native.")
                
        if not check_if_referenced_file(bpy.context.blend_data.filepath):
            check_materials_validity()
        collection_walker._write(context, abs_file_path)

        for i in log.warnings:
            operator.report({"WARNING"}, i)

        if log.errors:
            for i in log.errors:
                operator.report({"ERROR"}, i)
            log.errors = []
            return {'CANCELLED'}
            
        operator.report({"INFO"}, f'Model successfully exported to {abs_file_path}.')
    except EdmFatalException as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        res = ''.join(traceback.format_tb(exc_traceback, limit=1))
        res += ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback, limit=2))
        log.error(str(e))
        log.errors = []
        operator.report({"ERROR"}, str(e))
        return {'CANCELLED'}

    my_addon_params: EDMAddonParams = context.preferences.addons[__name__].preferences
    run_viewer_flag: bool = my_addon_params and my_addon_params.run_viewer_flag and run_model_viewer
    if run_viewer_flag:
        args = shlex.split(my_addon_params.arguments)
        args.insert(0, my_addon_params.executable_path)
        if '$FILE$' in args:
            i = args.index('$FILE$')
            args[i] = file_path
        DETACHED_PROCESS = 0x00000008
        try:
            subprocess.Popen(args, close_fds = True, creationflags = DETACHED_PROCESS)
        except:
            pass
    return {'FINISHED'}

class EDM_PT_export(Operator, ExportHelper):
    bl_idname = "edm.export"
    bl_label = "export to EDM"
    bl_description = "Export edm"
    filename_ext = ".edm"
    filter_glob: StringProperty (
        default = "*.edm",
        options = {'HIDDEN'},
        maxlen = 255
    )

    def execute(self, context):
        return run_edm_export(self.filepath, context, self)

class EDM_PT_fast_export(Operator):
    bl_idname = "edm.fast_export" 
    bl_label = "Fast EDM export"
    bl_description = "Fast export to edm"

    def execute(self, context):
        is_file_name_available: bool = len(bpy.data.filepath) > 0
        file_dir: str = os.path.dirname(bpy.data.filepath) if is_file_name_available else os.path.dirname(os.path.realpath(__file__))
        file_name = Path(bpy.data.filepath).stem if is_file_name_available else 'test'
        file_path: str = os.path.join(file_dir, file_name + '.edm')
        return run_edm_export(file_path, context, self)
    
class EDM_PT_fast_export_dummy(Operator):
    bl_idname = "edm.fast_export_dummy" 
    bl_label = "Fast EDM export dummy"
    bl_description = "Fast export to edm without calling ModelView.exe after"

    def execute(self, context):
        is_file_name_available: bool = len(bpy.data.filepath) > 0
        file_dir: str = os.path.dirname(bpy.data.filepath) if is_file_name_available else os.path.dirname(os.path.realpath(__file__))
        file_name = Path(bpy.data.filepath).stem if is_file_name_available else 'test'
        file_path: str = os.path.join(file_dir, file_name + '.edm')
        return run_edm_export(file_path, context, self, False)

def menu_func_export(self, context):
    self.layout.operator(EDM_PT_export.bl_idname, text="Eagle Dynamics Model (.edm)")


def collect_classes():
    classes = get_material_classes()
    classes += get_material_tool_classes()
    classes += get_arg_panel_classes()
    classes += get_custom_sockets_classes()
    classes += get_objects_custom_props_classes()
    classes += custom_sg.get_custom_shader_group_classes()
    classes += get_dev_mode_classes()
    classes += (
        EDMDataPanel,
        EDM_PT_fast_export,
        EDM_PT_fast_export_dummy,
        EDMAddonParams,
        LightChildPanel,
        UnknownChildPanel,
        UserBoxChildPanel,
        BoundingBoxChildPanel,
        CollisionLineChildPanel,
        CollisionShellChildPanel,
        ConnectorChildPanel,
        FakeLightChildPanel,
        LightBoxChildPanel,
        NumberTypeChildPanel,
        EDM_PT_export,
    )
    return classes


def visibility_get_func(self):
    if self.display_type == 'WIRE':
        return False
    return True

def visibility_set_func(self, val):
    if val == True:
        self.display_type = 'TEXTURED'
    else:
        self.display_type = 'WIRE'

def create_return_items(enum_name: str, mat_name: str, it: Dict[custom_sg.MaterialNameType, Dict[custom_sg.SocketNameType, List[Tuple[str, str, str, int]]]]):
    def retrive_items(self, context):
        return it[mat_name][enum_name]
    return retrive_items

def register():
    pyedm.init()

    material_desc: Dict[NodeGroupTypeEnum, MatDesc] = build_material_descriptions()
    items: Dict[custom_sg.MaterialNameType, Dict[custom_sg.SocketNameType, List[Tuple[str, str, str, int]]]] = custom_sg.get_enum_items(material_desc)
    names: Dict[custom_sg.MaterialNameType, Dict[str, str]] = custom_sg.get_enum_names(material_desc)
    names_enum: List[Tuple[custom_sg.SocketType, custom_sg.MaterialNameType, custom_sg.SocketNameType, int]] = custom_sg.get_enum_names_map(names)

    deffered_names_enum = bpy.props.EnumProperty (
        name        = 'enum_names',
        items       = names_enum
    )
    setattr(bpy.types.ShaderNodeCustomGroup, 'enum_names', deffered_names_enum)
    setattr(bpy.types.ShaderNodeGroup, 'enum_names', deffered_names_enum)

    for mat_name, enum_dict in items.items():
        for enum_name, enum_values in enum_dict.items():
            deffered_enum = bpy.props.EnumProperty (
                name        = enum_name,
                items       = create_return_items(enum_name, mat_name, items)
            )
            setattr(bpy.types.ShaderNodeCustomGroup, enum_name, deffered_enum)
            setattr(bpy.types.ShaderNodeGroup, enum_name, deffered_enum)


    classes = collect_classes()
    for cls in classes:
        utils.register_bpy_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.NODE_MT_add.append(add_node_button)
    
    bpy.types.Scene.EDMArgProps = PointerProperty(type = EDMArgPropsGroup)
    bpy.types.Object.EDMProps = PointerProperty(type = EDMPropsGroup)
    bpy.types.Scene.EDMEnumItems = PointerProperty(type = EDM_PropsEnumValues)
    
    if pyedm.dev_mode():
        bpy.types.Scene.EDMDevModeProps = PointerProperty(type = EDMDevModePropsGroup)
    
    # Have set this property directly into object as we need acces to parent object in callbacks.
    bpy.types.Object.VISIBLE = BoolProperty(
        name = "visibility",
        default = True,
        set = visibility_set_func,
        get = visibility_get_func,
    )

    print("EDM Addon was registered")

def unregister():
    pyedm.deinit()

    del bpy.types.Scene.EDMArgProps
    del bpy.types.Object.EDMProps
    del bpy.types.Scene.EDMEnumItems
    if pyedm.dev_mode():
        del bpy.types.Scene.EDMDevModeProps

    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.NODE_MT_add.remove(add_node_button)

    classes = collect_classes()
    for cls in reversed(classes):
        utils.unregister_bpy_class(cls)

    print("EDM Addon was unregistered")

if __name__ == "__main__":
    register()
