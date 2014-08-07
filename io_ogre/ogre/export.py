import bpy
import os
import getpass
import math
import mathutils
from bpy.props import EnumProperty, BoolProperty, FloatProperty, StringProperty, IntProperty
from .material import *
from .. import config
from ..config import CONFIG
from ..report import Report
from ..util import *
from ..xml import *
from .mesh import *

def export_mesh(ob, path='/tmp', force_name=None, ignore_shape_animation=False, normals=True):
    ''' returns materials used by the mesh '''
    return dot_mesh( ob, path, force_name, ignore_shape_animation, normals )

def _mesh_entity_helper( doc, ob, o ):
    ## extended format - BGE Physics ##
    o.setAttribute('mass', str(ob.game.mass))
    o.setAttribute('mass_radius', str(ob.game.radius))
    o.setAttribute('physics_type', ob.game.physics_type)
    o.setAttribute('actor', str(ob.game.use_actor))
    o.setAttribute('ghost', str(ob.game.use_ghost))
    o.setAttribute('velocity_min', str(ob.game.velocity_min))
    o.setAttribute('velocity_max', str(ob.game.velocity_max))
    o.setAttribute('lock_trans_x', str(ob.game.lock_location_x))
    o.setAttribute('lock_trans_y', str(ob.game.lock_location_y))
    o.setAttribute('lock_trans_z', str(ob.game.lock_location_z))
    o.setAttribute('lock_rot_x', str(ob.game.lock_rotation_x))
    o.setAttribute('lock_rot_y', str(ob.game.lock_rotation_y))
    o.setAttribute('lock_rot_z', str(ob.game.lock_rotation_z))
    o.setAttribute('anisotropic_friction', str(ob.game.use_anisotropic_friction))
    x,y,z = ob.game.friction_coefficients
    o.setAttribute('friction_x', str(x))
    o.setAttribute('friction_y', str(y))
    o.setAttribute('friction_z', str(z))
    o.setAttribute('damping_trans', str(ob.game.damping))
    o.setAttribute('damping_rot', str(ob.game.rotation_damping))
    o.setAttribute('inertia_tensor', str(ob.game.form_factor))

    mesh = ob.data
    # custom user props
    for prop in mesh.items():
        propname, propvalue = prop
        if not propname.startswith('_'):
            user = doc.createElement('user_data')
            o.appendChild( user )
            user.setAttribute( 'name', propname )
            user.setAttribute( 'value', str(propvalue) )
            user.setAttribute( 'type', type(propvalue).__name__ )

class _WrapLogic(object):
    SwapName = { 'frame_property' : 'animation' } # custom name hacks

    def __init__(self, node):
        self.node = node
        self.name = node.name
        self.type = node.type

    def widget(self, layout):
        box = layout.box()
        row = box.row()
        row.label( text=self.type )
        row.separator()
        row.prop( self.node, 'name', text='' )
        if self.type in self.TYPES:
            for name in self.TYPES[ self.type ]:
                if name in self.SwapName:
                    box.prop( self.node, name, text=self.SwapName[name] )
                else:
                    box.prop( self.node, name )

    def xml( self, doc ):
        g = doc.createElement( self.LogicType )
        g.setAttribute('name', self.name)
        g.setAttribute('type', self.type)
        if self.type in self.TYPES:
            for name in self.TYPES[ self.type ]:
                attr = getattr( self.node, name )
                if name in self.SwapName: name = self.SwapName[name]
                a = doc.createElement( 'component' )
                g.appendChild(a)
                a.setAttribute('name', name)
                if attr is None: a.setAttribute('type', 'POINTER' )
                else: a.setAttribute('type', type(attr).__name__)

                if type(attr) in (float, int, str, bool): a.setAttribute('value', str(attr))
                elif not attr: a.setAttribute('value', '')        # None case
                elif hasattr(attr,'filepath'): a.setAttribute('value', attr.filepath)
                elif hasattr(attr,'name'): a.setAttribute('value', attr.name)
                elif hasattr(attr,'x') and hasattr(attr,'y') and hasattr(attr,'z'):
                    a.setAttribute('value', '%s %s %s' %(attr.x, attr.y, attr.z))
                else:
                    print('ERROR: unknown type', attr)
        return g

class WrapSensor( _WrapLogic ):
    LogicType = 'sensor'
    TYPES = {
        'COLLISION': ['property'],
        'MESSAGE' : ['subject'],
        'NEAR' : ['property', 'distance', 'reset_distance'],
        'RADAR'  :  ['property', 'axis', 'angle', 'distance' ],
        'RAY'  :  ['ray_type', 'property', 'material', 'axis', 'range', 'use_x_ray'],
        'TOUCH'  :  ['material'],
    }

class WrapActuator( _WrapLogic ):
    LogicType = 'actuator'
    TYPES = {
        'CAMERA'  :  ['object', 'height', 'min', 'max', 'axis'],
        'CONSTRAINT'  :  ['mode', 'limit', 'limit_min', 'limit_max', 'damping'],
        'MESSAGE' : ['to_property', 'subject', 'body_message'],        #skipping body_type
        'OBJECT'  :  'damping derivate_coefficient force force_max_x force_max_y force_max_z force_min_x force_min_y force_min_z integral_coefficient linear_velocity mode offset_location offset_rotation proportional_coefficient reference_object torque use_local_location use_local_rotation use_local_torque use_servo_limit_x use_servo_limit_y use_servo_limit_z'.split(),
        'SOUND'  :  'cone_inner_angle_3d cone_outer_angle_3d cone_outer_gain_3d distance_3d_max distance_3d_reference gain_3d_max gain_3d_min mode pitch rolloff_factor_3d sound use_sound_3d volume'.split(),        # note .sound contains .filepath
        'VISIBILITY'  :  'apply_to_children use_occlusion use_visible'.split(),
        'SHAPE_ACTION'  :  'frame_blend_in frame_end frame_property frame_start mode property use_continue_last_frame'.split(),
        'EDIT_OBJECT'  :  'dynamic_operation linear_velocity mass mesh mode object time track_object use_3d_tracking use_local_angular_velocity use_local_linear_velocity use_replace_display_mesh use_replace_physics_mesh'.split(),
    }


