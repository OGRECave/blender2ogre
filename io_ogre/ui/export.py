
import bpy
import os
import getpass
import math
import mathutils
import logging

from pprint import pprint

from bpy.props import EnumProperty, BoolProperty, FloatProperty, StringProperty, IntProperty
from .. import config
from ..report import Report
from ..util import *
from ..xml import *
from ..ogre import mesh
from ..ogre import skeleton
from ..ogre import scene
from ..ogre import material

logger = logging.getLogger('root')

def auto_register(register):
    yield OP_ogre_export

    if register:
        bpy.types.TOPBAR_MT_file_export.append(menu_func)
    else:
        bpy.types.TOPBAR_MT_file_export.remove(menu_func)



def menu_func(self, context):
    """ invoked when export in drop down menu is clicked """
    op = self.layout.operator(OP_ogre_export.bl_idname, text="Ogre3D (.scene and .mesh)")
    return op

class _OgreCommonExport_(object):

    last_export_path = None

    @classmethod
    def poll(cls, context):
        if context.active_object and context.mode != 'EDIT_MESH':
            return True

    def __init__(self):
        # check that converter is setup
        self.converter = detect_converter_type()

    def invoke(self, context, event):

        # update the interface with the config values
        for key, value in config.CONFIG.items():
            if getattr(self, "EX_" + key, None) or getattr(self, "EX_Vx_" + key, None) or getattr(self, "EX_V1_" + key, None) or getattr(self, "EX_V2_" + key, None):
                # todo: isn't the key missing the "EX_" prefix?
                setattr(self,key,value)

        wm = context.window_manager
        fs = wm.fileselect_add(self)

        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout

        if self.converter == "unknown":
            layout.label(text="No converter found! Please check your preferences.", icon='ERROR')
        else:
            layout.label(text="Using '%s'" % self.converter, icon='INFO')

        for key in dir(_OgreCommonExport_):
            if key.startswith('EX_V1_'):
                if self.converter == "OgreXMLConverter":
                    layout.prop(self, key)
            elif key.startswith('EX_V2_'):
                if self.converter == "OgreMeshTool":
                    layout.prop(self, key)
            elif key.startswith('EX_Vx_'):
                if self.converter != "unknown":
                    layout.prop(self, key)
            elif key.startswith('EX_'):
                layout.prop(self, key)

    def execute(self, context):
        # add warinng about missing XML converter
        Report.reset()
        if self.converter == "unknown":
            Report.errors.append(
              "Cannot find suitable OgreXMLConverter or OgreMeshTool executable." +
              "Export XML mesh - do NOT automatically convert .xml to .mesh file. You MUST run converter mesh manually.")

        logger.info("context.blend_data %s"%context.blend_data.filepath)
        logger.info("context.scene.name %s"%context.scene.name)
        logger.info("self.filepath %s"%self.filepath)
        logger.info("self.last_export_path %s"%self.last_export_path)


        #-- load addonPreferenc in CONFIG
        config.update_from_addon_preference(context)

        # Resolve path from opened .blend if available. It's not if
        # blender normally was opened with "last open scene".
        # After export is done once, remember that path when re-exporting.
        if not self.last_export_path:
            # First export during this blender run
            if context.blend_data.filepath != "":
                path, name = os.path.split(context.blend_data.filepath)
                self.last_export_path = os.path.join(path, name.split('.')[0])

        if not self.last_export_path:
            self.last_export_path = os.path.expanduser("~")

        if self.filepath == "" or not self.filepath:
            self.filepath = "blender2ogre"

        logger.info("self.filepath %s"%self.filepath)

        kw = {}
        for name in dir(_OgreCommonExport_):
            if name[:6] in ('EX_V1_', 'EX_V2_', 'EX_Vx_'):
                kw[ name[6:] ] = getattr(self,name)
            elif name.startswith('EX_'):
                kw[ name[3:] ] = getattr(self,name)
        config.update(**kw)

        print ("_"*80)
        target_path, target_file_name = os.path.split(os.path.abspath(self.filepath))
        target_file_name = clean_object_name(target_file_name)
        target_file_name_no_ext = os.path.splitext(target_file_name)[0]

        logger.info("target_path %s"%target_path)
        logger.info("target_file_name %s"%target_file_name)
        logger.info("target_file_name_no_ext %s"%target_file_name_no_ext)

        scene.dot_scene(target_path, target_file_name_no_ext)
        Report.show()

        return {'FINISHED'}

    filepath = StringProperty(name="File Path",
        description="Filepath used for exporting Ogre .scene file",
        maxlen=1024,
        default="",
        subtype='FILE_PATH')

    # Basic options
    # NOTE config values are automatically propagated if you name it like: EX_<config-name>
    # Properties can also be enabled for a specific converter by adding V1 or V2 in the name:
    # EX_V1_<config-name> for OgreXMLConverter
    # EX_V2_<config-name> for OgreMeshTool
    # EX_Vx_<config-name> for OgreXMLConverter and OgreMeshTool (hide only when no converter found)
    EX_SWAP_AXIS = EnumProperty(
        items=config.AXIS_MODES,
        name='Swap Axis',
        description='axis swapping mode',
        default= config.get('SWAP_AXIS'))
    EX_SEP_MATS = BoolProperty(
        name="Separate Materials",
        description="exports a .material for each material (rather than putting all materials in a single .material file)",
        default=config.get('SEP_MATS'))
    EX_ONLY_DEFORMABLE_BONES = BoolProperty(
        name="Only Deformable Bones",
        description="only exports bones that are deformable. Useful for hiding IK-Bones used in Blender. Note: Any bone with deformable children/descendants will be output as well",
        default=config.get('ONLY_DEFORMABLE_BONES'))
    EX_ONLY_KEYFRAMED_BONES = BoolProperty(
        name="Only Keyframed Bones",
        description="only exports bones that have been keyframed for a given animation. Useful to limit the set of bones on a per-animation basis",
        default=config.get('ONLY_KEYFRAMED_BONES'))
    EX_OGRE_INHERIT_SCALE = BoolProperty(
        name="OGRE Inherit Scale",
        description="whether the OGRE bones have the 'inherit scale' flag on.  If the animation has scale in it, the exported animation needs to be adjusted to account for the state of the inherit-scale flag in OGRE",
        default=config.get('OGRE_INHERIT_SCALE'))
    EX_SCENE = BoolProperty(
        name="Export Scene",
        description="export current scene (OgreDotScene xml)",
        default=config.get('SCENE'))
    EX_SELONLY = BoolProperty(
        name="Export Selected Only",
        description="export selected",
        default=config.get('SELONLY'))
    EX_EXPORT_HIDDEN = BoolProperty(
        name="Export Hidden Also",
        description="Export hidden meshes in addition to visible ones. Turn off to avoid exporting hidden stuff",
        default=config.get('EXPORT_HIDDEN'))
    EX_FORCE_CAMERA = BoolProperty(
        name="Force Camera",
        description="export active camera",
        default=config.get('FORCE_CAMERA'))
    EX_FORCE_LAMPS = BoolProperty(
        name="Force Lamps",
        description="export all lamps",
        default=config.get('FORCE_LAMPS'))
    EX_MESH = BoolProperty(
        name="Export Meshes",
        description="export meshes",
        default=config.get('MESH'))
    EX_MESH_OVERWRITE = BoolProperty(
        name="Export Meshes (overwrite)",
        description="export meshes (overwrite existing files)",
        default=config.get('MESH_OVERWRITE'))
    EX_ARM_ANIM = BoolProperty(
        name="Armature Animation",
        description="export armature animations - updates the .skeleton file",
        default=config.get('ARM_ANIM'))
    EX_SHAPE_ANIM = BoolProperty(
        name="Shape Animation",
        description="export shape animations - updates the .mesh file",
        default=config.get('SHAPE_ANIM'))
    EX_SHAPE_NORMALS = BoolProperty(
        name="Shape Normals",
        description="export normals in shape animations - updates the .mesh file",
        default=config.get('SHAPE_NORMALS'))
    EX_TRIM_BONE_WEIGHTS = FloatProperty(
        name="Trim Weights",
        description="ignore bone weights below this value (Ogre supports 4 bones per vertex)",
        min=0.0, max=0.5, default=config.get('TRIM_BONE_WEIGHTS') )
    EX_ARRAY = BoolProperty(
        name="Optimize Arrays",
        description="optimize array modifiers as instances (constant offset only)",
        default=config.get('ARRAY'))
    EX_MATERIALS = BoolProperty(
        name="Export Materials",
        description="exports .material script",
        default=config.get('MATERIALS'))
    EX_DDS_MIPS = IntProperty(
        name="DDS Mips",
        description="number of mip maps (DDS)",
        min=0, max=16,
        default=config.get('DDS_MIPS'))

    # Mesh options
    EX_lodLevels = IntProperty(
        name="LOD Levels",
        description="MESH number of LOD levels",
        min=0, max=32,
        default=config.get('lodLevels'))
    EX_lodDistance = IntProperty(
        name="LOD Distance",
        description="MESH distance increment to reduce LOD",
        min=0, max=2000, default=config.get('lodDistance'))
    EX_lodPercent = IntProperty(
        name="LOD Percentage",
        description="LOD percentage reduction",
        min=0, max=99,
        default=config.get('lodPercent'))
    EX_V1_nuextremityPoints = IntProperty(
        name="Extremity Points",
        description="MESH Extremity Points",
        min=0, max=65536,
        default=config.get('nuextremityPoints'))
    EX_Vx_generateEdgeLists = BoolProperty(
        name="Edge Lists",
        description="MESH generate edge lists (for stencil shadows)",
        default=config.get('generateEdgeLists'))
    EX_generateTangents = EnumProperty(
        items=config.TANGENT_MODES,
        name="Tangents",
        description="Export tangents generated by Blender",
        default=config.get('generateTangents'))
    EX_Vx_optimiseAnimations = BoolProperty(
        name="Optimize Animations",
        description="MESH optimize animations",
        default=config.get('optimiseAnimations'))
    EX_COPY_SHADER_PROGRAMS = BoolProperty(
        name="Copy Shader Programs",
        description="when using script inheritance copy the source shader programs to the output path",
        default=config.get('COPY_SHADER_PROGRAMS'))
    EX_FORCE_IMAGE_FORMAT = EnumProperty(
        items=material.IMAGE_FORMATS,
        name='Convert Images',
        description='convert all textures to format',
        default=config.get('FORCE_IMAGE_FORMAT') )

    EX_Vx_EXPORT_ENABLE_LOGGING = BoolProperty(
        name="Write Exporter Logs",
        description="Log file will be created in the output directory",
        default=config.get('EXPORT_ENABLE_LOGGING'))
    EX_V2_MESH_TOOL_EXPORT_VERSION = EnumProperty(
        items=config.MESH_EXPORT_VERSIONS,
        name='Mesh Export Version',
        description='Specify Ogre version format to write',
        default=config.get('MESH_TOOL_EXPORT_VERSION') )

    EX_V2_optimizeVertexBuffersForShaders = BoolProperty(
        name="Optimize Vertex Buffers For Shaders",
        description="MESH optimize vertex buffers for shaders.\nSee Vertex Buffers Options for more settings",
        default=config.get('optimizeVertexBuffersForShaders'))
    EX_V2_optimizeVertexBuffersForShadersOptions = StringProperty(
        name="Vertex Buffers Options",
        description="""Used when optimizing vertex buffers for shaders.
Available flags are:
p - converts POSITION to 16-bit floats.
q - converts normal tangent and bitangent (28-36 bytes) to QTangents (8 bytes).
u - converts UVs to 16-bit floats.
s - make shadow mapping passes have their own optimized buffers. Overrides existing ones if any.
S - strips the buffers for shadow mapping (consumes less space and memory)""",
        maxlen=5,
        default=config.get('optimizeVertexBuffersForShadersOptions'))

class OP_ogre_export(bpy.types.Operator, _OgreCommonExport_):
    '''Export Ogre Scene'''
    bl_idname = "ogre.export"
    bl_label = "Export Ogre"
    bl_options = {'REGISTER'}
    # export logic is contained in the subclass


