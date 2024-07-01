from enum import Enum

class ObjectTypeEnum(str, Enum):
    MESH            = 'MESH'
    CURVE           = 'CURVE'
    SURFACE         = 'SURFACE'
    METABALL        = 'META'
    CURVES          = 'CURVES'
    POINTCLOUD      = 'POINTCLOUD'
    VOLUME          = 'VOLUME'
    GREASEPENCIL    = 'GPENCIL'
    ARMATURE        = 'ARMATURE'
    LATTICE         = 'LATTICE'
    EMPTY           = 'EMPTY'
    LIGHT           = 'LIGHT'
    LAMP            = 'LAMP'
    LIGHT_PROBE     = 'LIGHT_PROBE'
    CAMERA          = 'CAMERA'
    SPEAKER         = 'SPEAKER'

class LampTypeEnum(str, Enum):
    POINT           = 'POINT'
    SUN             = 'SUN'
    SPOT            = 'SPOT'

class EdmTransparencySocketItemsStr(str, Enum):
    OPAQUE              = 'Opaque'
    ALPHA_BLENDING      = 'Alpha Blending'
    Z_TEST              = 'Z-Test'
    SUM_BLENDING        = 'Sum Blending'
    SUM_BLENDING_SI     = 'Additive Self Illumination'
    SHADOWED_BLENDING   = 'Shadowed Blending'

class EdmTransparencySocketItemsEnum(str, Enum):
    OPAQUE              = 'OPAQUE'
    ALPHA_BLENDING      = 'ALPHA_BLENDING'
    Z_TEST              = 'Z_TEST'
    SUM_BLENDING        = 'SUM_BLENDING'
    SUM_BLENDING_SI     = 'SUM_BLENDING_SI'
    SHADOWED_BLENDING   = 'SHADOWED_BLENDING'

class EdmTransparencySocketItemsInt(int, Enum):
    OPAQUE              = 0
    ALPHA_BLENDING      = 1
    Z_TEST              = 2
    SUM_BLENDING        = 3
    SUM_BLENDING_SI     = 4
    SHADOWED_BLENDING   = 6

class EdmTwoSidedSocketItemsStr(str, Enum):
    TWO_SIDED_NO    = 'TWO_SIDED_NO'
    TWO_SIDED_YES   = 'TWO_SIDED_YES'

class EdmTwoSidedSocketItemsInt(int, Enum):
    TWO_SIDED_NO    = 0
    TWO_SIDED_YES   = 1

class EdmShadowCasterSocketItemsStr(str, Enum):
    SHADOW_CASTER_YES   = 'SHADOW_CASTER_YES'
    SHADOW_CASTER_NO    = 'SHADOW_CASTER_NO'
    SHADOW_CASTER_ONLY  = 'SHADOW_CASTER_ONLY'

class EdmShadowCasterSocketItemsInt(int, Enum):
    SHADOW_CASTER_YES   = 0
    SHADOW_CASTER_NO    = 1
    SHADOW_CASTER_ONLY  = 2

class EDMPropsSpecialTypeStr(str, Enum):
    UNKNOWN_TYPE        = 'UNKNOWN_TYPE'
    USER_BOX            = 'USER_BOX'
    BOUNDING_BOX        = 'BOUNDING_BOX'
    COLLISION_LINE      = 'COLLISION_LINE'
    COLLISION_SHELL     = 'COLLISION_SHELL'
    CONNECTOR           = 'CONNECTOR'
    FAKE_LIGHT          = 'FAKE_LIGHT'
    LIGHT_BOX           = 'LIGHT_BOX'
    NUMBER_TYPE         = 'NUMBER_TYPE'
    SKIN_BOX            = 'SKIN_BOX'

class EDMCustomEmissiveTypeInt(int, Enum):
    NONE                                = 0
    DEFAULT                             = 1
    SELF_ILLUMINATION                   = 2
    TRANSPARENT_SELF_ILLUMINATION       = 3
    ADDITIVE_SELF_ILLUMINATION          = 4
    ADDITIVE_SELF_COLOR_ILLUMINATION    = 5
    ADDITIVE_SELF_TEX_ILLUMINATION      = 6

class EDMPropsSpecialTypeInt(int, Enum):
    UNKNOWN_TYPE        = 0
    USER_BOX            = 1
    BOUNDING_BOX        = 2
    COLLISION_LINE      = 3
    COLLISION_SHELL     = 4
    CONNECTOR           = 5
    FAKE_LIGHT          = 6
    LIGHT_BOX           = 7
    NUMBER_TYPE         = 8
    SKIN_BOX            = 9

class EDMShadowCaster(int, Enum):
	YES             = 0
	NO              = 1
	ONLY            = 2

