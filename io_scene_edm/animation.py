from mathutils import Matrix
from pyedm_platform_selector import pyedm
from enum import Enum
from math_tools import euler_to_quat
from bpy.types import FCurve, Action, Object, AnimData
from typing import Union, Callable, Set, Tuple, List
import utils

class Data_Path_Enum(str, Enum):
    LOCATION        = 'location'
    ROTATION_QUAT   = 'rotation_quaternion'
    ROTATION_EULER  = 'rotation_euler'
    SCALE           = 'scale'
    ENERGY          = 'energy'
    COLOR           = 'color'
    CUTOFF_DISTANCE = 'cutoff_distance'
    SPECULAR        = 'specular_factor'
    SPOT_SIZE       = 'spot_size'
    SPOT_BLEND      = 'spot_blend'

OBJ_PATHS = [
    Data_Path_Enum.ROTATION_QUAT,
    Data_Path_Enum.ROTATION_EULER,
    Data_Path_Enum.LOCATION,
    Data_Path_Enum.SCALE
]

DATA_PATHS = [
    Data_Path_Enum.ENERGY,
    Data_Path_Enum.COLOR,
    Data_Path_Enum.CUTOFF_DISTANCE,
    Data_Path_Enum.SPECULAR,
    Data_Path_Enum.SPOT_SIZE,
    Data_Path_Enum.SPOT_BLEND
]

def get_anim_ch_paths(action: Action) -> Set[str]:
    result: Set[str] = set()
    if not action:
        return result
    for fcurve in action.fcurves:
        result.add(fcurve.data_path)
    return result

class DummyFCurve:
    def __init__(self, array_index: int, val) -> None:
        self.keyframe_points = []
        self.array_index = array_index
        self.val = val
    
    def update(self):
        pass

    def evaluate(self, frame):
        return self.val

# Bones add thier name to data_path, so we add argument process and return data_path whitout bone name.
# allowed_args == None means any args are allowed
# Returns tuple (action, arg) on success or (None, -1).
def has_transform_anim(obj: Object, data_path_modifier=lambda x: x, allowed_args=None) -> bool:
    obj_ad = obj.animation_data
    if not obj_ad or not obj_ad.action:
        return (None, -1)

    arg = utils.extract_arg_number(obj_ad.action.name)
    if arg < 0 or (allowed_args and arg not in allowed_args):
        return (None, -1)

    for fcu in obj_ad.action.fcurves:
         if data_path_modifier(fcu.data_path) in OBJ_PATHS:
            return (obj_ad.action, arg)
    
    return (None, -1)

def has_data_anim(obj: Object) -> bool:
    if not hasattr(obj, 'data'):
        return False
    data_ad: AnimData = obj.data.animation_data
    if not data_ad or not data_ad.action:
        return False

    for fcu in data_ad.action.fcurves:
         if fcu.data_path in DATA_PATHS:
            return True
    return False

def has_path_anim(anim_data: AnimData, data_path: str) -> bool:
    if not anim_data: 
        return False
    if not data_path:
        return False
    if not anim_data.action:
        return False
    action: Action = anim_data.action
    for fcu in action.fcurves:
        if data_path == fcu.data_path:
            return True
    return False

KeyFrameTime = float
KeyFrameValue = Union[float, List[float]]
KeyFrameValueTransform = Callable[[KeyFrameValue], KeyFrameValue]
KeyFramePoint = Tuple[KeyFrameTime, KeyFrameValue]
KeyFramePoints = List[KeyFramePoint]

# Returns [(key, value), ...] for 1 animation element and [(key, [value1, value2, ...], ...] for multiple, or None
def fcurves_animation(fcurves: List[FCurve], expected_num: int, def_value: KeyFrameValue, fn: KeyFrameValueTransform = lambda v: v) -> KeyFramePoints:
    if not def_value:
        def_value = [0] * expected_num
    
    # collect keys
    keys = set()
    for fcu in fcurves:
        fcu.update()
        for kf in fcu.keyframe_points:
            keys.add(kf.co[0])

    # collect values
    keys = sorted([x for x in keys])
    kvs = []
    if expected_num > 1:
        for k in keys:
            v = []
            for fcu in fcurves:
                if not type(fcu) is DummyFCurve:
                    val = fcu.evaluate(k)
                    v.append(val)
                else:
                    v.append(fcu.val)
            kvs.append((((k / 100.0) - 1.0), fn(v)))
    else:
        for k in keys:
            for fcu in fcurves:
                v = fcu.evaluate(k)
                kvs.append((((k / 100.0) - 1.0), fn(v)))
        
    return kvs

