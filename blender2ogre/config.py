
import bpy, os, sys, logging, pickle, mathutils
from bpy.props import *

AXIS_MODES =  [
    ('xyz', 'xyz', 'no swapping'),
    ('xz-y', 'xz-y', 'ogre standard'),
    ('-xzy', '-xzy', 'non standard'),
]

CONFIG_PATH = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
CONFIG_FILENAME = 'blender2ogre.pickle'
CONFIG_FILEPATH = os.path.join(CONFIG_PATH, CONFIG_FILENAME)

_CONFIG_DEFAULTS_ALL = {
    'TUNDRA_STREAMING' : True,
    'COPY_SHADER_PROGRAMS' : True,
    'MAX_TEXTURE_SIZE' : 4096,
    'SWAP_AXIS' : 'xz-y', # ogre standard
    'ONLY_DEFORMABLE_BONES' : False,
    'ONLY_KEYFRAMED_BONES' : False,
    'OGRE_INHERIT_SCALE' : False,
    'FORCE_IMAGE_FORMAT' : 'NONE',
    'TOUCH_TEXTURES' : True,
    'SEP_MATS' : True,
    'SCENE' : True,
    'SELONLY' : True,
    'EXPORT_HIDDEN' : True,
    'FORCE_CAMERA' : True,
    'FORCE_LAMPS' : True,
    'MESH' : True,
    'MESH_OVERWRITE' : True,
    'ARM_ANIM' : True,
    'SHAPE_ANIM' : True,
    'ARRAY' : True,
    'MATERIALS' : True,
    'DDS_MIPS' : True,
    'TRIM_BONE_WEIGHTS' : 0.01,
    'lodLevels' : 0,
    'lodDistance' : 300,
    'lodPercent' : 40,
    'nuextremityPoints' : 0,
    'generateEdgeLists' : False,
    'generateTangents' : True, # this is now safe - ignored if mesh is missing UVs
    'tangentSemantic' : 'tangent', # used to default to "uvw" but that doesn't seem to work with anything and breaks shaders
    'tangentUseParity' : 4,
    'tangentSplitMirrored' : False,
    'tangentSplitRotated' : False,
    'reorganiseBuffers' : True,
    'optimiseAnimations' : True,
}

_CONFIG_TAGS_ = 'OGRETOOLS_XML_CONVERTER OGRETOOLS_MESH_MAGICK TUNDRA_ROOT OGRE_MESHY IMAGE_MAGICK_CONVERT NVCOMPRESS NVIDIATOOLS_EXE USER_MATERIALS SHADER_PROGRAMS TUNDRA_STREAMING'.split()

''' todo: Change pretty much all of these windows ones. Make a smarter way of detecting
    Ogre tools and Tundra from various default folders. Also consider making a installer that
    ships Ogre cmd line tools to ease the setup steps for end users. '''

_CONFIG_DEFAULTS_WINDOWS = {
    'OGRETOOLS_XML_CONVERTER' : 'C:\\OgreCommandLineTools\\OgreXmlConverter.exe',
    'OGRETOOLS_MESH_MAGICK' : 'C:\\OgreCommandLineTools\\MeshMagick.exe',
    'TUNDRA_ROOT' : 'C:\\Tundra2',
    'OGRE_MESHY' : 'C:\\OgreMeshy\\Ogre Meshy.exe',
    'IMAGE_MAGICK_CONVERT' : 'C:\\Program Files\\ImageMagick\\convert.exe',
    'NVIDIATOOLS_EXE' : 'C:\\Program Files\\NVIDIA Corporation\\DDS Utilities\\nvdxt.exe',
    'USER_MATERIALS' : 'C:\\Tundra2\\media\\materials',
    'SHADER_PROGRAMS' : 'C:\\Tundra2\\media\\materials\\programs',
    'NVCOMPRESS' : 'C:\\nvcompress.exe'
}

_CONFIG_DEFAULTS_UNIX = {
    'OGRETOOLS_XML_CONVERTER' : '/usr/local/bin/OgreXMLConverter', # source build is better
    'OGRETOOLS_MESH_MAGICK' : '/usr/local/bin/MeshMagick',
    'TUNDRA_ROOT' : '~/Tundra2',
    'OGRE_MESHY' : '~/OgreMeshy/Ogre Meshy.exe',
    'IMAGE_MAGICK_CONVERT' : '/usr/bin/convert',
    'NVIDIATOOLS_EXE' : '~/.wine/drive_c/Program Files/NVIDIA Corporation/DDS Utilities',
    'USER_MATERIALS' : '~/Tundra2/media/materials',
    'SHADER_PROGRAMS' : '~/Tundra2/media/materials/programs',
    #'USER_MATERIALS' : '~/ogre_src_v1-7-3/Samples/Media/materials',
    #'SHADER_PROGRAMS' : '~/ogre_src_v1-7-3/Samples/Media/materials/programs',
    'NVCOMPRESS' : '/usr/local/bin/nvcompress'
}

