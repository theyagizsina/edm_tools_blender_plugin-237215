from bpy.types import PropertyGroup, Object
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, FloatVectorProperty, FloatProperty

class EDM_PropsEnumValues(PropertyGroup):
    bl_idname = "edm.PropsEnumValues"

    mat_name_prop: StringProperty(name="new_mat_prop_name", default="New Material")
    socket_name_prop: StringProperty(name="new_socket_prop_name", default="New Socket")
    enum_name_prop: StringProperty(name="new_enum_prop_name", default="New Enumeration Item")

class EDMPropsGroup(PropertyGroup):
    bl_idname = "edm.EDMPropsGroup"

    SPECIAL_TYPE : EnumProperty(
        name = "obj.type",
        description = "Choose the type of analysis this material do",
        items = [
            ('UNKNOWN_TYPE',            'unknown_type',             "Unspecified object type: geometry/animation empty",                    0),
            ('USER_BOX',                'user_box',                 "Box covering only geometry. Is used for backlight",                    1),
            ('BOUNDING_BOX',            'bounding_box',             "Box covering geometry and all animations. Is used for camera cutoff",  2),
            ('COLLISION_LINE',          'collision_line',           "Geometry edge used for collision",                                     3),
            ('COLLISION_SHELL',         'collision_shell',          "Geometry mesh used for collision",                                     4),
            ('CONNECTOR',               'connector',                "Type Connector",                                                       5),
            ('FAKE_LIGHT',              'fake_light',               "Type BANO",                                                            6),
            ('LIGHT_BOX',               'light_box',                "Box - Limiter for light source",                                       7),
            ('NUMBER_TYPE',             'number_type',              "Dynamic digits for bort number",                                       8),
            ('SKIN_BOX',                'skin_box',                 "Box covering bones geometry",                                          9)

        ],
        default = 'UNKNOWN_TYPE'
    ) # type: ignore

    TWO_SIDED : BoolProperty(
        name = "two sided object",
        default = False
    )
    
    SURFACE_MODE : BoolProperty(
        name = "surface mode",
        default = False
    )

    DAMAGE_ARG : IntProperty(
        name = 'Damage arg',
        min = -1,
        default = -1
    )

    LUMINANCE_ARG : IntProperty(
        name = 'Luminance arg',
        min = -1,
        default = -1
    )

    COLOR_ARG : IntProperty(
        name = 'Base color arg',
        min = -1,
        default = -1
    )

    EMISSIVE_ARG : IntProperty(
        name = 'Emissive value arg',
        min = -1,
        default = -1
    )

    EMISSIVE_COLOR_ARG : IntProperty(
        name = 'Emissive color arg',
        min = -1,
        default = -1
    )

    UV_LB : FloatVectorProperty(
        name = 'tex_coords_lb',
        precision = 2,
        size = 2,
        default = [0.0, 0.0],
        subtype = 'COORDINATES'
    )

    UV_RT : FloatVectorProperty(
        name = 'tex_coords_rt',
        precision = 2,
        size = 2,
        default = [1.0, 1.0],
        subtype = 'COORDINATES'
    )

    SIZE : FloatProperty(
        name = "size",
        default = 3.0,
        min = 0.0
    )

    UV_LB_BACK : FloatVectorProperty(
        name = 'tex_coords_lb_back',
        precision = 2,
        size = 2,
        default = [0.0, 0.0]
    )

    UV_RT_BACK : FloatVectorProperty(
        name = 'tex_coords_rt_back',
        precision = 2,
        size = 2,
        default = [1.0, 1.0]
    )

    ANIMATED_BRIGHTNESS : FloatProperty(
        name = "object luminance",
        default = 1.0,
        min = 0.0,
        options = {'ANIMATABLE'}
    )

    LIGHT_SOFTNESS : FloatProperty(
        name = "light softness",
        default = 0.0,
        min = 0.0,
        options = {'ANIMATABLE'}
    )

    LIGHT_SOFTNESS_ARG : IntProperty(
        name = 'light softness arg',
        min = -1,
        default = -1
    )

    NUMBER_CONTROLS : StringProperty(
        name = "controls",
        default = ""
    )

    CONNECTOR_EXT : StringProperty(
        name="connector ext",
        default = ""
    )

    LIGHT_COLOR_ARG : IntProperty(
        name = 'color',
        min = -1,
        default = -1
    )

    LIGHT_POWER_ARG : IntProperty(
        name = 'power',
        min = -1,
        default = -1
    )

    LIGHT_PHY_ARG : IntProperty(
        name = 'size',
        min = -1,
        default = -1
    )

    LIGHT_THETA_ARG : IntProperty(
        name = 'blend',
        min = -1,
        default = -1
    )

    LIGHT_DISTANCE_ARG : IntProperty(
        name = 'distance',
        min = -1,
        default = -1
    )

    LIGHT_SPECULAR_ARG : IntProperty(
        name = 'specular',
        min = -1,
        default = -1
    )

    OPACITY_VALUE_ARG : IntProperty(
        name = 'Opacity value arg',
        min = -1,
        default = -1
    )

def get_edm_props(o: Object) -> EDMPropsGroup:
    return o.EDMProps

def get_objects_custom_props_classes():
    return [
        EDM_PropsEnumValues,
        EDMPropsGroup,
    ]