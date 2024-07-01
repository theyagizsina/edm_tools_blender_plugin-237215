import bpy

from version_specific import InterfaceNodeSocket
from bpy.types import NodeSocket, PropertyGroup

ShadowCasterEnumItems = (
    ('SHADOW_CASTER_YES',   "YES",          "Cast Shadows",         0),
    ('SHADOW_CASTER_NO',    "NO",           "Don't cast shadows",   1),
    ('SHADOW_CASTER_ONLY',  "ONLY_SHADOW",  "Cast shadows only",    2)
)

class EdmShadowCasterSocket(NodeSocket):
    bl_idname = "EdmSocketShadowCasterType"
    bl_label = "EDM NodeShadow Caster Socket"

    def update_value(self, context):
        return None

    default_value: bpy.props.EnumProperty (
        name        = 'Shadow Caster',
        description = "Does mesh cast shadow",
        items       = ShadowCasterEnumItems,
        update      = update_value
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 0.5)
    
class EdmShadowCasterSocketInterface(InterfaceNodeSocket):
    bl_idname = "EdmShadowCasterSocketInterface"
    bl_socket_idname = 'EdmSocketShadowCasterType'
    bl_label = "ShadowCasterSocket"

    default_value: bpy.props.EnumProperty (
        name        = 'Shadow Caster',
        description = "Default value for shadow caster",
        items       = ShadowCasterEnumItems,
        default     = 'SHADOW_CASTER_YES'
    )

    def draw(self, context, layout):
        layout.prop(self, "default_value")

    def init_socket(self, node, socket, data_path):
        socket.default_value = self.default_value

    def from_socket(self, node, socket):
        self.default_value = socket.default_value

    def draw_color(self, context):
        return (1.0, 0.8, 0.4, 1.0)

class EdmBidirectionalCasterSocket(NodeSocket):
    bl_idname = "EdmSocketBidirectionalType"
    bl_label = "EDM Bidirectional Caster Socket"
    
    def update_value(self, context):
        return None
    
    default_value: bpy.props.BoolProperty(
        name    = 'Bidirectional',
        default = True,
        update  = update_value
    )
    
    def draw(self, context, layout, node, text):
        layout.prop(self, "default_value")

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 0.5)
    
class EdmBidirectionalCasterSocketInterface(InterfaceNodeSocket):
    bl_idname = "EdmBidirectionalCasterSocketInterface"
    bl_socket_idname = 'EdmSocketBidirectionalType'
    bl_label = "BidirectionalCasterSocket"

    def draw(self, context, layout):
        pass

    def draw_color(self, context):
        return (1.0, 0.8, 0.4, 1.0)
    
TransparencyEnumItems = (
    ('OPAQUE',              "Opaque",                       "", 0),
    ('ALPHA_BLENDING',      "Alpha Blending",               "", 1),
    ('Z_TEST',              "Alpha test",                   "", 2),
    ('SUM_BLENDING',        "Sum Blending",                 "", 3),
    ('SUM_BLENDING_SI',     "Additive Self Illumination",   "", 4),
    ('SHADOWED_BLENDING',   "Shadowed Blending",            "", 6)
)

class EdmTransparencySocket(NodeSocket):
    bl_idname = 'EdmTransparencySocketType'
    bl_label = "EDM Node Transparency Socket"
    
    def update_value(self, context):             
        return None
    
    default_value: bpy.props.EnumProperty(
        name        = 'Transparency',
        description = "Transparency/blending mode",
        items       = TransparencyEnumItems,
        update      = update_value
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 0.5)
    
class EdmTransparencySocketInterface(InterfaceNodeSocket):
    bl_idname = "EdmTransparencySocketInterface"
    bl_socket_idname = 'EdmTransparencySocketType'
    bl_label = "TransparencySocket"

    default_value: bpy.props.EnumProperty(
        name    = 'Transparency',
        description = "Default value for transparency/blending mode",
        items   = TransparencyEnumItems,
        default = 'OPAQUE'
    )

    def init_socket(self, node, socket, data_path):
        socket.default_value = self.default_value

    def from_socket(self, node, socket):
        self.default_value = socket.default_value

    def draw_color(self, context):
        return (1.0, 0.8, 0.4, 1.0)
    
DeckTransparencyEnumItems = (
    ('OPAQUE',          "Opaque",           "", 0),
    ('ALPHA_BLENDING',  "Alpha Blending",   "", 1),
    ('Z_TEST',          "Alpha test",       "", 2)
)

