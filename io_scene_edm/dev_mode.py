from bpy.types import PropertyGroup, Scene
from bpy.props import BoolProperty

from pyedm_platform_selector import pyedm

class EDMDevModePropsGroupDummy:
    def __init__(self) -> None:
        self.EXPORT_CUR_ARG_ONLY = False

class EDMDevModePropsGroup(PropertyGroup):
    bl_idname = "edm.EDMDevModePropsGroup"
    EXPORT_CUR_ARG_ONLY : BoolProperty(
        name = "Export only one arg",
        default = False,
		options = {'SKIP_SAVE'},
    )

def get_dev_mode_classes():
    if pyedm.dev_mode():
        return [EDMDevModePropsGroup]
    return []
    
def get_dev_mode_props(o: Scene)->EDMDevModePropsGroup:
    if pyedm.dev_mode():
        return o.EDMDevModeProps    
    return EDMDevModePropsGroupDummy()