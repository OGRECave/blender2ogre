
import bpy, os, sys, logging, pickle, mathutils
from pprint import pprint
from bpy.props import *

AXIS_MODES =  [
    ('xyz', 'xyz', 'no swapping'),
    ('xz-y', 'xz-y', 'ogre standard'),
    ('-xzy', '-xzy', 'non standard'),
]

MESH_EXPORT_VERSIONS = [
    ('v1', 'v1', 'Export the mesh as a v1 object'),
    ('v2', 'v2', 'Export the mesh as a v2 object')
]

TANGENT_MODES =  [
    ('0', 'none', 'do not export'),
    ('3', 'generate', 'generate'),
    ('4', 'with parity', 'generate with parity'),
]

CONFIG_PATH = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
CONFIG_FILENAME = 'io_ogre.pickle'
CONFIG_FILEPATH = os.path.join(CONFIG_PATH, CONFIG_FILENAME)

_CONFIG_DEFAULTS_ALL = {
    'MESH' : True,
    'SCENE' : True,
    'COPY_SHADER_PROGRAMS' : True,
    'MAX_TEXTURE_SIZE' : 4096,
    'SWAP_AXIS' : 'xyz', # ogre standard is 'xz-y', but swapping is currently broken
    'SEP_MATS' : True,
    'SELONLY' : True,
    'EXPORT_HIDDEN' : True,
    'FORCE_CAMERA' : True,
    'FORCE_LAMPS' : True,
    'MESH_OVERWRITE' : True,
    'ONLY_DEFORMABLE_BONES' : False,
    'ONLY_KEYFRAMED_BONES' : False,
    'OGRE_INHERIT_SCALE' : False,
    'FORCE_IMAGE_FORMAT' : 'NONE',
    'TOUCH_TEXTURES' : True,
    'ARM_ANIM' : True,
    'SHAPE_ANIM' : True,
    'SHAPE_NORMALS' : True,
    'ARRAY' : True,
    'MATERIALS' : True,
    'DDS_MIPS' : 16,
    'TRIM_BONE_WEIGHTS' : 0.01,
    'TUNDRA_STREAMING' : True,
    'lodLevels' : 0,
    'lodDistance' : 300,
    'lodPercent' : 40,
    'nuextremityPoints' : 0,
    'generateEdgeLists' : False,
    'generateTangents' : "0",
    'optimiseAnimations' : True,
    'interface_toggle': False,
    'optimizeVertexBuffersForShaders' : True,
    'optimizeVertexBuffersForShadersOptions' : 'puqs',
    'EXPORT_ENABLE_LOGGING' : False,
    'MESH_TOOL_EXPORT_VERSION' : 'v2'
}

_CONFIG_TAGS_ = 'OGRETOOLS_XML_CONVERTER OGRETOOLS_MESH_MAGICK TUNDRA_ROOT MESH_PREVIEWER IMAGE_MAGICK_CONVERT USER_MATERIALS SHADER_PROGRAMS TUNDRA_STREAMING'.split()

''' todo: Change pretty much all of these windows ones. Make a smarter way of detecting
    Ogre tools and Tundra from various default folders. Also consider making a installer that
    ships Ogre cmd line tools to ease the setup steps for end users. '''

_CONFIG_DEFAULTS_WINDOWS = {
    'OGRETOOLS_XML_CONVERTER' : 'C:\\OgreCommandLineTools\\OgreXmlConverter.exe',
    'OGRETOOLS_MESH_MAGICK' : 'C:\\OgreCommandLineTools\\MeshMagick.exe',
    'TUNDRA_ROOT' : 'C:\\Tundra2',
    'MESH_PREVIEWER' : 'C:\\OgreMeshy\\Ogre Meshy.exe',
    'IMAGE_MAGICK_CONVERT' : 'C:\\Program Files\\ImageMagick\\convert.exe',
    'USER_MATERIALS' : 'C:\\Tundra2\\media\\materials',
    'SHADER_PROGRAMS' : 'C:\\Tundra2\\media\\materials\\programs'
}

_CONFIG_DEFAULTS_UNIX = {
    # do not use absolute paths like /usr/bin/exe_name. some distris install to /usr/local/bin ...
    # just trust the env PATH variable
    'IMAGE_MAGICK_CONVERT' : 'convert',
    'OGRETOOLS_XML_CONVERTER' : 'OgreXMLConverter',
    'OGRETOOLS_MESH_MAGICK' : '/usr/local/bin/MeshMagick',
    'TUNDRA_ROOT' : '~/Tundra2',
    'MESH_PREVIEWER' : 'ogre-meshviewer',
    'USER_MATERIALS' : '~/Tundra2/media/materials',
    'SHADER_PROGRAMS' : '~/Tundra2/media/materials/programs',
    #'USER_MATERIALS' : '~/ogre_src_v1-7-3/Samples/Media/materials',
    #'SHADER_PROGRAMS' : '~/ogre_src_v1-7-3/Samples/Media/materials/programs',
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
    config_dict = {}

    if os.path.isfile( CONFIG_FILEPATH ):
        try:
            with open( CONFIG_FILEPATH, 'rb' ) as f:
                config_dict = pickle.load( f )
        except:
            print('[ERROR]: Can not read config from %s' %CONFIG_FILEPATH)

    for tag in _CONFIG_DEFAULTS_ALL:
        if tag not in config_dict:
            config_dict[ tag ] = _CONFIG_DEFAULTS_ALL[ tag ]

    for tag in _CONFIG_TAGS_:
        if tag not in config_dict:
            if sys.platform.startswith('win'):
                config_dict[ tag ] = _CONFIG_DEFAULTS_WINDOWS[ tag ]
            elif sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
                config_dict[ tag ] = _CONFIG_DEFAULTS_UNIX[ tag ]
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
                    config_dict['OGRETOOLS_XML_CONVERTER'] = exe_install_dir + "OgreXmlConverter.exe"
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
        default = config_dict[ tag ]
        #func = eval( 'lambda self,con: config_dict.update( {"%s" : self.%s} )' %(tag,tag) )
        func = lambda self,con: config_dict.update( {tag : getattr(self,tag,default)} )
        if type(default) is bool:
            prop = BoolProperty( name=tag,
                                 description='updates bool setting',
                                 default=default,
                                 options={'SKIP_SAVE'},
                                 update=func)
        else:
            prop = StringProperty( name=tag,
                    description='updates path setting',
                    maxlen=128,
                    default=default,
                    options={'SKIP_SAVE'},
                    update=func)
        setattr( bpy.types.WindowManager, tag, prop )

    return config_dict

CONFIG = load_config()

def get(name, default=None):
    
    global CONFIG
    if name in CONFIG:
        return CONFIG[name]
    return default

def update(**kwargs):
    for k,v in kwargs.items():
        if k not in _CONFIG_DEFAULTS_ALL:
            print("trying to set CONFIG['%s']=%s, but is not a known config setting" % (k,v))
        CONFIG[k] = v
    save_config()

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


def update_from_addon_preference(context):
    addon_preferences = context.preferences.addons["io_ogre"].preferences

    for key in _CONFIG_TAGS_:
        addon_pref_value = getattr(addon_preferences,key,None)
        if addon_pref_value is not None:
            CONFIG[key] = addon_pref_value