class EdmDeckTransparencySocket(NodeSocket):
    bl_idname = 'EdmDeckTransparencySocketType'
    bl_label = "EDM Node Deck Transparency Socket"
    
    def update_value(self, context):             
        return None
    
    default_value: bpy.props.EnumProperty(
        name        = 'Transparency',
        description = "Transparency/blending mode",
        items       = DeckTransparencyEnumItems,
        update      = update_value
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 0.5)

class EdmDeckTransparencySocketInterface(InterfaceNodeSocket):
    bl_idname = "EdmDeckTransparencySocketInterface"
    bl_socket_idname = 'EdmDeckTransparencySocketType'
    bl_label = "DeckTransparencySocket"

    default_value: bpy.props.EnumProperty(
        name    = 'Transparency',
        description = "Default value for transparency/blending mode",
        items   = DeckTransparencyEnumItems,
        default = 'OPAQUE'
    )

    def init_socket(self, node, socket, data_path):
        socket.default_value = self.default_value

    def from_socket(self, node, socket):
        self.default_value = socket.default_value

    def draw_color(self, context):
        return (1.0, 0.8, 0.4, 1.0)
    
EmissionEnumItems = (
    ('NONE',                            "None",                             "", 0),
    ('DEFAULT',                         "Default Illumination",             "", 1),
    ('SELF_ILLUMINATION',               "Self Illumination",                "", 2),
    ('TRANSPARENT_SELF_ILLUMINATION',   "Transparent Self Illumination",    "", 3),
    ('ADDITIVE_SELF_ILLUMINATION',      "Additive Self Illumination",       "", 4)
)

class EdmEmissionTypeSocket(NodeSocket):
    bl_idname = 'EdmEmissionTypeSocketType'
    bl_label = "EDM Node Emission Type Socket"
    
    def update_value(self, context):             
        return None
    
    default_value: bpy.props.EnumProperty(
        name        = 'Self Illumination Type',
        description = "Illumination type",
        items       = EmissionEnumItems,
        update      = update_value
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 0.5)
    
class EdmEmissionTypeSocketInterface(InterfaceNodeSocket):
    bl_idname = "EdmEmissionTypeSocketInterface"
    bl_socket_idname = 'EdmEmissionTypeSocketType'
    bl_label = "EmissionTypeSocket"

    default_value: bpy.props.EnumProperty(
        name        = 'Self Illumination Type',
        description = "Default value for emission type",
        items       = EmissionEnumItems,
        default     = 'NONE'
    )

    def init_socket(self, node, socket, data_path):
        socket.default_value = self.default_value

    def from_socket(self, node, socket):
        self.default_value = socket.default_value

    def draw_color(self, context):
        return (1.0, 0.8, 0.4, 1.0)
    
class EDMPropsMaterial(PropertyGroup):
    bl_idname = "edm.EDMPropsShadowCaster"

    shadow_caster_value: bpy.props.EnumProperty (
        name        = 'Shadow Caster',
        description = "Does mesh cast shadow",
        items       = ShadowCasterEnumItems
    )

    is_shadow_caster_active: bpy.props.BoolProperty (
        default     = False
    )

    transparency_value: bpy.props.EnumProperty(
        name        = 'Transparency',
        description = "Transparency/blending mode",
        items       = TransparencyEnumItems
    )

    is_transparency_active: bpy.props.BoolProperty (
        default     = False
    )

    deck_transparency_value: bpy.props.EnumProperty(
        name        = 'Transparency',
        description = "Transparency/blending mode",
        items       = DeckTransparencyEnumItems
    )

    is_deck_transparency_active: bpy.props.BoolProperty (
        default     = False
    )

    emission_value: bpy.props.EnumProperty(
        name        = 'Self Illumination Type',
        description = "Illumination type",
        items       = EmissionEnumItems
    )

    is_emission_active: bpy.props.BoolProperty (
        default     = False
    )

def get_custom_sockets_classes():
    return [
        EdmShadowCasterSocket,
        EdmShadowCasterSocketInterface,
        EdmBidirectionalCasterSocket,
        EdmBidirectionalCasterSocketInterface,
        EdmTransparencySocket,
        EdmDeckTransparencySocket,
        EdmTransparencySocketInterface,
        EdmDeckTransparencySocketInterface,
        EDMPropsMaterial,
    ]