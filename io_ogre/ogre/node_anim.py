
# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    # ...so we need to reload our submodule(s) using importlib
    import importlib
    if "config" in locals():
        importlib.reload(config)
    if "report" in locals():
        importlib.reload(report)
    if "xml" in locals():
        importlib.reload(xml)
    if "util" in locals():
        importlib.reload(util)

# This is only relevant on first run, on later reloads those modules
# are already in locals() and those statements do not do anything.
import bpy, mathutils, logging, time
from .. import config
from ..report import Report
from ..xml import RDocument
from .. import util
from os.path import join

logger = logging.getLogger('node_anim')

# Node Animation, based on the work done in Easy Ogre Exporter (3D Studio Max exporter)
# https://github.com/OGRECave/EasyOgreExporter/blob/master/source/ExScene.cpp#L104
# The idea is that the data exported by blender2ogre would have the same format as the one exported by Easy Ogre Exporter which would be the standard by being the first ones to implement it
# There seems to be some support for animation in the Maya Ogre Exporter, but for the camera so it is possible to animate values like FOV
# https://github.com/bitgate/maya-ogre3d-exporter/blob/master/src/ogreExporter.cpp#L373

def dot_nodeanim(ob, doc, xmlnode):
    """
    Create the node animation for this object. 
    This is only possible if the object has any animation data

    ob: the blender object
    doc: the parent xml node to attach the animation data
    """

    # Do not process node animations for Armatures (to avoid setting spurious rotations on the armature which causes problems with SeletalAnimation)
    # To have a node animation in combination with an Armature, it should be parented to an Empty and have the Empty animated
    if ob.type == 'ARMATURE':
        return

    anim = ob.animation_data

    if anim is None or anim.nla_tracks is None:
        return

    savedUseNla = anim.use_nla
    savedAction = anim.action
    anim.use_nla = False
    if not len( anim.nla_tracks ):
        Report.warnings.append('You must assign an NLA strip to object (%s) that defines the start and end frames' % ob.name)

    logger.info('* Generating node animation for: %s' % ob.name)

    start = time.time()

    actions = {}  # actions by name
    # the only thing NLA is used for is to gather the names of the actions
    # it doesn't matter if the actions are all in the same NLA track or in different tracks
    for nla in anim.nla_tracks:        # NLA required, lone actions not supported
        logger.info('+ NLA track: %s' % nla.name)

        for strip in nla.strips:
            action = strip.action
            actions[ action.name ] = [action, strip.action_frame_start, strip.action_frame_end]
            logger.info('  - Action name: %s' % action.name)
            logger.info('  -  Strip name: %s' % strip.name)

    actionNames = sorted( actions.keys() )  # output actions in alphabetical order
    for actionName in actionNames:
        actionData = actions[ actionName ]
        action = actionData[0]
        anim.action = action  # set as the current action
        write_animation( ob, action, actionData[1], actionData[2], doc, xmlnode )

    # restore these to what they originally were
    anim.action = savedAction
    anim.use_nla = savedUseNla

    logger.info('- Done at %s seconds' % util.timer_diff_str(start))

# A note about the option: NODE_KEYFRAMES
# If NODE_KEYFRAMES is False, then this function processess the objects animation frame by frame, instead of using its keyframes
# The advantage of this method is that it respects the users tuning of the node animation curves
# The disadvantage is that it generates more data than just processing the keyframes and it might clutter the .scene file.
# Since the .scene file is not a binary file it might take longer to process with this method