def _ogre_node_helper( doc, ob, objects, prefix='', pos=None, rot=None, scl=None ):
    # shouldn't this be matrix_local?
    mat = get_parent_matrix(ob, objects).inverted() * ob.matrix_world

    o = doc.createElement('node')
    o.setAttribute('name',prefix+ob.name)
    p = doc.createElement('position')
    q = doc.createElement('rotation')       #('quaternion')
    s = doc.createElement('scale')
    for n in (p,q,s):
        o.appendChild(n)

    if pos:
        v = swap(pos)
    else:
        v = swap( mat.to_translation() )
    p.setAttribute('x', '%6f'%v.x)
    p.setAttribute('y', '%6f'%v.y)
    p.setAttribute('z', '%6f'%v.z)

    if rot:
        v = swap(rot)
    else:
        v = swap( mat.to_quaternion() )
    q.setAttribute('qx', '%6f'%v.x)
    q.setAttribute('qy', '%6f'%v.y)
    q.setAttribute('qz', '%6f'%v.z)
    q.setAttribute('qw','%6f'%v.w)

    if scl:        # this should not be used
        v = swap(scl)
        x=abs(v.x); y=abs(v.y); z=abs(v.z)
        s.setAttribute('x', '%6f'%x)
        s.setAttribute('y', '%6f'%y)
        s.setAttribute('z', '%6f'%z)
    else:        # scale is different in Ogre from blender - rotation is removed
        ri = mat.to_quaternion().inverted().to_matrix()
        scale = ri.to_4x4() * mat
        v = swap( scale.to_scale() )
        x=abs(v.x); y=abs(v.y); z=abs(v.z)
        s.setAttribute('x', '%6f'%x)
        s.setAttribute('y', '%6f'%y)
        s.setAttribute('z', '%6f'%z)
    return o

last_export_filepath = ""