# Returns [(key, value), ...] for 1 animation element and [(key, [value1, value2, ...], ...] for multiple, or None
def action_animation(action: Action, data_path: str, expected_num: int, def_value: KeyFrameValue, fn: KeyFrameValueTransform = lambda v: v) -> KeyFramePoints:
    if not action:
        return None
    
    if not def_value:
        def_value = [0] * expected_num
    
    fcurves = [DummyFCurve(i, def_value[i]) for i in range(expected_num)]

    not_dummy = False
    for fcu in action.fcurves:
        if fcu.data_path == data_path:
            not_dummy = True
            fcurves[fcu.array_index] = fcu

    if not not_dummy:
        return None
    
    return fcurves_animation(fcurves, expected_num, def_value, fn)

def extract_anim_float(action: Action, data_path: str, fn: KeyFrameValueTransform = lambda v: v) -> KeyFramePoints:
    return action_animation(action, data_path, 1, None, fn)

def extract_anim_vec2(action: Action, data_path: str, def_value, fn: KeyFrameValueTransform = lambda v: v) -> KeyFramePoints:
    return action_animation(action, data_path, 2, def_value, fn)

def extract_anim_vec3(action: Action, data_path: str, def_value, fn: KeyFrameValueTransform = lambda v: v) -> KeyFramePoints:
    return action_animation(action, data_path, 3, def_value, fn)

def extract_anim_vec4(action: Action, data_path: str, def_value, fn: KeyFrameValueTransform = lambda v: v) -> KeyFramePoints:
    return action_animation(action, data_path, 4, def_value, fn)

def euler_to_quat_anim(rot_anim):
    a = []
    for i in rot_anim[1]:
        a.append((i[0], euler_to_quat(i[1])))

    return [rot_anim[0], a]

class AllowedAnimationsEnum(int, Enum):
    LOCATION    = 1 << 0
    SCALE       = 1 << 1
    ROTATION    = 1 << 2
    ALL         = 0xffffffff

def extract_transform_anim(parent: pyedm.Node, action, arg, mat, bmat, name, allowed_anims=AllowedAnimationsEnum.ALL, data_path_enum=Data_Path_Enum):
    bmat_inv = bmat.inverted()
    bloc, brot, bsca = bmat.decompose()
    euler_brot = brot.to_euler()

    al = ar = asc = None

    if allowed_anims & AllowedAnimationsEnum.LOCATION:
        loc_keys = extract_anim_vec3(action, data_path_enum.LOCATION, bloc)
        if loc_keys != None:
            al = pyedm.AnimationNode('al_' + name)
            al.setPositionAnimation([[arg, loc_keys]])
    
    if allowed_anims & AllowedAnimationsEnum.SCALE:
        scale_keys = extract_anim_vec3(action, data_path_enum.SCALE, bsca)
        if scale_keys:
            asc = pyedm.AnimationNode('as_' + name)
            asc.setScaleAnimation([[arg, scale_keys]])

    if allowed_anims & AllowedAnimationsEnum.ROTATION:
        rot_keys = extract_anim_vec3(action, data_path_enum.ROTATION_EULER, euler_brot)
        if rot_keys != None:
            anim = euler_to_quat_anim([arg, rot_keys])
            ar = pyedm.AnimationNode('ar_' + name)
            ar.setRotationAnimation([anim])
        else:
            rot_keys = extract_anim_vec4(action, data_path_enum.ROTATION_QUAT, brot)
            if rot_keys:
                ar = pyedm.AnimationNode('ar_' + name)
                ar.setRotationAnimation([[arg, rot_keys]])

    #al = ar = asc =  None
    a = parent
    
    a = a.addChild(pyedm.Transform(name + '_mat', mat))
    a = a.addChild(pyedm.Transform(name + '_bmat_inv', bmat_inv))

    if al:
        a = a.addChild(al)
    else:
        a = a.addChild(pyedm.Transform('tl_' + name, Matrix.LocRotScale(bloc, None, None)))

    if asc:
        a = a.addChild(asc)
    else:
        a = a.addChild(pyedm.Transform('s_' + name, Matrix.LocRotScale(None, None, bsca)))

    if ar:
        a = a.addChild(ar)
    else:
        a = a.addChild(pyedm.Transform('tr_' + name, Matrix.LocRotScale(None, brot, None)))

    return a

# allowed_args == None means any args are allowed
# Animation keys are in space before parenting applied (matrix_basis's space).
def extract_transform_animation(parent: pyedm.Node, obj: Object, allowed_args=None) -> Union[pyedm.AnimationNode, pyedm.Transform]:
    action, arg = has_transform_anim(obj, allowed_args=allowed_args)
    if not action:
        parent = parent.addChild(pyedm.Transform(obj.name, obj.matrix_local))
        return parent
    
    a = extract_transform_anim(parent, action, arg, obj.matrix_local, obj.matrix_basis, obj.name)

    return a
