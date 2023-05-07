import bpy, os, getpass, math, mathutils, logging

from pprint import pprint

# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    # ...so we need to reload our submodule(s) using importlib
    import importlib
    if "config" in locals():
        importlib.reload(config)
    if "mesh" in locals():
        importlib.reload(mesh)
    if "skeleton" in locals():
        importlib.reload(skeleton)
    if "scene" in locals():
        importlib.reload(scene)
    if "material" in locals():
        importlib.reload(material)
    if "report" in locals():
        importlib.reload(report)

# This is only relevant on first run, on later reloads those modules
# are already in locals() and those statements do not do anything.
from bpy.props import EnumProperty, BoolProperty, FloatProperty, StringProperty, IntProperty
from .. import config
from ..ogre import material
from ..ogre import mesh
from ..ogre import scene
from ..ogre import skeleton
from ..report import Report
from ..util import *
from ..xml import *

logger = logging.getLogger('export')

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

    @classmethod
    def poll(cls, context):
        if context.active_object and context.mode != 'EDIT_MESH':
            return True

    def __init__(self):
        # Check that converter is setup
        self.converter = detect_converter_type()

    def invoke(self, context, event):
        # Update the interface with the config values
        for key, value in config.CONFIG.items():
            if getattr(self, "EX_" + key, None) or getattr(self, "EX_Vx_" + key, None) or getattr(self, "EX_V1_" + key, None) or getattr(self, "EX_V2_" + key, None):
                # todo: isn't the key missing the "EX_" prefix?
                setattr(self,key,value)

        if not self.filepath:
            blend_filepath = context.blend_data.filepath
            if not blend_filepath:
                blend_filepath = "blender2ogre"
            else:
                blend_filepath = os.path.splitext(blend_filepath)[0]

            self.filepath = blend_filepath + ".scene"

        logger.debug("Context.blend_data: %s" % context.blend_data.filepath)
        logger.debug("Context.scene.name: %s" % context.scene.name)
        logger.debug("Self.filepath: %s" % self.filepath)

        wm = context.window_manager
        fs = wm.fileselect_add(self)
        
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout

        if self.converter == "unknown":
            layout.label(text="No converter found! Please check your preferences.", icon='ERROR')
        else:
            layout.label(text="Using '%s'" % self.converter, icon='INFO')

        # The Sections are listed in an array to have them in this particular order
        sections = ["General", "Scene", "Materials", "Textures", "Armature", "Mesh", "LOD", "Shape Animation", "Logging"]
        
        # Icons to use for the sections
        section_icons = {
            "General" : "WORLD", "Scene" : "SCENE_DATA", 
            "Materials" : "MATERIAL", "Textures" : "TEXTURE", 
            "Armature" : "ARMATURE_DATA", "Mesh" : "MESH_DATA", "LOD" : "LATTICE_DATA", "Shape Animation" : "POSE_HLT", 
            "Logging" : "TEXT"
        }

        # Options associated with each section
        section_options = {
            "General" : ["EX_SWAP_AXIS", "EX_V2_MESH_TOOL_VERSION", "EX_XML_DELETE"],
            "Scene" : ["EX_SCENE", "EX_SELECTED_ONLY", "EX_EXPORT_HIDDEN", "EX_FORCE_CAMERA", "EX_FORCE_LAMPS", "EX_NODE_ANIMATION"],
            "Materials" : ["EX_MATERIALS", "EX_SEPARATE_MATERIALS", "EX_COPY_SHADER_PROGRAMS", "EX_USE_FFP_PARAMETERS"],
            "Textures" : ["EX_DDS_MIPS", "EX_FORCE_IMAGE_FORMAT"],
            "Armature" : ["EX_ARMATURE_ANIMATION", "EX_SHARED_ARMATURE", "EX_ONLY_KEYFRAMES", "EX_ONLY_DEFORMABLE_BONES", "EX_ONLY_KEYFRAMED_BONES", "EX_OGRE_INHERIT_SCALE", "EX_TRIM_BONE_WEIGHTS"],
            "Mesh" : ["EX_MESH", "EX_MESH_OVERWRITE", "EX_ARRAY", "EX_V1_EXTREMITY_POINTS", "EX_Vx_GENERATE_EDGE_LISTS", "EX_GENERATE_TANGENTS", "EX_Vx_OPTIMISE_ANIMATIONS", "EX_V2_OPTIMISE_VERTEX_BUFFERS", "EX_V2_OPTIMISE_VERTEX_BUFFERS_OPTIONS"],
            "LOD" : ["EX_LOD_LEVELS", "EX_LOD_DISTANCE", "EX_LOD_PERCENT", "EX_LOD_MESH_TOOLS"],
            "Shape Animation" : ["EX_SHAPE_ANIMATIONS", "EX_SHAPE_NORMALS"],
            "Logging" : ["EX_Vx_ENABLE_LOGGING", "EX_Vx_DEBUG_LOGGING"]
        }

        for section in sections:
            row = layout.row()
            box = row.box()
            box.label(text=section, icon=section_icons[section])
            for prop in section_options[section]:
                if prop.startswith('EX_V1_'):
                    if self.converter == "OgreXMLConverter":
                        box.prop(self, prop)
                elif prop.startswith('EX_V2_'):
                    if self.converter == "OgreMeshTool":
                        box.prop(self, prop)
                elif prop.startswith('EX_Vx_'):
                    if self.converter != "unknown":
                        box.prop(self, prop)
                elif prop.startswith('EX_'):
                    box.prop(self, prop)

    def execute(self, context):
        Report.reset()

        # Add warning about missing XML converter
        if self.converter == "unknown":
            Report.errors.append(
              "Cannot find suitable OgreXMLConverter or OgreMeshTool executable.\n" +
              "Exported XML mesh was NOT automatically converted to .mesh file.\n" + 
              "You MUST run the converter manually to create binary .mesh file.")

        # Load addonPreference in CONFIG
        config.update_from_addon_preference(context)

        kw = {}
        for name in dir(_OgreCommonExport_):
            if name.startswith('EX_V1_'):
                kw[ name[6:] ] = getattr(self,name)
            elif name.startswith('EX_V2_'):
                kw[ name[6:] ] = getattr(self,name)
            elif name.startswith('EX_Vx_'):
                kw[ name[6:] ] = getattr(self,name)
            elif name.startswith('EX_'):
                kw[ name[3:] ] = getattr(self,name)
        config.update(**kw)

        print ("_" * 80,"\n")

        target_path, target_file_name = os.path.split(os.path.abspath(self.filepath))
        target_file_name = clean_object_name(target_file_name)
        target_file_name_no_ext = os.path.splitext(target_file_name)[0]

        file_handler = None

        # Add a file handler to all Logger instances
        if config.get('ENABLE_LOGGING') == True:
            log_file = ("%s/blender2ogre.log" % target_path)
            logger.info("* Writing log file to: %s" % log_file)

            try:
                file_handler = logging.FileHandler(filename=log_file, mode='w', encoding='utf-8', delay=False)

                # Show the python file name from where each log message originated
                SHOW_LOG_NAME = False

                if SHOW_LOG_NAME:
                    file_formatter = logging.Formatter(fmt='%(asctime)s %(name)9s.py [%(levelname)5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
                else:
                    file_formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

                file_handler.setFormatter(file_formatter)

                if config.get('DEBUG_LOGGING') == True:
                    level = logging.DEBUG
                else:
                    level = logging.INFO

                for logger_name in logging.Logger.manager.loggerDict.keys():
                    logging.getLogger(logger_name).addHandler(file_handler)
                    logging.getLogger(logger_name).setLevel(level)
            except Exception as e:
                logger.warn("Unable to create log file: %s" % log_file)
                logger.warn(e)

        logger.info("* Target path: %s" % target_path)
        logger.info("* Target file name: %s" % target_file_name)
        logger.debug("* Target file name (no ext): %s" % target_file_name_no_ext)

        # https://blender.stackexchange.com/questions/45528/how-to-get-blenders-version-number-from-python
        logger.info("* Blender version: %s (%s; %s)" % (bpy.app.version_string, bpy.app.version_cycle, bpy.app.build_platform.decode('UTF-8')))
        logger.debug(" + Binary Path: %s" % bpy.app.binary_path)
        logger.debug(" + Build Date: %s %s" % (bpy.app.build_date.decode('UTF-8'), bpy.app.build_time.decode('UTF-8')))
        logger.debug(" + Build Hash: %s" % bpy.app.build_hash.decode('UTF-8'))
        logger.debug(" + Build Branch: %s" % bpy.app.build_branch.decode('UTF-8'))
        logger.debug(" + Build Platform: %s" % bpy.app.build_platform.decode('UTF-8'))

        # Start exporting the elements in the scene
        scene.dot_scene(target_path, target_file_name_no_ext)
        Report.show()

        # Flush and close all logging file handlers
        if config.get('ENABLE_LOGGING') == True and file_handler != None:
            for logger_name in logging.Logger.manager.loggerDict.keys():
                logging.getLogger(logger_name).handlers.clear()
            
            file_handler.flush()
            file_handler.close()

        return {'FINISHED'}

    filepath : StringProperty(name="File Path",
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

    # General
    EX_SWAP_AXIS : EnumProperty(
        items=config.AXIS_MODES,
        name='Swap Axis',
        description='Axis swapping mode',
        default=config.get('SWAP_AXIS')) = {}
    EX_V2_MESH_TOOL_VERSION : EnumProperty(
        items=config.MESH_TOOL_VERSIONS,
        name='Mesh Export Version',
        description='Specify Ogre version format to write',
        default=config.get('MESH_TOOL_VERSION')) = {}
    EX_XML_DELETE : BoolProperty(
        name="Clean up xml files",
        description="Remove the generated xml files after binary conversion. \n(The removal will only happen if OgreXMLConverter/OgreMeshTool finishes successfully)",
        default=config.get('XML_DELETE')) = {}
    
    # Scene
    EX_SCENE : BoolProperty(
        name="Export Scene",
        description="Export current scene (OgreDotScene xml file)",
        default=config.get('SCENE')) = {}
    EX_SELECTED_ONLY : BoolProperty(
        name="Export Selected Only",
        description="Export only selected objects\nTurn on to avoid exporting non-selected stuff",
        default=config.get('SELECTED_ONLY')) = {}
    EX_EXPORT_HIDDEN : BoolProperty(
        name="Export Hidden Also",
        description="Export hidden meshes in addition to visible ones.\nTurn off to avoid exporting hidden stuff",
        default=config.get('EXPORT_HIDDEN')) = {}
    #EX_EXPORT_USER : BoolProperty(
    #    name="Export User Properties",
    #    description="Export user properties such as as physical properties.\nTurn off to avoid exporting the user data",
    #    default=config.get('EXPORT_USER')) = {}
    EX_FORCE_CAMERA : BoolProperty(
        name="Force Camera",
        description="Export active camera",
        default=config.get('FORCE_CAMERA')) = {}
    EX_FORCE_LAMPS : BoolProperty(
        name="Force Lamps",
        description="Export all Lamps",
        default=config.get('FORCE_LAMPS')) = {}
    EX_NODE_ANIMATION : BoolProperty(
        name="Export Node Animations",
        description="Export Node Animations, these are animations of the objects properties like position, rotation and scale",
        default=config.get('NODE_ANIMATION')) = {}
#    EX_NODE_KEYFRAMES : BoolProperty(
#        name="Only write Node Keyframes",
#        description="""The default behaviour when exporting Node Animations is to write every keyframe.
#Select this option if you want to have more control of the Node Animation in your Ogre application
#Don't select this option if you have any fine tuning of the F-Curves in Blender, since they won't get exported.
#NOTE: Node Animations based on the 'Follow Path' constraint will most likely fail with this option set to True.""",
#        default=config.get('NODE_KEYFRAMES')) = {}
    
    # Materials
    EX_MATERIALS : BoolProperty(
        name="Export Materials",
        description="Exports .material scripts",
        default=config.get('MATERIALS')) = {}
    EX_SEPARATE_MATERIALS : BoolProperty(
        name="Separate Materials",
        description="Exports a .material file for each material\n(rather than putting all materials into a single .material file)",
        default=config.get('SEPARATE_MATERIALS')) = {}
    EX_COPY_SHADER_PROGRAMS : BoolProperty(
        name="Copy Shader Programs",
        description="When using script inheritance copy the source shader programs to the output path",
        default=config.get('COPY_SHADER_PROGRAMS')) = {}
    EX_USE_FFP_PARAMETERS : BoolProperty(
        name="Fixed Function Parameters",
        description="Convert material parameters to Blinn-Phong model",
        default=config.get('USE_FFP_PARAMETERS')) = {}

    # Textures
    EX_DDS_MIPS : IntProperty(
        name="DDS Mips",
        description="Number of Mip Maps (DDS)",
        min=0, max=16,
        default=config.get('DDS_MIPS')) = {}
    EX_FORCE_IMAGE_FORMAT : EnumProperty(
        items=material.IMAGE_FORMATS,
        name="Convert Images",
        description="Convert all textures to selected image format",
        default=config.get('FORCE_IMAGE_FORMAT')) = {}
    
    # Armature
    EX_ARMATURE_ANIMATION : BoolProperty(
        name="Armature Animation",
        description="Export armature animations (updates the .skeleton file)",
        default=config.get('ARMATURE_ANIMATION')) = {}
    EX_SHARED_ARMATURE : BoolProperty(
        name="Shared Armature",
        description="Export a single .skeleton file for objects that have the same Armature parent (useful for: shareSkeletonInstanceWith())\nNOTE: The name of the .skeleton file will be that of the Armature",
        default=config.get('SHARED_ARMATURE')) = {}
    EX_ONLY_KEYFRAMES : BoolProperty(
        name="Only Keyframes",
        description="Only export Keyframes.\nNOTE: Exported animation won't be affected by Inverse Kinematics, Drivers and modified F-Curves",
        default=config.get('ONLY_KEYFRAMES')) = {}
    EX_ONLY_DEFORMABLE_BONES : BoolProperty(
        name="Only Deformable Bones",
        description="Only exports bones that are deformable. Useful for hiding IK-Bones used in Blender.\nNOTE: Any bone with deformable children/descendants will be output as well",
        default=config.get('ONLY_DEFORMABLE_BONES')) = {}
    EX_ONLY_KEYFRAMED_BONES : BoolProperty(
        name="Only Keyframed Bones",
        description="Only exports bones that have been keyframed for a given animation.\nUseful to limit the set of bones on a per-animation basis",
        default=config.get('ONLY_KEYFRAMED_BONES')) = {}
    EX_OGRE_INHERIT_SCALE : BoolProperty(
        name="OGRE Inherit Scale",
        description="Whether the OGRE bones have the 'inherit scale' flag on.\nIf the animation has scale in it, the exported animation needs to be\nadjusted to account for the state of the inherit-scale flag in OGRE",
        default=config.get('OGRE_INHERIT_SCALE')) = {}
    EX_TRIM_BONE_WEIGHTS : FloatProperty(
        name="Trim Weights",
        description="Ignore bone weights below this value (Ogre supports 4 bones per vertex)",
        min=0.0, max=0.5,
        default=config.get('TRIM_BONE_WEIGHTS')) = {}

    # Mesh Options
    EX_MESH : BoolProperty(
        name="Export Meshes",
        description="Export meshes",
        default=config.get('MESH')) = {}
    EX_MESH_OVERWRITE : BoolProperty(
        name="Export Meshes (overwrite)",
        description="Export meshes (overwrite existing files)",
        default=config.get('MESH_OVERWRITE')) = {}
    EX_ARRAY : BoolProperty(
        name="Optimise Arrays",
        description="Optimise array modifiers as instances (constant offset only)",
        default=config.get('ARRAY')) = {}
    EX_V1_EXTREMITY_POINTS : IntProperty(
        name="Extremity Points",
        description="""Submeshes can have optional 'extremity points' stored with them to allow 
submeshes to be sorted with respect to each other in the case of transparency. 
For some meshes with transparent materials (partial transparency) this can be useful""",
        min=0, max=65536,
        default=config.get('EXTREMITY_POINTS')) = {}
    EX_Vx_GENERATE_EDGE_LISTS : BoolProperty(
        name="Generate Edge Lists",
        description="Generate Edge Lists (for Stencil Shadows)",
        default=config.get('GENERATE_EDGE_LISTS')) = {}
    EX_GENERATE_TANGENTS : EnumProperty(
        items=config.TANGENT_MODES,
        name="Tangents",
        description="Export tangents generated by Blender",
        default=config.get('GENERATE_TANGENTS')) = {}
    EX_Vx_OPTIMISE_ANIMATIONS : BoolProperty(
        name="Optimise Animations",
        description="DON'T optimise out redundant tracks & keyframes",
        default=config.get('OPTIMISE_ANIMATIONS')) = {}
    EX_V2_OPTIMISE_VERTEX_BUFFERS : BoolProperty(
        name="Optimise Vertex Buffers For Shaders",
        description="Optimise vertex buffers for shaders.\nSee Vertex Buffers Options for more settings",
        default=config.get('OPTIMISE_VERTEX_BUFFERS')) = {}
    EX_V2_OPTIMISE_VERTEX_BUFFERS_OPTIONS : StringProperty(
        name="Vertex Buffers Options",
        description="""Used when optimizing vertex buffers for shaders.
Available flags are:
p - converts POSITION to 16-bit floats.
q - converts normal tangent and bitangent (28-36 bytes) to QTangents (8 bytes).
u - converts UVs to 16-bit floats.
s - make shadow mapping passes have their own optimised buffers. Overrides existing ones if any.
S - strips the buffers for shadow mapping (consumes less space and memory)""",
        maxlen=5,
        default=config.get('OPTIMISE_VERTEX_BUFFERS_OPTIONS')) = {}

    # LOD
    EX_LOD_LEVELS : IntProperty(
        name="LOD Levels",
        description="Number of LOD levels",
        min=0, max=32,
        default=config.get('LOD_LEVELS')) = {}
    EX_LOD_DISTANCE : IntProperty(
        name="LOD Distance",
        description="Distance increment to reduce LOD",
        min=0, max=2000,
        default=config.get('LOD_DISTANCE')) = {}
    EX_LOD_PERCENT : IntProperty(
        name="LOD Percentage",
        description="LOD percentage reduction",
        min=0, max=99,
        default=config.get('LOD_PERCENT')) = {}
    EX_LOD_MESH_TOOLS : BoolProperty(
        name="Use OgreMesh Tools",
        description="""Use OgreMeshUpgrader/OgreMeshTool instead of Blender to generate the mesh LODs.
OgreMeshUpgrader/OgreMeshTool does LOD by removing edges, which allows only changing the index buffer and re-use the vertex-buffer (storage efficient).
Blenders decimate does LOD by collapsing vertices, which can result in a visually better LOD, but needs different vertex-buffers per LOD.""",
        default=config.get('LOD_MESH_TOOLS')) = {}

    # Pose Animation
    EX_SHAPE_ANIMATIONS : BoolProperty(
        name="Shape Animation",
        description="Export shape animations (updates the .mesh file)",
        default=config.get('SHAPE_ANIMATIONS')) = {}
    EX_SHAPE_NORMALS : BoolProperty(
        name="Shape Normals",
        description="Export normals in shape animations (updates the .mesh file)",
        default=config.get('SHAPE_NORMALS')) = {}
    
    # Logging
    EX_Vx_ENABLE_LOGGING : BoolProperty(
        name="Write Exporter Logs",
        description="Write Log file to the output directory (blender2ogre.log)",
        default=config.get('ENABLE_LOGGING')) = {}
    
    # It seems that it is not possible to exclude DEBUG when selecting a log level
    EX_Vx_DEBUG_LOGGING : BoolProperty(
        name="Debug Logging",
        description="Whether to show DEBUG log messages",
        default=config.get('DEBUG_LOGGING')) = {}
    
    # It was decided to make this an option that is not user-facing
    #EX_Vx_SHOW_LOG_NAME : BoolProperty(
    #    name="Show Log name",
    #    description="Show .py file from where each log message originated",
    #    default=config.get('SHOW_LOG_NAME')) = {}

class OP_ogre_export(bpy.types.Operator, _OgreCommonExport_):
    '''Export Ogre Scene'''
    bl_idname = "ogre.export"
    bl_label = "Export Ogre"
    bl_options = {'REGISTER'}
    # export logic is contained in the subclass