class EDMTransparentMode(int, Enum):
	OPAQUE          = 0
	BLEND           = 1
	ALPHA_TEST      = 2

class SocketItemTypeEnum(str, Enum):
    SOCKET          = 'SOCKET'
    PANEL           = 'PANEL'

class SocketItemInOutTypeEnum(str, Enum):
    INPUT           = 'INPUT'
    OUTPUT          = 'OUTPUT'
	
class NodeGroupTypeEnum(str, Enum):
    DECK            = 'EDM_Deck_Material'
    DEFAULT         = 'EDM_Default_Material'
    FAKE_OMNI       = 'EDM_Fake_Omni_Material'
    FAKE_SPOT       = 'EDM_Fake_Spot_Material'
    GLASS           = 'EDM_Glass_Material'
    MIRROR          = 'EDM_Mirror_Material'

## temrorary. TODO: add support of mirror and glass (or delete it if its not used).
def get_node_group_types():
    return (NodeGroupTypeEnum.DECK, NodeGroupTypeEnum.DEFAULT, NodeGroupTypeEnum.FAKE_OMNI, NodeGroupTypeEnum.FAKE_SPOT)

class NodeSocketCommonEnum(str, Enum):
    VERSION         = 'Version'

class NodeSocketInEmissiveEnum(str, Enum):
    EMISSIVE        = 'Emissive'
    NAV_LIGHT       = 'NAV Light'

class NodeSocketInFakeOmniEnum(str, Enum):
    EMISSIVE        = 'Emissive'
    LUMINANCE       = 'Luminance'
    MIN_SIZE_PIXELS = 'MinSizePixels'
    MAX_DISTANCE    = 'MaxDistance'
    SHIFT_TO_CAMERA = 'ShiftToCamera'

class NodeSocketInFakeSpotEnum(str, Enum):
    EMISSIVE        = 'Emissive'
    LUMINANCE       = 'Luminance'
    MIN_SIZE_PIXELS = 'MinSizePixels'
    MAX_DISTANCE    = 'MaxDistance'
    SHIFT_TO_CAMERA = 'ShiftToCamera'
    PHI             = 'Outer Angle'
    THETA           = 'Inner Angle'
    SPECULAR_AMOUNT = 'SpecularAmount'

class NodeSocketInMirrorEnum(str, Enum):
    BASE_COLOR      = 'Base Color'

class NodeSocketInGlassEnum(str, Enum):
    BASE_COLOR      = 'Base Color'
    BASE_ALPHA      = 'Base Alpha*'
    DECAL_COLOR     = 'Decal Color'
    DECAL_ALPHA     = 'Decal Alpha*'
    ROUGH_METAL     = 'RoughMet (Non-Color)'
    AO_VALUE        = 'AO Value'
    LIGHTMAP        = 'LightMap (Non-Color)'
    LIGHTMAP_VALUE  = 'LightMap Value'
    NORMAL          = 'Normal (Non-Color)'
    NORMAL_ENCODING = 'Normal Encoding DirectX/OpenGL'
    EMISSIVE        = 'Emissive'
    EMISSIVE_VALUE  = 'Emissive Value'
    FILTER_COLOR    = 'Filter Color'
    FLIR            = 'Flir'
    DAMAGE_COLOR    = 'Damage Color'
    DAMAGE_NORMAL   = 'Damage Normal'
    DAMAGE_MASK     = 'Damage Mask'
    DAMAGE_ARG      = 'Damage Arg'
    DECALID         = 'DecalId'
    SHADOW_CASTER   = 'Shadow Caster'
    TRANSPARENCY    = 'Transparency'

class NodeSocketInDefaultEnum(str, Enum):
    BASE_COLOR      = 'Base Color'
    BASE_ALPHA      = 'Base Alpha*'
    DECAL_COLOR     = 'Decal Color'
    DECAL_ALPHA     = 'Decal Alpha*'
    ROUGH_METAL     = 'RoughMet (Non-Color)'
    AO_VALUE        = 'AO Value'
    LIGHTMAP        = 'LightMap (Non-Color)'
    LIGHTMAP_VALUE  = 'LightMap Value'
    NORMAL          = 'Normal (Non-Color)'
    NORMAL_ENCODING = 'Normal Encoding DirectX/OpenGL'
    EMISSIVE        = 'Emissive'
    EMISSIVE_MASK   = 'Emissive Mask'
    EMISSIVE_VALUE  = 'Emissive Value'
    FLIR            = 'Flir'
    DAMAGE_COLOR    = 'Damage Base'
    DAMAGE_NORMAL   = 'Damage Normal (Non-Color)'
    DAMAGE_MASK     = 'Damage Mask (Non-Color)'
    DAMAGE_ALPHA    = 'Damage Map Alpha'
    DAMAGE_ARG      = 'Damage Arg'
    DECALID         = 'DecalId'
    SHADOW_CASTER   = 'Shadow Caster'
    TRANSPARENCY    = 'Transparency'
    OPACITY_VALUE   = 'Opacity Value'

