from bpy.types import NodeTree, ShaderNodeGroup
from serializer import SOutput, SInput
from typing import List, Union, Tuple
from utils import type_helper
from enums import SocketItemTypeEnum, SocketItemInOutTypeEnum, BpyNodeSocketType

from bpy.types import NodeTreeInterfaceSocket
from bpy.types import NodeTree

def get_version(node_tree: NodeTree) -> int:
    if not node_tree:
        return 0
    version_socket: NodeTreeInterfaceSocket = node_tree.interface.items_tree.get('Version')
    if not version_socket:
        return 0
    
    return version_socket.default_value

def create_inodesocket_output(self, node_tree: NodeTree) -> NodeTreeInterfaceSocket:
    if self.bl_socket_idname == BpyNodeSocketType.INTEGER:
        socket: NodeTreeInterfaceSocket = node_tree.interface.new_socket(self.name, socket_type=BpyNodeSocketType.FLOAT, in_out=SocketItemInOutTypeEnum.OUTPUT)
    else:
        socket: NodeTreeInterfaceSocket = node_tree.interface.new_socket(self.name, socket_type=self.bl_socket_idname, in_out=SocketItemInOutTypeEnum.OUTPUT)
    return socket

def create_inodesocket_input(sinput: SInput, node_tree: NodeTree) -> Union[NodeTreeInterfaceSocket, None]:
    if sinput.bl_socket_idname in (BpyNodeSocketType.TRANSPARENCY, BpyNodeSocketType.DECK_TRANSPARENCY, BpyNodeSocketType.SHADOWCASTER):
        return None
    if sinput.bl_socket_idname in (BpyNodeSocketType.INTEGER):
        socket: NodeTreeInterfaceSocket = node_tree.interface.new_socket(sinput.name, socket_type=BpyNodeSocketType.FLOAT, in_out=SocketItemInOutTypeEnum.INPUT)
    else:
        socket: NodeTreeInterfaceSocket = node_tree.interface.new_socket(sinput.name, socket_type=sinput.bl_socket_idname, in_out=SocketItemInOutTypeEnum.INPUT)
    return socket

def extract_group_outputs(node_group: ShaderNodeGroup) -> List[SOutput]:
    outputs: List[SOutput] = []
    for output in [item for item in node_group.node_tree.interface.items_tree if item.item_type == SocketItemTypeEnum.SOCKET and item.in_out == SocketItemInOutTypeEnum.OUTPUT]:
        socket_type: str = node_group.outputs[output.name].bl_idname if hasattr(node_group.outputs[output.name], 'bl_idname') else output.bl_socket_idname
        outputs.append(
            SOutput (
                socket_type,
                output.name,
                output.description
            )
        )
    return outputs

def extract_group_inputs(node_group: ShaderNodeGroup) -> List[SInput]:
    inputs: List[SInput] = []
    if not node_group:
        return inputs
    for input in [item for item in node_group.node_tree.interface.items_tree if item.item_type == SocketItemTypeEnum.SOCKET and item.in_out == SocketItemInOutTypeEnum.INPUT]:
        default_value = type_helper(input.default_value) if hasattr(input, 'default_value') else None
        min_max_tuple = (type_helper(input.min_value), type_helper(input.max_value)) if hasattr(input, 'min_value') else None
        instance_value = type_helper(node_group.inputs[input.name].default_value) if hasattr(node_group.inputs.get(input.name), 'default_value') else None
        socket_type: str = node_group.inputs[input.name].bl_idname if hasattr(node_group.inputs.get(input.name), 'bl_idname') else input.bl_socket_idname
        input_type: str = node_group.inputs[input.name].bl_rna.properties['default_value'].rna_type.identifier if hasattr(input, 'default_value') else None
        enum_values: List[str] = None
        if input_type and input_type == 'EnumProperty':
            enum_values: List[Tuple[str, str, str, str]] = []
            for item in node_group.inputs[input.name].bl_rna.properties['default_value'].enum_items:
                enum_values.append((item.identifier, item.name, item.description, item.value))
        inputs.append(
            SInput(
                socket_type,
                input.name,
                input.description,
                default_value,
                min_max_tuple,
                instance_value,
                enum_values
            )
        )
    return inputs