# If NODE_KEYFRAMES is True, then this function processess the objects keyframes one by one by going through the F-Curves
# The advantage of this method is that it is very fast and produces less data (only the keyframes)
# The disadvantage is that if the user did an extensive tuning of the node animation curves that tuning is lost since only IM_LINEAR / IM_SPLINE at the global level is supported by Ogre
# Another disadvantage is that it is very difficult if not impossible to choose between IM_LINEAR or IM_SPLINE for the resulting animation since the user might be choosing between different interpolation types for each F-Curve
def write_animation(ob, action, frame_start, frame_end, doc, xmlnode):

    _fps = float( bpy.context.scene.render.fps )

    # Actually in Blender this does not make sense because there is only one possible animation per object,
    # but lets maintain compatibility with Easy Ogre Exporter
    aa = doc.createElement('animations')
    xmlnode.appendChild(aa)

    a = doc.createElement('animation')
    a.setAttribute("name", "%s" % action.name)
    a.setAttribute("enable", "false")
    a.setAttribute("loop", "false")
    a.setAttribute("interpolationMode", "linear")
    a.setAttribute("rotationInterpolationMode", "linear")
    a.setAttribute("length", '%6f' % ((frame_end) / _fps))
    aa.appendChild(a)

    frame_current = bpy.context.scene.frame_current

    initial_location = mathutils.Vector((0, 0, 0))
    initial_rotation = mathutils.Quaternion((1, 0, 0, 0))
    initial_scale = mathutils.Vector((1, 1, 1))

    frames = range(int(frame_start), int(frame_end) + 1)

    # If NODE_KEYFRAMES is True, then use only the keyframes to export the animation
    #if config.get('NODE_KEYFRAMES') is True:
    #    frames = get_keyframes(action)

    for frame in frames:

        kf = doc.createElement('keyframe')
        kf.setAttribute("time", '%6f' % (frame / _fps))
        a.appendChild(kf)

        bpy.context.scene.frame_set(frame)

        translation = mathutils.Vector((0, 0, 0))
        rotation_quat = mathutils.Quaternion((1, 0, 0, 0))
        scale = mathutils.Vector((1, 1, 1))

        if frame == frame_start:
            initial_location = util.swap( ob.matrix_local.to_translation() )
            initial_rotation = util.swap( ob.matrix_local.to_quaternion() )
            initial_scale = calc_scale( ob.matrix_local )

        else:
            translation = util.swap( ob.matrix_local.to_translation() ) - initial_location
            rotation_quat = initial_rotation.rotation_difference( util.swap( ob.matrix_local.to_quaternion() ) )
            current_scale = calc_scale( ob.matrix_local )
            scale.x = current_scale.x / initial_scale.x
            scale.y = current_scale.y / initial_scale.y
            scale.z = current_scale.z / initial_scale.z

        t = doc.createElement('position')
        t.setAttribute("x", '%6f' % translation.x)
        t.setAttribute("y", '%6f' % translation.y)
        t.setAttribute("z", '%6f' % translation.z)
        kf.appendChild(t)

        q = doc.createElement('rotation')
        q.setAttribute("qw", '%6f' % rotation_quat.w)
        q.setAttribute("qx", '%6f' % rotation_quat.x)
        q.setAttribute("qy", '%6f' % rotation_quat.y)
        q.setAttribute("qz", '%6f' % rotation_quat.z)
        kf.appendChild(q)

        s = doc.createElement('scale')
        s.setAttribute("x", '%6f' % scale.x)
        s.setAttribute("y", '%6f' % scale.y)
        s.setAttribute("z", '%6f' % scale.z)
        kf.appendChild(s)

    bpy.context.scene.frame_set(frame_current)

def calc_scale(matrix_local):
    # Scale is different in Ogre from blender - rotation is removed
    ri = matrix_local.to_quaternion().inverted().to_matrix()
    scale = ri.to_4x4() * matrix_local
    v = util.swap( scale.to_scale() )

    return mathutils.Vector((abs(v.x), abs(v.y), abs(v.z)))

def get_keyframes(action):

    keyframes = {}

    for fcurve in action.fcurves:

        for keyframe in fcurve.keyframe_points:

            frame, value = keyframe.co

            # Add Keyframe if it does not exist
            if frame not in keyframes:
                keyframes[frame] = frame

    return sorted(keyframes)