class NodeSocketInDeckEnum(str, Enum):
    BASE_TILE_MAP   = 'Tiled Base Color'
    BASE_ALPHA      = 'Base_Alpha'
    NORMAL_TILE_MAP = 'Tiled Normal (Non-Color)'
    RMO_TILE_MAP    = 'Tiled RoughMet (Non-Color)'
    DECAL_BASE_COLOR= 'Decal Base'
    DECAL_ALPHA     = 'Decal Alpha'
    DECAL_RMO       = 'Decal RoughMetAO (Non-Color)'
    AO_VALUE        = 'AO Value'
    DAMAGE_COLOR    = 'Damage Base'
    DAMAGE_NORMAL   = 'Damage Normal (Non-Color)'
    DAMAGE_MASK     = 'Damage Mask (Non-Color)'
    DAMAGE_ALPHA    = 'Damage Map Alpha'
    RAIN_MASK       = 'Wet Map (Non-Color)'
    WETNESS         = 'Wetness'
    DECALID         = 'DecalId'
    TRANSPARENCY    = 'Transparency'

class BpyShaderNode(str, Enum):
    MIX_RGB                 = 'ShaderNodeMixRGB'
    MIX                     = 'ShaderNodeMix'
    SEPARATE_RGB            = 'ShaderNodeSeparateRGB'
    SEPARATE_COLOR          = 'ShaderNodeSeparateColor'
    COLOR_RAMP              = "ShaderNodeValToRGB"
    INVERT                  = 'ShaderNodeInvert'
    COMBINE_RGB             = 'ShaderNodeCombineRGB'
    NORMAL_MAP              = 'ShaderNodeNormalMap'
    BSDF_PRINCIPLED         = 'ShaderNodeBsdfPrincipled'
    NODE_GROUP              = 'ShaderNodeGroup'
    NODE_GROUP_EDM          = 'EdmMatrialShaderNodeType'
    NODE_GROUP_DEFAULT      = 'EdmDefaultShaderNodeType'
    NODE_GROUP_DECK         = 'EdmDeckShaderNodeType'
    NODE_GROUP_FAKE_OMNI    = 'EdmFakeOmniShaderNodeType'
    NODE_GROUP_FAKE_SPOT    = 'EdmFakeSpotShaderNodeType'
    NODE_TREE               = 'ShaderNodeTree'
    UVMAP                   = 'ShaderNodeUVMap'
    NODE_GROUP_INPUT        = 'NodeGroupInput'
    NODE_GROUP_OUTPUT       = 'NodeGroupOutput'
    NODE_REROUTE            = 'NodeReroute'
    SHADER_NODE             = 'ShaderNode'
    SHADER_NODE_MATH        = 'ShaderNodeMath'
    OUTPUT_MATERIAL         = 'ShaderNodeOutputMaterial'
    OUTPUT_LIGHT            = 'ShaderNodeOutputLight'
    EMISSION                = 'ShaderNodeEmission'
    LIGHT_FALLOFF           = 'ShaderNodeLightFalloff'

class BpyNodeSocketType(str, Enum):
    FLOAT               = 'NodeSocketFloat'
    COLOR               = 'NodeSocketColor'
    SHADER              = 'NodeSocketShader'
    VECTOR              = 'NodeSocketVector'
    INTEGER             = 'NodeSocketInt'
    SHADOWCASTER        = 'EdmSocketShadowCasterType'
    TRANSPARENCY        = 'EdmTransparencySocketType'
    DECK_TRANSPARENCY   = 'EdmDeckTransparencySocketType'
    EMISSION            = 'EdmEmissionTypeSocketType'

class ShaderNodeLightFalloffOutParams(str, Enum):
    QUADRATIC       = 'Quadratic'
    LINEAR          = 'Linear'
    CONSTANT        = 'Constant'

class ShaderNodeLightFalloffInParams(str, Enum):
    STRENGTH        = 'Strength'
    SMOOTH          = 'Smooth'

class ShaderNodeMixInParams(str, Enum):
    FACTOR          = 'Factor'
    A               = 'A'
    B               = 'B'

class ShaderNodeMappingInParams(str, Enum):
    VECTOR          = 'Vector'
    LOCATION        = 'Location'
    ROTATION        = 'Rotation'
    SCALE           = 'Scale'