# Unix: Replace ~ with absolute home dir path
if sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
    for tag in _CONFIG_DEFAULTS_UNIX:
        path = _CONFIG_DEFAULTS_UNIX[ tag ]
        if path.startswith('~'):
            _CONFIG_DEFAULTS_UNIX[ tag ] = os.path.expanduser( path )
        elif tag.startswith('OGRETOOLS') and not os.path.isfile( path ):
            _CONFIG_DEFAULTS_UNIX[ tag ] = os.path.join( '/usr/bin', os.path.split( path )[-1] )
    del tag
    del path


## PUBLIC API continues

def load_config():
    CONFIG = {}

    if os.path.isfile( CONFIG_FILEPATH ):
        try:
            with open( CONFIG_FILEPATH, 'rb' ) as f:
                CONFIG = pickle.load( f )
        except:
            print('[ERROR]: Can not read config from %s' %CONFIG_FILEPATH)

    for tag in _CONFIG_DEFAULTS_ALL:
        if tag not in CONFIG:
            CONFIG[ tag ] = _CONFIG_DEFAULTS_ALL[ tag ]

    for tag in _CONFIG_TAGS_:
        if tag not in CONFIG:
            if sys.platform.startswith('win'):
                CONFIG[ tag ] = _CONFIG_DEFAULTS_WINDOWS[ tag ]
            elif sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
                CONFIG[ tag ] = _CONFIG_DEFAULTS_UNIX[ tag ]
            else:
                print( 'ERROR: unknown platform' )
                assert 0

    try:
        if sys.platform.startswith('win'):
            import winreg
            # Find the blender2ogre install path from windows registry
            registry_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'Software\blender2ogre', 0, winreg.KEY_READ)
            exe_install_dir = winreg.QueryValueEx(registry_key, "Path")[0]
            if exe_install_dir != "":
                # OgreXmlConverter
                if os.path.isfile(exe_install_dir + "OgreXmlConverter.exe"):
                    print ("Using OgreXmlConverter from install path:", exe_install_dir + "OgreXmlConverter.exe")
                    CONFIG['OGRETOOLS_XML_CONVERTER'] = exe_install_dir + "OgreXmlConverter.exe"
                # Run auto updater as silent. Notifies user if there is a new version out.
                # This will not show any UI if there are no update and will go to network
                # only once per 2 days so it wont be spending much resources either.
                # todo: Move this to a more appropriate place than load_config()
                if os.path.isfile(exe_install_dir + "check-for-updates.exe"):
                    subprocess.Popen([exe_install_dir + "check-for-updates.exe", "/silent"])
    except Exception as e:
        print("Exception while reading windows registry:", e)

    # Setup temp hidden RNA to expose the file paths
    for tag in _CONFIG_TAGS_:
        default = CONFIG[ tag ]
        func = eval( 'lambda self,con: CONFIG.update( {"%s" : self.%s} )' %(tag,tag) )
        if type(default) is bool:
            prop = BoolProperty(
                name=tag, description='updates bool setting', default=default,
                options={'SKIP_SAVE'}, update=func
            )
        else:
            prop = StringProperty(
                name=tag, description='updates path setting', maxlen=128, default=default,
                options={'SKIP_SAVE'}, update=func
            )
        setattr( bpy.types.WindowManager, tag, prop )

    return CONFIG

CONFIG = load_config()

def save_config():
    global CONFIG
    #for key in CONFIG: print( '%s =   %s' %(key, CONFIG[key]) )
    if os.path.isdir( CONFIG_PATH ):
        try:
            with open( CONFIG_FILEPATH, 'wb' ) as f:
                pickle.dump( CONFIG, f, -1 )
        except:
            print('[ERROR]: Can not write to %s' %CONFIG_FILEPATH)
    else:
        print('[ERROR:] Config directory does not exist %s' %CONFIG_PATH)


class Blender2Ogre_ConfigOp(bpy.types.Operator):
    '''operator: saves current b2ogre configuration'''
    bl_idname = "ogre.save_config"
    bl_label = "save config file"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return True
    def invoke(self, context, event):
        config.save_config()
        Report.reset()
        Report.messages.append('SAVED %s' %CONFIG_FILEPATH)
        Report.show()
        return {'FINISHED'}


