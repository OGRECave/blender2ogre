# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    import importlib
    #print("Reloading modules: ogre_import")
    importlib.reload(ogre_import)

import bpy, os, getpass, math, mathutils, logging, datetime

from pprint import pprint
from bpy.props import EnumProperty, BoolProperty, FloatProperty, StringProperty, IntProperty
from .. import config
from ..report import Report
from ..util import *
from ..xml import *
from ..ogre import ogre_import

logger = logging.getLogger('import')

def auto_register(register):
    yield OP_ogre_import

    if register:
        if bpy.app.version >= (4, 1, 0):
            bpy.utils.register_class(OGRE_FH_import)
        bpy.types.TOPBAR_MT_file_import.append(menu_func)
    else:
        if bpy.app.version >= (4, 1, 0):
            bpy.utils.unregister_class(OGRE_FH_import)
        bpy.types.TOPBAR_MT_file_import.remove(menu_func)

def menu_func(self, context):
    """ invoked when import in drop down menu is clicked """
    op = self.layout.operator(OP_ogre_import.bl_idname, text="Ogre3D (.scene and .mesh)")
    return op

class _OgreCommonImport_(object):

    last_import_path = None
    called_from_UI = False

    @classmethod
    def poll(cls, context):
        if context.mode != 'EDIT_MESH':
            return True

    def __init__(self):
        # Check that converter is setup
        self.converter = detect_converter_type()

    def invoke(self, context, event):
        """
        By default the file handler invokes the operator with the filepath property set.
        In this example if this property is set the operator is executed, if not the
        file select window is invoked.
        This depends on setting ``options={'SKIP_SAVE'}`` to the property options to avoid
        to reuse filepath data between operator calls.
        """
        if self.filepath:
            return self.execute(context)

        # Update the interface with the config values
        for key, value in config.CONFIG.items():
            for prefix in ["IM_", "IM_Vx_", "IM_V1_", "IM_V2_"]:
                attr_name = prefix + key
                if getattr(self, attr_name, None) is not None:
                    setattr(self, attr_name, value)

        wm = context.window_manager
        fs = wm.fileselect_add(self)

        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        self.called_from_UI = True

        if self.converter == "unknown":
            layout.label(text="No converter found! Please check your preferences.", icon='ERROR')
        else:
            layout.label(text="Using '%s'" % self.converter, icon='INFO')

        # The Sections are listed in an array to have them in this particular order
        sections = ["General", "Armature", "Mesh", "Shape Keys", "Logging"]
        
        # Icons to use for the sections
        section_icons = {
            "General" : "WORLD", "Armature" : "ARMATURE_DATA", "Mesh" : "MESH_DATA", "Shape Keys" : "ANIM_DATA", "Logging" : "TEXT"
        }

        # Options associated with each section
        section_options = {
            "General" : ["IM_SWAP_AXIS", "IM_V2_MESH_TOOL_VERSION", "IM_IMPORT_XML_DELETE"], 
            "Armature" : ["IM_IMPORT_ANIMATIONS", "IM_ROUND_FRAMES", "IM_USE_SELECTED_SKELETON"], 
            "Mesh" : ["IM_IMPORT_NORMALS", "IM_MERGE_SUBMESHES"], 
            "Shape Keys" : ["IM_IMPORT_SHAPEKEYS"], 
            "Logging" : ["IM_Vx_ENABLE_LOGGING", "IM_Vx_DEBUG_LOGGING"]
        }

        for section in sections:
            row = layout.row()
            box = row.box()
            box.label(text=section, icon=section_icons[section])
            for prop in section_options[section]:
                if prop.startswith('IM_V1_'):
                    if self.converter == "OgreXMLConverter":
                        box.prop(self, prop)
                elif prop.startswith('IM_V2_'):
                    if self.converter == "OgreMeshTool":
                        box.prop(self, prop)
                elif prop.startswith('IM_Vx_'):
                    if self.converter != "unknown":
                        box.prop(self, prop)
                elif prop.startswith('IM_'):
                    box.prop(self, prop)

    def execute(self, context):
        """ Calls to this Operator can set unfiltered filepaths, ensure the file extension is .mesh, .xml or .scene. """
        if not self.filepath or not (\
           self.filepath.endswith(".mesh") or \
           self.filepath.endswith(".xml") or \
           self.filepath.endswith(".scene")):
            return {'CANCELLED'}

        # Add warning about missing XML converter
        Report.reset()
        if self.converter == "unknown":
            Report.errors.append(
              "Cannot find suitable OgreXMLConverter or OgreMeshTool executable." +
              "Import XML mesh - does NOT automatically convert .mesh to .xml file. You MUST run converter on the mesh manually.")

        logger.debug("Context.blend_data: %s" % context.blend_data.filepath)
        logger.debug("Context.scene.name: %s" % context.scene.name)
        logger.debug("Self.filepath: %s" % self.filepath)
        logger.debug("Self.last_import_path: %s" % self.last_import_path)

        # Load addonPreference in CONFIG
        config.update_from_addon_preference(context)

        # Resolve path from opened .blend if available. 
        # Normally it's not if blender was opened with "Recover Last Session".
        # After import is done once, remember that path when re-importing.
        if not self.last_import_path:
            # First import during this blender run
            if context.blend_data.filepath != "":
                path, name = os.path.split(context.blend_data.filepath)
                self.last_import_path = os.path.join(path, name.split('.')[0])

        if not self.last_import_path:
            self.last_import_path = os.path.expanduser("~")

        if self.filepath == "" or not self.filepath:
            self.filepath = "blender2ogre"

        logger.debug("Self.filepath: %s" % self.filepath)

        # Update saved defaults to new settings and also print import code
        kw = {}

        print ("_" * 80,"\n")

        script_text = "# Blender Import Script:\n\n"
        script_text += "import bpy\n"
        script_text += "bpy.ops.ogre.import_mesh(\n"
        script_text += "  filepath='%s', \n" % os.path.abspath(self.filepath).replace('\\', '\\\\')
        for name in dir(_OgreCommonImport_):
            conf_name = ""
            if name.startswith('IM_V1_') or \
               name.startswith('IM_V2_') or \
               name.startswith('IM_Vx_'):
                conf_name = name[6:]
            elif name.startswith('IM_'):
                conf_name = name[3:]
            if conf_name not in config.CONFIG.keys():
                continue
            attribute = getattr(self, name)
            kw[ conf_name ] = attribute
            if config._CONFIG_DEFAULTS_ALL[ conf_name ] != attribute:
                if type(attribute) == str:
                    script_text += "  %s='%s', \n" % (name, attribute)
                else:
                    script_text += "  %s=%s, \n" % (name, attribute)
        script_text += ")\n"

        print(script_text)

        print ("_" * 80,"\n")

        # Let's save the script in a text block if called from the UI
        if self.called_from_UI:
            text_block_name = "ogre_import-" + datetime.datetime.now().strftime("%Y%m%d%H%M")
            logger.info("* Creating Text Block '%s' with import script" % text_block_name)
            if text_block_name not in bpy.data.texts:
                #text_block = bpy.data.texts[text_block_name]
                text_block = bpy.data.texts.new(text_block_name)
                text_block.from_string(script_text)

        config.update(**kw)

        target_path, target_file_name = os.path.split(os.path.abspath(self.filepath))
        target_file_name = clean_object_name(target_file_name)
        target_file_name_no_ext = os.path.splitext(target_file_name)[0]

        file_handler = None

        # Add a file handler to all Logger instances
        if config.get('ENABLE_LOGGING') is True:
            log_file = os.path.join(target_path, "blender2ogre.log")
            logger.info("Writing log file to: %s" % log_file)

            file_handler = logging.FileHandler(filename=log_file, mode='w', encoding='utf-8', delay=False)

            # Show the python file name from where each log message originated
            SHOW_LOG_NAME = False

            if SHOW_LOG_NAME:
                file_formatter = logging.Formatter(fmt='%(asctime)s %(name)9s.py [%(levelname)5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            else:
                file_formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

            file_handler.setFormatter(file_formatter)

            for logger_name in logging.Logger.manager.loggerDict.keys():
                logging.getLogger(logger_name).addHandler(file_handler)

        logger.info("Target_path: %s" % target_path)
        logger.info("Target_file_name: %s" % target_file_name)

        Report.importing = True
        if target_file_name.lower().endswith(".scene"):
            ogre_import.load_scene(os.path.join(target_path, target_file_name))
        else:
            ogre_import.load_mesh(os.path.join(target_path, target_file_name))
        Report.show()

        # Flush and close all logging file handlers
        if config.get('ENABLE_LOGGING') is True:
            for logger_name in logging.Logger.manager.loggerDict.keys():
                logger_instance = logging.getLogger(logger_name)

                # Remove handlers
                logger_instance.handlers.clear()

            file_handler.flush()
            file_handler.close()

        return {'FINISHED'}

    filepath : StringProperty(name="File Path",
        description="Filepath used for importing Ogre .mesh and .scene files",
        maxlen=1024,
        default="",
        options={'SKIP_SAVE'},
        subtype='FILE_PATH')

    filter_glob : StringProperty(
            default="*.mesh;*.xml;*.scene;",
            options={'HIDDEN'})

    # Basic options
    # NOTE config values are automatically propagated if you name it like: IM_<config-name>
    # Properties can also be enabled for a specific converter by adding V1 or V2 in the name:
    # IM_V1_<config-name> for OgreXMLConverter
    # IM_V2_<config-name> for OgreMeshTool
    # IM_Vx_<config-name> for OgreXMLConverter and OgreMeshTool (hide only when no converter found)

    # General
    IM_SWAP_AXIS : EnumProperty(
        items=config.AXIS_MODES,
        name='Swap Axis',
        description='Axis swapping mode',
        default=config.get('SWAP_AXIS')) = {}

    IM_V2_MESH_TOOL_VERSION : EnumProperty(
        items=config.MESH_TOOL_VERSIONS,
        name='Mesh Import Version',
        description='Specify Ogre version format to read',
        default=config.get('MESH_TOOL_VERSION')) = {}

    IM_IMPORT_XML_DELETE : BoolProperty(
        name="Clean up XML files",
        description="Remove the generated XML files after binary conversion. \n(The removal will only happen if OgreXMLConverter/OgreMeshTool finishes successfully)",
        default=config.get('IMPORT_XML_DELETE')) = {}

    # Mesh
    IM_IMPORT_NORMALS : BoolProperty(
        name="Import Normals",
        description="Import custom mesh normals",
        default=config.get('IMPORT_NORMALS')) = {}

    IM_MERGE_SUBMESHES : BoolProperty(
        name="Merge Submeshes",
        description="Whether to merge submeshes to form a single mesh with different materials",
        default=config.get('MERGE_SUBMESHES')) = {}

    # Armature
    IM_IMPORT_ANIMATIONS : BoolProperty(
        name="Import animation",
        description="Import animations as actions",
        default=config.get('IMPORT_ANIMATIONS')) = {}

    IM_ROUND_FRAMES : BoolProperty(
        name="Adjust frame rate",
        description="Adjust scene frame rate to match imported animation",
        default=config.get('ROUND_FRAMES'))

    IM_USE_SELECTED_SKELETON : BoolProperty(
        name='Use selected skeleton',
        description='Link with selected armature object rather than importing a skeleton.\nUse this for importing skinned meshes that don\'t have their own skeleton.\nMake sure you have the correct skeleton selected or the weight maps may get mixed up.',
        default=config.get('USE_SELECTED_SKELETON')) = {}

    # Shape Keys
    IM_IMPORT_SHAPEKEYS : BoolProperty(
        name="Import shape keys",
        description="Import shape keys (morphs)",
        default=config.get('IMPORT_SHAPEKEYS')) = {}

    # Logging
    IM_Vx_ENABLE_LOGGING : BoolProperty(
        name="Write Importer Logs",
        description="Write Log file to the output directory (blender2ogre.log)",
        default=config.get('ENABLE_LOGGING')) = {}

    # It seems that it is not possible to exclude DEBUG when selecting a log level
    IM_Vx_DEBUG_LOGGING : BoolProperty(
        name="Debug Logging",
        description="Whether to show DEBUG log messages",
        default=config.get('DEBUG_LOGGING')) = {}


# Support for Blender 4.1+ drag and drop
# (https://docs.blender.org/api/4.1/bpy.types.FileHandler.html)
if bpy.app.version >= (4, 1, 0):
    class OGRE_FH_import(bpy.types.FileHandler):
        bl_idname = "OGRE_FH_import"
        bl_label = "Import Ogre drag and drop support"
        bl_import_operator = "ogre.import_mesh"
        bl_file_extensions = ".mesh;.xml;.scene;"

        @classmethod
        def poll_drop(cls, context):
            if context.mode != 'EDIT_MESH':
                return True


class OP_ogre_import(bpy.types.Operator, _OgreCommonImport_):
    '''Import Ogre Scene'''
    bl_idname = "ogre.import_mesh"
    bl_label = "Import Ogre"
    bl_options = {'REGISTER'}
    # import logic is contained in the subclass

    def __init__(self, *args, **kwargs):
        bpy.types.Operator.__init__(self, *args, **kwargs)
        _OgreCommonImport_.__init__(self)