class ShaderNodeMappingOutParams(str, Enum):
    VECTOR          = 'Vector'

class ShaderNodeMixOutParams(str, Enum):
    RESULT          = 'Result'

class ShaderNodeSeparateColorOutParams(str, Enum):
     RED            = 'Red'
     GREEN          = 'Green'
     BLUE           = 'Blue'

class ShaderNodeSeparateColorInParams(str, Enum):
     COLOR          = 'Color'

class ShaderNodeTexImageOutParams(str, Enum):
     COLOR          = 'Color'
     ALPHA          = 'Alpha'

class ShaderNodeTexImageInParams(str, Enum):
     VECTOR         = 'Vector'

class NodeSocketOutEmissiveEnum(str, Enum):
    SURFACE         = 'Surface'

class NodeSocketInEmissiveEnum(str, Enum):
    COLOR           = 'Color'
    STRENGTH        = 'Strength'

class BpyMixRampBlend(str, Enum):
    MIX             = 'MIX'
    DARKEN          = 'DARKEN'
    MULTIPLY        = 'MULTIPLY'
    BURN            = 'BURN'
    LIGHTEN         = 'LIGHTEN'
    SCREEN          = 'SCREEN'
    DODGE           = 'DODGE'
    ADD             = 'ADD'
    OVERLAY         = 'OVERLAY'
    SOFT_LIGHT      = 'SOFT_LIGHT'
    LINEAR_LIGHT    = 'LINEAR_LIGHT'
    DIFFERENCE      = 'DIFFERENCE'
    EXCLUSION       = 'EXCLUSION'
    SUBTRACT        = 'SUBTRACT'
    DIVIDE          = 'DIVIDE'
    HUE             = 'HUE'
    SATURATION      = 'SATURATION'
    COLOR           = 'COLOR'
    VALUE           = 'VALUE'

class ShaderNodeSeparateRGBInParams(str, Enum):
     IMAGE          = 'Image'

class ShaderNodeSeparateRGBOutParams(str, Enum):
     R              = 'R'
     G              = 'G'
     B              = 'B'

class ShaderNodeMixRGBInParams(str, Enum):
    FAC             = 'Fac'
    COLOR1          = 'Color1'
    COLOR2          = 'Color2'

class ShaderNodeMixRGBOutParams(str, Enum):
    COLOR           = 'Color'

class ShaderNodeInvertInParams(str, Enum):
    COLOR           = 'Color'
    Fac             = 'Fac'

class ShaderNodeInvertOutParams(str, Enum):
    COLOR           = 'Color'

class ShaderNodeCombineRGBInParams(str, Enum):
    R               = 'R'
    G               = 'G'
    B               = 'B'

class ShaderNodeCombineRGBOutParams(str, Enum):
    IMAGE           = 'Image'

class ShaderNodeNormalMapInParams(str, Enum):
    STRENGTH        = 'Strength'
    COLOR           = 'Color'

class ShaderNodeNormalMapOutParams(str, Enum):
    NORMAL          = 'Normal'

class ShaderNodeBsdfPrincipledInParams(str, Enum):
    BASE_COLOR      = 'Base Color'
    SUBSURFACE      = 'Subsurface'
    SUBSURFACE_RADIUS   = 'Subsurface Radius'
    SUBSURFACE_COLOR    = 'Subsurface Color'
    SUBSURFACE_IOR   = 'Subsurface IOR'
    SUBSURFACE_ANISOTROPY   = 'Subsurface Anisotropy'
    METALLIC        = 'Metallic'
    SPECULAR        = 'Specular'
    SPECULAR_TINT   = 'Specular Tint'
    ROUGHNESS       = 'Roughness'
    ANISOTROPIC     = 'Anisotropic'
    ANISOTROPIC_ROTATION    = 'Anisotropic Rotation'
    SHEEN           = 'Sheen'
    SHEEN_TINT      = 'Sheen Tint'
    CLEARCOAT       = 'Clearcoat'
    CLEARCOAT_ROUGHNESS     = 'Clearcoat Roughness'
    IOR             = 'IOR'
    TRANSMISSION    = 'Transmission'
    TRANSMISSION_ROUGHNESS  = 'Transmission Roughness'
    EMISSION        = 'Emission'
    EMISSION_STRENGTH   = 'Emission Strength'
    ALPHA           = 'Alpha'
    NORMAL          = 'Normal'
    CLEARCOAT_NORMAL    = 'Clearcoat Normal'
    TANGENT         = 'Tangent'

class ShaderNodeBsdfPrincipledOutParams(str, Enum):
    BSDF            = 'BSDF'