class _OgreCommonExport_(object):

    @classmethod
    def poll(cls, context):
        if context.active_object and context.mode != 'EDIT_MESH':
            return True

    def invoke(self, context, event):
        # Resolve path from opened .blend if available. It's not if
        # blender normally was opened with "last open scene".
        # After export is done once, remember that path when re-exporting.
        global last_export_filepath
        if last_export_filepath == "":
            # First export during this blender run
            if self.filepath == "" and context.blend_data.filepath != "":
                path, name = os.path.split(context.blend_data.filepath)
                self.filepath = os.path.join(path, name.split('.')[0])
            if self.filepath == "":
                self.filepath = "blender2ogre-export"
            if self.EXPORT_TYPE == "OGRE":
                self.filepath += ".scene"
            elif self.EXPORT_TYPE == "REX":
                self.filepath += ".txml"
        else:
            # Sequential export, use the previous path
            self.filepath = last_export_filepath

        # Replace file extension if we have swapped dialogs.
        if self.EXPORT_TYPE == "OGRE":
            self.filepath = self.filepath.replace(".txml", ".scene")
        elif self.EXPORT_TYPE == "REX":
            self.filepath = self.filepath.replace(".scene", ".txml")

        # Update ui setting from the last export, or file config.
        self.update_ui()

        wm = context.window_manager
        fs = wm.fileselect_add(self) # writes to filepath
        return {'RUNNING_MODAL'}

    def execute(self, context):
        # Store this path for later re-export
        global last_export_filepath
        last_export_filepath = self.filepath

        # Run the .scene or .txml export
        self.ogre_export(self.filepath, context)
        return {'FINISHED'}

    def update_ui(self):
        self.EX_SWAP_AXIS = CONFIG['SWAP_AXIS']
        self.EX_SEP_MATS = CONFIG['SEP_MATS']
        self.EX_ONLY_DEFORMABLE_BONES = CONFIG['ONLY_DEFORMABLE_BONES']
        self.EX_ONLY_KEYFRAMED_BONES = CONFIG['ONLY_KEYFRAMED_BONES']
        self.EX_OGRE_INHERIT_SCALE = CONFIG['OGRE_INHERIT_SCALE']
        self.EX_SCENE = CONFIG['SCENE']
        self.EX_EXPORT_HIDDEN = CONFIG['EXPORT_HIDDEN']
        self.EX_SELONLY = CONFIG['SELONLY']
        self.EX_FORCE_CAMERA = CONFIG['FORCE_CAMERA']
        self.EX_FORCE_LAMPS = CONFIG['FORCE_LAMPS']
        self.EX_MESH = CONFIG['MESH']
        self.EX_MESH_OVERWRITE = CONFIG['MESH_OVERWRITE']
        self.EX_ARM_ANIM = CONFIG['ARM_ANIM']
        self.EX_SHAPE_ANIM = CONFIG['SHAPE_ANIM']
        self.EX_TRIM_BONE_WEIGHTS = CONFIG['TRIM_BONE_WEIGHTS']
        self.EX_ARRAY = CONFIG['ARRAY']
        self.EX_MATERIALS = CONFIG['MATERIALS']
        self.EX_FORCE_IMAGE_FORMAT = CONFIG['FORCE_IMAGE_FORMAT']
        self.EX_DDS_MIPS = CONFIG['DDS_MIPS']
        self.EX_COPY_SHADER_PROGRAMS = CONFIG['COPY_SHADER_PROGRAMS']
        self.EX_lodLevels = CONFIG['lodLevels']
        self.EX_lodDistance = CONFIG['lodDistance']
        self.EX_lodPercent = CONFIG['lodPercent']
        self.EX_nuextremityPoints = CONFIG['nuextremityPoints']
        self.EX_generateEdgeLists = CONFIG['generateEdgeLists']
        self.EX_generateTangents = CONFIG['generateTangents']
        self.EX_tangentSemantic = CONFIG['tangentSemantic']
        self.EX_tangentUseParity = CONFIG['tangentUseParity']
        self.EX_tangentSplitMirrored = CONFIG['tangentSplitMirrored']
        self.EX_tangentSplitRotated = CONFIG['tangentSplitRotated']
        self.EX_reorganiseBuffers = CONFIG['reorganiseBuffers']
        self.EX_optimiseAnimations = CONFIG['optimiseAnimations']

    # Basic options
    EX_SWAP_AXIS = EnumProperty(
        items=config.AXIS_MODES,
        name='swap axis',
        description='axis swapping mode',
        default= CONFIG['SWAP_AXIS'])
    EX_SEP_MATS = BoolProperty(
        name="Separate Materials",
        description="exports a .material for each material (rather than putting all materials in a single .material file)",
        default=CONFIG['SEP_MATS'])
    EX_ONLY_DEFORMABLE_BONES = BoolProperty(
        name="Only Deformable Bones",
        description="only exports bones that are deformable. Useful for hiding IK-Bones used in Blender. Note: Any bone with deformable children/descendants will be output as well.",
        default=CONFIG['ONLY_DEFORMABLE_BONES'])
    EX_ONLY_KEYFRAMED_BONES = BoolProperty(
        name="Only Keyframed Bones",
        description="only exports bones that have been keyframed for a given animation. Useful to limit the set of bones on a per-animation basis.",
        default=CONFIG['ONLY_KEYFRAMED_BONES'])
    EX_OGRE_INHERIT_SCALE = BoolProperty(
        name="OGRE inherit scale",
        description="whether the OGRE bones have the 'inherit scale' flag on.  If the animation has scale in it, the exported animation needs to be adjusted to account for the state of the inherit-scale flag in OGRE.",
        default=CONFIG['OGRE_INHERIT_SCALE'])
    EX_SCENE = BoolProperty(
        name="Export Scene",
        description="export current scene (OgreDotScene xml)",
        default=CONFIG['SCENE'])
    EX_SELONLY = BoolProperty(
        name="Export Selected Only",
        description="export selected",
        default=CONFIG['SELONLY'])
    EX_EXPORT_HIDDEN = BoolProperty(
        name="Export Hidden Also",
        description="Export hidden meshes in addition to visible ones. Turn off to avoid exporting hidden stuff.",
        default=CONFIG['EXPORT_HIDDEN'])
    EX_FORCE_CAMERA = BoolProperty(
        name="Force Camera",
        description="export active camera",
        default=CONFIG['FORCE_CAMERA'])
    EX_FORCE_LAMPS = BoolProperty(
        name="Force Lamps",
        description="export all lamps",
        default=CONFIG['FORCE_LAMPS'])
    EX_MESH = BoolProperty(
        name="Export Meshes",
        description="export meshes",
        default=CONFIG['MESH'])
    EX_MESH_OVERWRITE = BoolProperty(
        name="Export Meshes (overwrite)",
        description="export meshes (overwrite existing files)",
        default=CONFIG['MESH_OVERWRITE'])
    EX_ARM_ANIM = BoolProperty(
        name="Armature Animation",
        description="export armature animations - updates the .skeleton file",
        default=CONFIG['ARM_ANIM'])
    EX_SHAPE_ANIM = BoolProperty(
        name="Shape Animation",
        description="export shape animations - updates the .mesh file",
        default=CONFIG['SHAPE_ANIM'])
    EX_TRIM_BONE_WEIGHTS = FloatProperty(
        name="Trim Weights",
        description="ignore bone weights below this value (Ogre supports 4 bones per vertex)",
        min=0.0, max=0.5, default=CONFIG['TRIM_BONE_WEIGHTS'] )
    EX_ARRAY = BoolProperty(
        name="Optimize Arrays",
        description="optimize array modifiers as instances (constant offset only)",
        default=CONFIG['ARRAY'])
    EX_MATERIALS = BoolProperty(
        name="Export Materials",
        description="exports .material script",
        default=CONFIG['MATERIALS'])
    EX_DDS_MIPS = IntProperty(
        name="DDS Mips",
        description="number of mip maps (DDS)",
        min=0, max=16,
        default=CONFIG['DDS_MIPS'])

    # Mesh options
    EX_lodLevels = IntProperty(
        name="LOD Levels",
        description="MESH number of LOD levels",
        min=0, max=32,
        default=CONFIG['lodLevels'])
    EX_lodDistance = IntProperty(
        name="LOD Distance",
        description="MESH distance increment to reduce LOD",
        min=0, max=2000, default=CONFIG['lodDistance'])
    EX_lodPercent = IntProperty(
        name="LOD Percentage",
        description="LOD percentage reduction",
        min=0, max=99,
        default=CONFIG['lodPercent'])
    EX_nuextremityPoints = IntProperty(
        name="Extremity Points",
        description="MESH Extremity Points",
        min=0, max=65536,
        default=CONFIG['nuextremityPoints'])
    EX_generateEdgeLists = BoolProperty(
        name="Edge Lists",
        description="MESH generate edge lists (for stencil shadows)",
        default=CONFIG['generateEdgeLists'])
    EX_generateTangents = BoolProperty(
        name="Tangents",
        description="MESH generate tangents",
        default=CONFIG['generateTangents'])
    EX_tangentSemantic = StringProperty(
        name="Tangent Semantic",
        description="MESH tangent semantic - can be 'uvw' or 'tangent'",
        maxlen=16,
        default=CONFIG['tangentSemantic'])
    EX_tangentUseParity = IntProperty(
        name="Tangent Parity",
        description="MESH tangent use parity",
        min=0, max=16,
        default=CONFIG['tangentUseParity'])
    EX_tangentSplitMirrored = BoolProperty(
        name="Tangent Split Mirrored",
        description="MESH split mirrored tangents",
        default=CONFIG['tangentSplitMirrored'])
    EX_tangentSplitRotated = BoolProperty(
        name="Tangent Split Rotated",
        description="MESH split rotated tangents",
        default=CONFIG['tangentSplitRotated'])
    EX_reorganiseBuffers = BoolProperty(
        name="Reorganise Buffers",
        description="MESH reorganise vertex buffers",
        default=CONFIG['reorganiseBuffers'])
    EX_optimiseAnimations = BoolProperty(
        name="Optimize Animations",
        description="MESH optimize animations",
        default=CONFIG['optimiseAnimations'])
    EX_COPY_SHADER_PROGRAMS = BoolProperty(
        name="copy shader programs",
        description="when using script inheritance copy the source shader programs to the output path",
        default=CONFIG['COPY_SHADER_PROGRAMS'])

    filepath_last = ""
    filepath = StringProperty(
        name="File Path",
        description="Filepath used for exporting file",
        maxlen=1024, default="",
        subtype='FILE_PATH')

    EX_SEP_MATS = BoolProperty(
        name="Separate Materials",
        description="exports a .material for each material (rather than putting all materials in a single .material file)",
        default=CONFIG['SEP_MATS'])
    EX_ONLY_DEFORMABLE_BONES = BoolProperty(
        name="Only Deformable Bones",
        description="only exports bones that are deformable. Useful for hiding IK-Bones used in Blender. Note: Any bone with deformable children/descendants will be output as well.",
        default=CONFIG['ONLY_DEFORMABLE_BONES'])
    EX_ONLY_KEYFRAMED_BONES = BoolProperty(
        name="Only Keyframed Bones",
        description="only exports bones that have been keyframed for a given animation. Useful to limit the set of bones on a per-animation basis.",
        default=CONFIG['ONLY_KEYFRAMED_BONES'])
    EX_OGRE_INHERIT_SCALE = BoolProperty(
        name="OGRE inherit scale",
        description="whether the OGRE bones have the 'inherit scale' flag on.  If the animation has scale in it, the exported animation needs to be adjusted to account for the state of the inherit-scale flag in OGRE.",
        default=CONFIG['OGRE_INHERIT_SCALE'])
    EX_SCENE = BoolProperty(
        name="Export Scene",
        description="export current scene (OgreDotScene xml)",
        default=CONFIG['SCENE'])
    EX_SELONLY = BoolProperty(
        name="Export Selected Only",
        description="export selected",
        default=CONFIG['SELONLY'])
    EX_EXPORT_HIDDEN = BoolProperty(
        name="Export Hidden Also",
        description="Export hidden meshes in addition to visible ones. Turn off to avoid exporting hidden stuff.",
        default=CONFIG['EXPORT_HIDDEN'])
    EX_FORCE_CAMERA = BoolProperty(
        name="Force Camera",
        description="export active camera",
        default=CONFIG['FORCE_CAMERA'])
    EX_FORCE_LAMPS = BoolProperty(
        name="Force Lamps",
        description="export all lamps",
        default=CONFIG['FORCE_LAMPS'])
    EX_MESH = BoolProperty(
        name="Export Meshes",
        description="export meshes",
        default=CONFIG['MESH'])
    EX_MESH_OVERWRITE = BoolProperty(
        name="Export Meshes (overwrite)",
        description="export meshes (overwrite existing files)",
        default=CONFIG['MESH_OVERWRITE'])
    EX_ARM_ANIM = BoolProperty(
        name="Armature Animation",
        description="export armature animations - updates the .skeleton file",
        default=CONFIG['ARM_ANIM'])
    EX_SHAPE_ANIM = BoolProperty(
        name="Shape Animation",
        description="export shape animations - updates the .mesh file",
        default=CONFIG['SHAPE_ANIM'])
    EX_TRIM_BONE_WEIGHTS = FloatProperty(
        name="Trim Weights",
        description="ignore bone weights below this value (Ogre supports 4 bones per vertex)",
        min=0.0, max=0.5, default=CONFIG['TRIM_BONE_WEIGHTS'] )
    EX_ARRAY = BoolProperty(
        name="Optimize Arrays",
        description="optimize array modifiers as instances (constant offset only)",
        default=CONFIG['ARRAY'])
    EX_MATERIALS = BoolProperty(
        name="Export Materials",
        description="exports .material script",
        default=CONFIG['MATERIALS'])
    EX_FORCE_IMAGE_FORMAT = EnumProperty(
        items=IMAGE_FORMATS,
        name='Convert Images',
        description='convert all textures to format',
        default=CONFIG['FORCE_IMAGE_FORMAT'] )
    EX_DDS_MIPS = IntProperty(
        name="DDS Mips",
        description="number of mip maps (DDS)",
        min=0, max=16,
        default=CONFIG['DDS_MIPS'])

    # Mesh options
    EX_lodLevels = IntProperty(
        name="LOD Levels",
        description="MESH number of LOD levels",
        min=0, max=32,
        default=CONFIG['lodLevels'])
    EX_lodDistance = IntProperty(
        name="LOD Distance",
        description="MESH distance increment to reduce LOD",
        min=0, max=2000,
        default=CONFIG['lodDistance'])
    EX_lodPercent = IntProperty(
        name="LOD Percentage",
        description="LOD percentage reduction",
        min=0, max=99,
        default=CONFIG['lodPercent'])
    EX_nuextremityPoints = IntProperty(
        name="Extremity Points",
        description="MESH Extremity Points",
        min=0, max=65536,
        default=CONFIG['nuextremityPoints'])
    EX_generateEdgeLists = BoolProperty(
        name="Edge Lists",
        description="MESH generate edge lists (for stencil shadows)",
        default=CONFIG['generateEdgeLists'])
    EX_generateTangents = BoolProperty(
        name="Tangents",
        description="MESH generate tangents",
        default=CONFIG['generateTangents'])
    EX_tangentSemantic = StringProperty(
        name="Tangent Semantic",
        description="MESH tangent semantic",
        maxlen=16,
        default=CONFIG['tangentSemantic'])
    EX_tangentUseParity = IntProperty(
        name="Tangent Parity",
        description="MESH tangent use parity",
        min=0, max=16,
        default=CONFIG['tangentUseParity'])
    EX_tangentSplitMirrored = BoolProperty(
        name="Tangent Split Mirrored",
        description="MESH split mirrored tangents",
        default=CONFIG['tangentSplitMirrored'])
    EX_tangentSplitRotated = BoolProperty(
        name="Tangent Split Rotated",
        description="MESH split rotated tangents",
        default=CONFIG['tangentSplitRotated'])
    EX_reorganiseBuffers = BoolProperty(
        name="Reorganise Buffers",
        description="MESH reorganise vertex buffers",
        default=CONFIG['reorganiseBuffers'])
    EX_optimiseAnimations = BoolProperty(
        name="Optimize Animations",
        description="MESH optimize animations",
        default=CONFIG['optimiseAnimations'])

    filepath= StringProperty(
        name="File Path",
        description="Filepath used for exporting Ogre .scene file",
        maxlen=1024,
        default="",
        subtype='FILE_PATH')

    def dot_material( self, meshes, path='/tmp', mat_file_name='SceneMaterial'):
        material_files = []
        mats = []
        for ob in meshes:
            if len(ob.data.materials):
                for mat in ob.data.materials:
                    if mat not in mats:
                        mats.append( mat )

        if not mats:
            print('WARNING: no materials, not writting .material script'); return []

        M = MISSING_MATERIAL + '\n'
        for mat in mats:
            if mat is None:
                continue
            Report.materials.append( material_name(mat) )
            if CONFIG['COPY_SHADER_PROGRAMS']:
                data = generate_material( mat, path=path, copy_programs=True, touch_textures=CONFIG['TOUCH_TEXTURES'] )
            else:
                data = generate_material( mat, path=path, touch_textures=CONFIG['TOUCH_TEXTURES'] )

            M += data
            # Write own .material file per material
            if self.EX_SEP_MATS:
                url = self.dot_material_write_separate( mat, data, path )
                material_files.append(url)

        # Write one .material file for everything
        if not self.EX_SEP_MATS:
            try:
                url = os.path.join(path, '%s.material' % mat_file_name)
                f = open( url, 'wb' ); f.write( bytes(M,'utf-8') ); f.close()
                print('    - Created material:', url)
                material_files.append( url )
            except Exception as e:
                show_dialog("Invalid material object name: " + mat_file_name)

        return material_files

    def dot_material_write_separate( self, mat, data, path = '/tmp' ):
        try:
            clean_filename = clean_object_name(mat.name);
            url = os.path.join(path, '%s.material' % clean_filename)
            f = open(url, 'wb'); f.write( bytes(data,'utf-8') ); f.close()
            print('    - Exported Material:', url)
            return url
        except Exception as e:
            show_dialog("Invalid material object name: " + clean_filename)
            return ""

    def dot_mesh( self, ob, path='/tmp', force_name=None, ignore_shape_animation=False ):
        dot_mesh( ob, path, force_name, ignore_shape_animation=False )

    def ogre_export(self, url, context, force_material_update=[]):
        print ("_"*80)

        # Updating config to latest values?
        global CONFIG
        for name in dir(self):
            if name.startswith('EX_'):
                CONFIG[ name[3:] ] = getattr(self,name)

        Report.reset()

        print("Processing Scene")
        prefix = url.split('.')[0]
        path = os.path.split(url)[0]

        # Nodes (objects) - gather because macros will change selection state
        objects = []
        linkedgroups = []
        invalidnamewarnings = []
        for ob in bpy.context.scene.objects:
            if ob.subcollision:
                continue
            if not self.EX_EXPORT_HIDDEN and ob.hide:
                continue
            if self.EX_SELONLY and not ob.select:
                if ob.type == 'CAMERA' and self.EX_FORCE_CAMERA:
                    pass
                elif ob.type == 'LAMP' and self.EX_FORCE_LAMPS:
                    pass
                else:
                    continue
            if ob.type == 'EMPTY' and ob.dupli_group and ob.dupli_type == 'GROUP':
                linkedgroups.append(ob)
            else:
                # Gather data of invalid names. Don't bother user with warnings on names
                # that only get spaces converted to _, just do that automatically.
                cleanname = clean_object_name(ob.name)
                cleannamespaces = clean_object_name_with_spaces(ob.name)
                if cleanname != ob.name:
                    if cleannamespaces != ob.name:
                        invalidnamewarnings.append(ob.name + " -> " + cleanname)
                objects.append(ob)

        # Print invalid obj names so user can go and fix them.
        if len(invalidnamewarnings) > 0:
            print ("[Warning]: Following object names have invalid characters for creating files. They will be automatically converted.")
            for namewarning in invalidnamewarnings:
                Report.warnings.append("Auto correcting object name: " + namewarning)
                print ("  - ", namewarning)

        # Linked groups - allows 3 levels of nested blender library linking
        temps = []
        for e in linkedgroups:
            grp = e.dupli_group
            subs = []
            for o in grp.objects:
                if o.type=='MESH':
                    subs.append( o )     # TOP-LEVEL
                elif o.type == 'EMPTY' and o.dupli_group and o.dupli_type == 'GROUP':
                    ss = []     # LEVEL2
                    for oo in o.dupli_group.objects:
                        if oo.type=='MESH':
                            ss.append( oo )
                        elif oo.type == 'EMPTY' and oo.dupli_group and oo.dupli_type == 'GROUP':
                            sss = []    # LEVEL3
                            for ooo in oo.dupli_group.objects:
                                if ooo.type=='MESH':
                                    sss.append( ooo )
                            if sss:
                                m = merge_objects( sss, name=oo.name, transform=oo.matrix_world )
                                subs.append( m )
                                temps.append( m )
                    if ss:
                        m = merge_objects( ss, name=o.name, transform=o.matrix_world )
                        subs.append( m )
                        temps.append( m )
            if subs:
                m = merge_objects( subs, name=e.name, transform=e.matrix_world )
                objects.append( m )
                temps.append( m )

        # Find merge groups
        mgroups = []
        mobjects = []
        for ob in objects:
            group = get_merge_group( ob )
            if group:
                for member in group.objects:
                    if member not in mobjects: mobjects.append( member )
                if group not in mgroups: mgroups.append( group )
        for rem in mobjects:
            if rem in objects: objects.remove( rem )

        for group in mgroups:
            merged = merge_group( group )
            objects.append( merged )
            temps.append( merged )

        # Gather roots because ogredotscene supports parents and children
        def _flatten( _c, _f ):
            if _c.parent in objects: _f.append( _c.parent )
            if _c.parent: _flatten( _c.parent, _f )
            else: _f.append( _c )

        roots = []
        meshes = []

        for ob in objects:
            flat = []
            _flatten( ob, flat )
            root = flat[-1]
            if root not in roots:
                roots.append(root)
            if ob.type=='MESH':
                meshes.append(ob)

        mesh_collision_prims = {}
        mesh_collision_files = {}

        # Track that we don't export same data multiple times
        exported_meshes = []

        if self.EX_MATERIALS:
            print ("  Processing Materials")
            material_file_name_base = os.path.split(url)[1].replace('.scene', '').replace('.txml', '')
            material_files = self.dot_material(meshes + force_material_update, path, material_file_name_base)
        else:
            material_files = []

        # realXtend Tundra .txml scene description export
        # TODO re enable this export type
        #if self.EXPORT_TYPE == 'REX':
        #    rex = self.create_tundra_document(context)
        #    proxies = []
        #    for ob in objects:
        #        print("  Processing %s [%s]" % (ob.name, ob.type))

        #        # This seemingly needs to be done as its done in .scene
        #        # export. Fixed a bug that no .meshes were exported when doing
        #        # a Tundra export.
        #        if ob.type == 'MESH':
        #            ob.data.update(calc_tessface=True)

        #        # EC_Light
        #        if ob.type == 'LAMP':
        #            TE = self.tundra_entity(rex, ob, path=path, collision_proxies=proxies)
        #            self.tundra_light( TE, ob )
        #        # EC_Sound
        #        elif ob.type == 'SPEAKER':
        #            TE = self.tundra_entity(rex, ob, path=path, collision_proxies=proxies)
        #        # EC_Mesh
        #        elif ob.type == 'MESH' and len(ob.data.tessfaces):
        #            if ob.modifiers and ob.modifiers[0].type=='MULTIRES' and ob.use_multires_lod:
        #                mod = ob.modifiers[0]
        #                basename = ob.name
        #                dataname = ob.data.name
        #                ID = uid( ob ) # ensure uid
        #                TE = self.tundra_entity(rex, ob, path=path, collision_proxies=proxies)

        #                for level in range( mod.total_levels+1 ):
        #                    ob.uid += 1
        #                    mod.levels = level
        #                    ob.name = '%s.LOD%s' %(basename,level)
        #                    ob.data.name = '%s.LOD%s' %(dataname,level)
        #                    TE = self.tundra_entity(
        #                        rex, ob, path=path, collision_proxies=proxies, parent=basename,
        #                        matrix=mathutils.Matrix(), visible=False
        #                    )
        #                    self.tundra_mesh( TE, ob, url, exported_meshes )

        #                ob.uid = ID
        #                ob.name = basename
        #                ob.data.name = dataname
        #            else:
        #                TE = self.tundra_entity( rex, ob, path=path, collision_proxies=proxies )
        #                self.tundra_mesh( TE, ob, url, exported_meshes )

        #    # EC_RigidBody separate collision meshes
        #    for proxy in proxies:
        #        self.dot_mesh(
        #            proxy,
        #            path=os.path.split(url)[0],
        #            force_name='_collision_%s' %proxy.data.name
        #        )

        #    if self.EX_SCENE:
        #        if not url.endswith('.txml'):
        #            url += '.txml'
        #        data = rex.toprettyxml()
        #        f = open( url, 'wb' ); f.write( bytes(data,'utf-8') ); f.close()
        #        print('  Exported Tundra Scene:', url)

        # Ogre .scene scene description export
        if self.EXPORT_TYPE == 'OGRE':
            doc = self.create_ogre_document( context, material_files )

            for root in roots:
                print('      - Exporting root node:', root.name)
                self._node_export(
                    root,
                    url = url,
                    doc = doc,
                    exported_meshes = exported_meshes,
                    meshes = meshes,
                    mesh_collision_prims = mesh_collision_prims,
                    mesh_collision_files = mesh_collision_files,
                    prefix = prefix,
                    objects = objects,
                    xmlparent = doc._scene_nodes
                )

            if self.EX_SCENE:
                if not url.endswith('.scene'):
                    url += '.scene'
                data = doc.toprettyxml()
                f = open( url, 'wb' ); f.write( bytes(data,'utf-8') ); f.close()
                print('  Exported Ogre Scene:', url)

        for ob in temps:
            context.scene.objects.unlink( ob )
        Report.show()

        # Always save?
        # todo: This does not seem to stick! It might save to disk
        # but the old config defaults are read when this panel is opened!
        config.save_config()

    def create_ogre_document(self, context, material_files=[] ):
        now = time.time()
        doc = RDocument()
        scn = doc.createElement('scene'); doc.appendChild( scn )
        scn.setAttribute('export_time', str(now))
        scn.setAttribute('formatVersion', '1.0.1')
        bscn = bpy.context.scene

        if '_previous_export_time_' in bscn.keys():
            scn.setAttribute('previous_export_time', str(bscn['_previous_export_time_']))
        else:
            scn.setAttribute('previous_export_time', '0')
        bscn[ '_previous_export_time_' ] = now
        scn.setAttribute('exported_by', getpass.getuser())

        nodes = doc.createElement('nodes')
        doc._scene_nodes = nodes
        extern = doc.createElement('externals')
        environ = doc.createElement('environment')
        for n in (nodes,extern,environ):
            scn.appendChild( n )

        # Extern files
        for url in material_files:
            item = doc.createElement('item'); extern.appendChild( item )
            item.setAttribute('type','material')
            a = doc.createElement('file'); item.appendChild( a )
            a.setAttribute('name', url)

        # Environ settings
        world = context.scene.world
        if world: # multiple scenes - other scenes may not have a world
            _c = {'colourAmbient':world.ambient_color, 'colourBackground':world.horizon_color, 'colourDiffuse':world.horizon_color}
            for ctag in _c:
                a = doc.createElement(ctag); environ.appendChild( a )
                color = _c[ctag]
                a.setAttribute('r', '%s'%color.r)
                a.setAttribute('g', '%s'%color.g)
                a.setAttribute('b', '%s'%color.b)

        if world and world.mist_settings.use_mist:
            a = doc.createElement('fog'); environ.appendChild( a )
            a.setAttribute('linearStart', '%s'%world.mist_settings.start )
            mist_falloff = world.mist_settings.falloff
            if mist_falloff == 'QUADRATIC': a.setAttribute('mode', 'exp')    # on DTD spec (none | exp | exp2 | linear)
            elif mist_falloff == 'LINEAR': a.setAttribute('mode', 'linear')
            else: a.setAttribute('mode', 'exp2')
            #a.setAttribute('mode', world.mist_settings.falloff.lower() )    # not on DTD spec
            a.setAttribute('linearEnd', '%s' %(world.mist_settings.start+world.mist_settings.depth))
            a.setAttribute('expDensity', world.mist_settings.intensity)
            a.setAttribute('colourR', world.horizon_color.r)
            a.setAttribute('colourG', world.horizon_color.g)
            a.setAttribute('colourB', world.horizon_color.b)

        return doc

    # Recursive Node export
    def _node_export( self, ob, url='', doc=None, rex=None, exported_meshes=[], meshes=[], mesh_collision_prims={}, mesh_collision_files={}, prefix='', objects=[], xmlparent=None ):
        o = _ogre_node_helper( doc, ob, objects )
        xmlparent.appendChild(o)

        # Custom user props
        for prop in ob.items():
            propname, propvalue = prop
            if not propname.startswith('_'):
                user = doc.createElement('user_data')
                o.appendChild( user )
                user.setAttribute( 'name', propname )
                user.setAttribute( 'value', str(propvalue) )
                user.setAttribute( 'type', type(propvalue).__name__ )

        # Custom user props from BGE props by Mind Calamity
        for prop in ob.game.properties:
            e = doc.createElement( 'user_data' )
            o.appendChild( e )
            e.setAttribute('name', prop.name)
            e.setAttribute('value', str(prop.value))
            e.setAttribute('type', type(prop.value).__name__)
        # -- end of Mind Calamity patch

        # BGE subset
        game = doc.createElement('game')
        o.appendChild( game )
        sens = doc.createElement('sensors')
        game.appendChild( sens )
        acts = doc.createElement('actuators')
        game.appendChild( acts )
        for sen in ob.game.sensors:
            sens.appendChild( WrapSensor(sen).xml(doc) )
        for act in ob.game.actuators:
            acts.appendChild( WrapActuator(act).xml(doc) )

        if ob.type == 'MESH':
            ob.data.update(calc_tessface=True)

        if ob.type == 'MESH' and len(ob.data.tessfaces):
            collisionFile = None
            collisionPrim = None
            if ob.data.name in mesh_collision_prims:
                collisionPrim = mesh_collision_prims[ ob.data.name ]
            if ob.data.name in mesh_collision_files:
                collisionFile = mesh_collision_files[ ob.data.name ]

            e = doc.createElement('entity')
            o.appendChild(e); e.setAttribute('name', ob.data.name)
            prefix = ''
            e.setAttribute('meshFile', '%s%s.mesh' %(prefix,ob.data.name) )

            if not collisionPrim and not collisionFile:
                if ob.game.use_collision_bounds:
                    collisionPrim = ob.game.collision_bounds_type.lower()
                    mesh_collision_prims[ ob.data.name ] = collisionPrim
                else:
                    for child in ob.children:
                        if child.subcollision and child.name.startswith('DECIMATE'):
                            collisionFile = '%s_collision_%s.mesh' %(prefix,ob.data.name)
                            break
                    if collisionFile:
                        mesh_collision_files[ ob.data.name ] = collisionFile
                        self.dot_mesh(
                            child,
                            path=os.path.split(url)[0],
                            force_name='_collision_%s' %ob.data.name
                        )

            if collisionPrim:
                e.setAttribute('collisionPrim', collisionPrim )
            elif collisionFile:
                e.setAttribute('collisionFile', collisionFile )

            _mesh_entity_helper( doc, ob, e )

            if self.EX_MESH:
                murl = os.path.join( os.path.split(url)[0], '%s.mesh'%ob.data.name )
                exists = os.path.isfile( murl )
                if not exists or (exists and self.EX_MESH_OVERWRITE):
                    if ob.data.name not in exported_meshes:
                        exported_meshes.append( ob.data.name )
                        self.dot_mesh( ob, os.path.split(url)[0] )

            # Deal with Array modifier
            vecs = [ ob.matrix_world.to_translation() ]
            for mod in ob.modifiers:
                if mod.type == 'ARRAY':
                    if mod.fit_type != 'FIXED_COUNT':
                        print( 'WARNING: unsupport array-modifier type->', mod.fit_type )
                        continue
                    if not mod.use_constant_offset:
                        print( 'WARNING: unsupport array-modifier mode, must be "constant offset" type' )
                        continue
                    else:
                        #v = ob.matrix_world.to_translation()
                        newvecs = []
                        for prev in vecs:
                            for i in range( mod.count-1 ):
                                v = prev + mod.constant_offset_displace
                                newvecs.append( v )
                                ao = _ogre_node_helper( doc, ob, objects, prefix='_array_%s_'%len(vecs+newvecs), pos=v )
                                xmlparent.appendChild(ao)

                                e = doc.createElement('entity')
                                ao.appendChild(e); e.setAttribute('name', ob.data.name)
                                #if self.EX_MESH_SUBDIR: e.setAttribute('meshFile', 'meshes/%s.mesh' %ob.data.name)
                                #else:
                                e.setAttribute('meshFile', '%s.mesh' %ob.data.name)

                                if collisionPrim: e.setAttribute('collisionPrim', collisionPrim )
                                elif collisionFile: e.setAttribute('collisionFile', collisionFile )
                        vecs += newvecs

        elif ob.type == 'CAMERA':
            Report.cameras.append( ob.name )
            c = doc.createElement('camera')
            o.appendChild(c); c.setAttribute('name', ob.data.name)
            aspx = bpy.context.scene.render.pixel_aspect_x
            aspy = bpy.context.scene.render.pixel_aspect_y
            sx = bpy.context.scene.render.resolution_x
            sy = bpy.context.scene.render.resolution_y
            fovY = 0.0
            if (sx*aspx > sy*aspy):
                fovY = 2*math.atan(sy*aspy*16.0/(ob.data.lens*sx*aspx))
            else:
                fovY = 2*math.atan(16.0/ob.data.lens)
            # fov in radians - like OgreMax - requested by cyrfer
            fov = math.radians( fovY*180.0/math.pi )
            c.setAttribute('fov', '%s'%fov)
            c.setAttribute('projectionType', "perspective")
            a = doc.createElement('clipping'); c.appendChild( a )
            a.setAttribute('nearPlaneDist', '%s' %ob.data.clip_start)
            a.setAttribute('farPlaneDist', '%s' %ob.data.clip_end)
            a.setAttribute('near', '%s' %ob.data.clip_start)    # requested by cyrfer
            a.setAttribute('far', '%s' %ob.data.clip_end)

        elif ob.type == 'LAMP' and ob.data.type in 'POINT SPOT SUN'.split():
            Report.lights.append( ob.name )
            l = doc.createElement('light')
            o.appendChild(l)

            mat = get_parent_matrix(ob, objects).inverted() * ob.matrix_world

            p = doc.createElement('position')   # just to make sure we conform with the DTD
            l.appendChild(p)
            v = swap( ob.matrix_world.to_translation() )
            p.setAttribute('x', '%6f'%v.x)
            p.setAttribute('y', '%6f'%v.y)
            p.setAttribute('z', '%6f'%v.z)

            if ob.data.type == 'POINT':
                l.setAttribute('type', 'point')
            elif ob.data.type == 'SPOT':
                l.setAttribute('type', 'spot')
            elif ob.data.type == 'SUN':
                l.setAttribute('type', 'directional')

            l.setAttribute('name', ob.name )
            l.setAttribute('powerScale', str(ob.data.energy))

            a = doc.createElement('lightAttenuation'); l.appendChild( a )
            a.setAttribute('range', '5000' )            # is this an Ogre constant?
            a.setAttribute('constant', '1.0')        # TODO support quadratic light
            a.setAttribute('linear', '%s'%(1.0/ob.data.distance))
            a.setAttribute('quadratic', '0.0')

            if ob.data.type in ('SPOT', 'SUN'):
                vector = swap(mathutils.Euler.to_matrix(ob.rotation_euler)[2])
                a = doc.createElement('direction')
                l.appendChild(a)
                a.setAttribute('x',str(round(-vector[0],3)))
                a.setAttribute('y',str(round(-vector[1],3)))
                a.setAttribute('z',str(round(-vector[2],3)))

            if ob.data.type == 'SPOT':
                a = doc.createElement('spotLightRange')
                l.appendChild(a)
                a.setAttribute('inner',str( ob.data.spot_size*(1.0-ob.data.spot_blend) ))
                a.setAttribute('outer',str(ob.data.spot_size))
                a.setAttribute('falloff','1.0')

            if ob.data.use_diffuse:
                a = doc.createElement('colourDiffuse'); l.appendChild( a )
                a.setAttribute('r', '%s'%ob.data.color.r)
                a.setAttribute('g', '%s'%ob.data.color.g)
                a.setAttribute('b', '%s'%ob.data.color.b)

            if ob.data.use_specular:
                a = doc.createElement('colourSpecular'); l.appendChild( a )
                a.setAttribute('r', '%s'%ob.data.color.r)
                a.setAttribute('g', '%s'%ob.data.color.g)
                a.setAttribute('b', '%s'%ob.data.color.b)

            if ob.data.type != 'HEMI':  # colourShadow is extra, not part of Ogre DTD
                if ob.data.shadow_method != 'NOSHADOW': # Hemi light has no shadow_method
                    a = doc.createElement('colourShadow');l.appendChild( a )
                    a.setAttribute('r', '%s'%ob.data.color.r)
                    a.setAttribute('g', '%s'%ob.data.color.g)
                    a.setAttribute('b', '%s'%ob.data.color.b)
                    l.setAttribute('shadow','true')

        for child in ob.children:
            self._node_export( child,
                url = url, doc = doc, rex = rex,
                exported_meshes = exported_meshes,
                meshes = meshes,
                mesh_collision_prims = mesh_collision_prims,
                mesh_collision_files = mesh_collision_files,
                prefix = prefix,
                objects=objects,
                xmlparent=o
            )

