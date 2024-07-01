import bpy

BLENDER_VERSION_MAJOR = bpy.app.version[0]
BLENDER_VERSION_MINOR = bpy.app.version[1]
IS_BLENDER_3 = BLENDER_VERSION_MAJOR == 3
IS_BLENDER_4 = BLENDER_VERSION_MAJOR == 4
BLENDER_36 = 36
BLENDER_40 = 40
BLENDER_41 = 41
BLENDER_RELEASE = bpy.app.version[0] * 10 + bpy.app.version[1]

if IS_BLENDER_3:
    import version_specific_v3 as v3
    from bpy.types import NodeSocketInterface
    InterfaceNodeSocket = NodeSocketInterface
    
    get_version = v3.get_version
    create_inodesocket_output = v3.create_inodesocket_output
    extract_group_outputs = v3.extract_group_outputs
    create_inodesocket_input = v3.create_inodesocket_input
    create_custom_inodesocket_input = v3.create_custom_inodesocket_input
    extract_group_inputs = v3.extract_group_inputs
    
elif IS_BLENDER_4:
    import version_specific_v4 as v4
    from bpy.types import NodeTreeInterfaceSocket
    InterfaceNodeSocket = NodeTreeInterfaceSocket

    get_version = v4.get_version
    create_inodesocket_output = v4.create_inodesocket_output
    extract_group_outputs = v4.extract_group_outputs
    create_inodesocket_input = v4.create_inodesocket_input
    create_custom_inodesocket_input = v4.create_inodesocket_input
    extract_group_inputs = v4.extract_group_inputs
    