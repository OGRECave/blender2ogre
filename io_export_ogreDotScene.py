# Copyright (C) 2010 Brett Hartshorn
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

bl_info = {
    "name": "OGRE Exporter (.scene, .mesh, .skeleton) and RealXtend (.txml)",
    "author": "HartsAntler, Sebastien Rombauts, and F00bar",
    "version": (0,5,5),
    "blender": (2,5,9),
    "location": "File > Export...",
    "description": "Export to Ogre xml and binary formats",
    #"warning": "Quick Start: '.mesh' output requires OgreCommandLineTools (http://www.ogre3d.org/download/tools) - install to the default path.",
    "wiki_url": "http://code.google.com/p/blender2ogre/w/list",
    "tracker_url": "http://code.google.com/p/blender2ogre/issues/list",
    "category": "Import-Export"}

VERSION = '0.5.5 preview6'

## Options ##
AXIS_MODES =  [
    ('xyz', 'xyz', 'no swapping'),
    ('xz-y', 'xz-y', 'ogre standard'),
    ('-xzy', '-xzy', 'non standard'),
]

# options yet to be added to the config file
OPTIONS = {
    'ONLY_ANIMATED_BONES' : False,
    'FORCE_IMAGE_FORMAT' : None,
    'PATH' : '/tmp',    			# TODO SRombauts: use the CONFIG_TEMP_DIR variable
    'TOUCH_TEXTURES' : False,
    'SWAP_AXIS' : 'xz-y',         # Tundra2 standard
    #'SWAP_AXIS' : '-xzy',         # Tundra1 standard
}



def swap(vec):
    if OPTIONS['SWAP_AXIS'] == 'xyz': return vec
    elif OPTIONS['SWAP_AXIS'] == 'xzy':
        if len(vec) == 3: return mathutils.Vector( [vec.x, vec.z, vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, vec.x, vec.z, vec.y] )
    elif OPTIONS['SWAP_AXIS'] == '-xzy':
        if len(vec) == 3: return mathutils.Vector( [-vec.x, vec.z, vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, -vec.x, vec.z, vec.y] )
    elif OPTIONS['SWAP_AXIS'] == 'xz-y':
        if len(vec) == 3: return mathutils.Vector( [vec.x, vec.z, -vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, vec.x, vec.z, -vec.y] )
    else:
        print( 'unknown swap axis mode', OPTIONS['SWAP_AXIS'] )
        assert 0


###########################################################
###### imports #####
import os, sys, time, hashlib, getpass, tempfile, configparser
import math, subprocess
import array, time, ctypes
from xml.sax.saxutils import XMLGenerator

try:
    import bpy, mathutils
    from bpy.props import *
except ImportError:
    sys.exit("This script is an addon for blender, you must install it from blender.")


######################### bpy RNA #########################

# ..Material.ogre_depth_write = AUTO|ON|OFF
bpy.types.Material.ogre_disable_depth_write = BoolProperty( name='force disable depth write', default=False )

#If depth-buffer checking is on, whenever a pixel is about to be written to the frame buffer the depth buffer is checked to see if the pixel is in front of all other pixels written at that point. If not, the pixel is not written. If depth checking is off, pixels are written no matter what has been rendered before.
bpy.types.Material.ogre_depth_check = BoolProperty( name='depth check', default=True )

#Sets whether this pass will use 'alpha to coverage', a way to multisample alpha texture edges so they blend more seamlessly with the background. This facility is typically only available on cards from around 2006 onwards, but it is safe to enable it anyway - Ogre will just ignore it if the hardware does not support it. The common use for alpha to coverage is foliage rendering and chain-link fence style textures.
bpy.types.Material.ogre_alpha_to_coverage = BoolProperty( name='multisample alpha edges', default=False )

#This option is usually only useful if this pass is an additive lighting pass, and is at least the second one in the technique. Ie areas which are not affected by the current light(s) will never need to be rendered. If there is more than one light being passed to the pass, then the scissor is defined to be the rectangle which covers all lights in screen-space. Directional lights are ignored since they are infinite.
#This option does not need to be specified if you are using a standard additive shadow mode, i.e. SHADOWTYPE_STENCIL_ADDITIVE or SHADOWTYPE_TEXTURE_ADDITIVE, since it is the default behaviour to use a scissor for each additive shadow pass. However, if you're not using shadows, or you're using Integrated Texture Shadows where passes are specified in a custom manner, then this could be of use to you.
bpy.types.Material.ogre_light_scissor = BoolProperty( name='light scissor', default=False )


bpy.types.Material.ogre_light_clip_planes = BoolProperty( name='light clip planes', default=False )

#Scaling objects causes normals to also change magnitude, which can throw off your lighting calculations. By default, the SceneManager detects this and will automatically re-normalise normals for any scaled object, but this has a cost. If you'd prefer to control this manually, call SceneManager::setNormaliseNormalsOnScale(false) and then use this option on materials which are sensitive to normals being resized.
bpy.types.Material.ogre_normalize_normals = BoolProperty( name='normalize normals', default=False )

#Sets whether or not dynamic lighting is turned on for this pass or not. If lighting is turned off, all objects rendered using the pass will be fully lit. This attribute has no effect if a vertex program is used.
bpy.types.Material.ogre_lighting = BoolProperty( name='dynamic lighting', default=True )

#If colour writing is off no visible pixels are written to the screen during this pass. You might think this is useless, but if you render with colour writing off, and with very minimal other settings, you can use this pass to initialise the depth buffer before subsequently rendering other passes which fill in the colour data. This can give you significant performance boosts on some newer cards, especially when using complex fragment programs, because if the depth check fails then the fragment program is never run. 
bpy.types.Material.ogre_colour_write = BoolProperty( name='color-write', default=True )


bpy.types.Material.use_fixed_pipeline = BoolProperty( name='fixed pipeline', default=True )

# hidden option - gets turned on by operator
bpy.types.Material.use_material_passes = BoolProperty( name='use ogre extra material passes (layers)', default=False )


bpy.types.Material.use_in_ogre_material_pass = BoolProperty( name='Layer Toggle', default=True )

bpy.types.Material.use_ogre_advanced_options = BoolProperty( name='Show Advanced Options', default=False )




#http://blenderpython.svn.sourceforge.net/viewvc/blenderpython/259/scripts/addons_extern/io_scene_assimp/import_assimp.py?revision=4&view=markup
#bpy.types.Material.pass1 = PointerProperty(
#    name = 'ogre pass 1',
#    type = bpy.types.Material,
#)


bpy.types.Material.ogre_parent_material = EnumProperty(
  name="Script Inheritence", 
  description='ogre parent material class', default='',
  items=[ ('', '', 'none') ],
)


bpy.types.Material.ogre_polygon_mode = EnumProperty(
    items=[
            ('solid', 'solid', 'SOLID'),
            ('wireframe', 'wireframe', 'WIREFRAME'),
            ('points', 'points', 'POINTS'),
    ],
    name='faces draw type', 
    description="ogre face draw mode", 
    default='solid'
)

bpy.types.Material.ogre_shading = EnumProperty(
    items=[
            ('flat', 'flat', 'FLAT'),
            ('gouraud', 'gouraud', 'GOURAUD'),
            ('phong', 'phong', 'PHONG'),
    ],
    name='hardware shading', 
    description="Sets the kind of shading which should be used for representing dynamic lighting for this pass.", 
    default='gouraud'
)


bpy.types.Material.ogre_cull_hardware = EnumProperty(
    items=[
            ('clockwise', 'clockwise', 'CLOCKWISE'),
            ('anticlockwise', 'anticlockwise', 'COUNTER CLOCKWISE'),
            ('none', 'none', 'NONE'),
    ],
    name='hardware culling', 
    description="If the option 'cull_hardware clockwise' is set, all triangles whose vertices are viewed in clockwise order from the camera will be culled by the hardware.", 
    default='clockwise'
)


bpy.types.Material.ogre_transparent_sorting = EnumProperty(
    items=[
            ('on', 'on', 'ON'),
            ('off', 'off', 'OFF'),
            ('force', 'force', 'FORCE ON'),
    ],
    name='transparent sorting', 
    description="By default all transparent materials are sorted such that renderables furthest away from the camera are rendered first. This is usually the desired behaviour but in certain cases this depth sorting may be unnecessary and undesirable. If for example it is necessary to ensure the rendering order does not change from one frame to the next. In this case you could set the value to 'off' to prevent sorting.", 
    default='on'
)



bpy.types.Material.ogre_illumination_stage = EnumProperty(
    items=[
            ('none', 'none', 'autodetect'),
            ('ambient', 'ambient', 'ambient'),
            ('per_light', 'per_light', 'lights'),
            ('decal', 'decal', 'decal')
    ],
    name='illumination stage', 
    description='When using an additive lighting mode (SHADOWTYPE_STENCIL_ADDITIVE or SHADOWTYPE_TEXTURE_ADDITIVE), the scene is rendered in 3 discrete stages, ambient (or pre-lighting), per-light (once per light, with shadowing) and decal (or post-lighting). Usually OGRE figures out how to categorise your passes automatically, but there are some effects you cannot achieve without manually controlling the illumination.', 
    default='none'
)




_ogre_depth_func =  [
    ('less_equal', 'less_equal', '<='),
    ('less', 'less', '<'),
    ('equal', 'equal', '=='),
    ('not_equal', 'not_equal', '!='),
    ('greater_equal', 'greater_equal', '>='),
    ('greater', 'greater', '>'),
    ('always_fail', 'always_fail', 'false'),
    ('always_pass', 'always_pass', 'true'),
]
bpy.types.Material.ogre_depth_func = EnumProperty(
    items=_ogre_depth_func, 
    name='depth buffer function', 
    description='If depth checking is enabled (see depth_check) a comparison occurs between the depth value of the pixel to be written and the current contents of the buffer. This comparison is normally less_equal, i.e. the pixel is written if it is closer (or at the same distance) than the current contents', 
    default='less_equal'
)



_ogre_scene_blend_ops =  [
    ('add', 'add', 'DEFAULT'),
    ('subtract', 'subtract', 'SUBTRACT'),
    ('reverse_subtract', 'reverse_subtract', 'REVERSE SUBTRACT'),
    ('min', 'min', 'MIN'),
    ('max', 'max', 'MAX'),

]
bpy.types.Material.ogre_scene_blend_op = EnumProperty(
    items=_ogre_scene_blend_ops, 
    name='scene blending operation', 
    description='This directive changes the operation which is applied between the two components of the scene blending equation', 
    default='add'
)

_ogre_scene_blend_types =  [
    ('one zero', 'one zero', 'DEFAULT'),
    ('alpha_blend', 'alpha_blend', "The alpha value of the rendering output is used as a mask. Equivalent to 'scene_blend src_alpha one_minus_src_alpha'"),
    ('add', 'add', "The colour of the rendering output is added to the scene. Good for explosions, flares, lights, ghosts etc. Equivalent to 'scene_blend one one'."),
    ('modulate', 'modulate', "The colour of the rendering output is multiplied with the scene contents. Generally colours and darkens the scene, good for smoked glass, semi-transparent objects etc. Equivalent to 'scene_blend dest_colour zero'"),
    ('colour_blend', 'colour_blend', 'Colour the scene based on the brightness of the input colours, but dont darken. Equivalent to "scene_blend src_colour one_minus_src_colour"'),
]
for mode in 'dest_colour src_colour one_minus_dest_colour dest_alpha src_alpha one_minus_dest_alpha one_minus_src_alpha'.split():
    _ogre_scene_blend_types.append( ('one %s'%mode, 'one %s'%mode, '') )
del mode

bpy.types.Material.ogre_scene_blend = EnumProperty(
    items=_ogre_scene_blend_types, 
    name='scene blend', 
    description='blending operation of material to scene', 
    default='one zero'
)



###########################################################
_faq_ = '''

Q: i have hundres of objects, is there a way i can merge them on export only?
A: yes, just add them to a group named starting with "merge"

Q: can i use subsurf or multi-res on a mesh with an armature?
A: yes.

Q: can i use subsurf or multi-res on a mesh with shape animation?
A: no.

Q: i don't see any objects when i export?
A: you must select the objects you wish to export.

Q: i don't see my animations when exported?
A: make sure you created an NLA strip on the armature.

Q: do i need to bake my IK and other constraints into FK on my armature before export?
A: no.

'''


_doc_installing_ = '''
Installing:
    Installing the Addon:
        You can simply copy io_export_ogreDotScene.py to your blender installation under blender/2.57/scripts/addons/
        and enable it in the user-prefs interface (CTRL+ALT+U)
        Or you can use blenders interface, under user-prefs, click addons, and click 'install-addon'
        (its a good idea to delete the old version first)

    Required:
        1. blender2.59

        2. Install Ogre Command Line tools to the default path ( C:\\OgreCommandLineTools )
            http://www.ogre3d.org/download/tools
            (Linux users may use above and Wine, or install from source, or install via apt-get install ogre-tools)

    Optional:
        3. Install NVIDIA DDS Legacy Utilities    ( install to default path )
            http://developer.nvidia.com/object/dds_utilities_legacy.html
            (Linux users will need to use Wine)

        4. Install Image Magick
            http://www.imagemagick.org

        5. Copy OgreMeshy to C:\\OgreMeshy
            If your using 64bit Windows, you may need to download a 64bit OgreMeshy
            (Linux copy to your home folder)

'''




## make sure we can import from same directory ##
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path: sys.path.append( SCRIPT_DIR )


############ CONFIG ##############
CONFIG_FILENAME = 'blender2ogre.cfg'

# Methode to read a config value from a config file, or update it to the default value
def readOrCreateConfigValue(config, section, option, default):
    try:
        return config.get(section, option)
    except configparser.NoOptionError:
        config.set(section, option, default)
        return default

# Read the addon config values from the config blender2ogre.cfg file, or create/update it whith platform specific default values
def readOrCreateConfig():
    # TODO SRombauts: make a class AddonConfig to store these values
    global CONFIG_TEMP_DIR, CONFIG_OGRETOOLS_XML_CONVERTER, CONFIG_OGRETOOLS_MESH_MAGICK, CONFIG_OGRE_MESHY, CONFIG_IMAGE_MAGICK_CONVERT, CONFIG_NVIDIATOOLS_EXE, CONFIG_MYSHADERS_DIR, CONFIG_TUNDRA_ROOT
    
    # Create default options values (platform specific paths)
    DEFAULT_TEMP_DIR = tempfile.gettempdir()
    if sys.platform.startswith('win'):        # win32 and win64
        DEFAULT_OGRETOOLS_XML_CONVERTER = 'C:\\OgreCommandLineTools\\OgreXmlConverter.exe'
        DEFAULT_OGRETOOLS_MESH_MAGICK = 'C:\\OgreCommandLineTools\\MeshMagick.exe'
        DEFAULT_OGRE_MESHY = 'C:\\OgreMeshy\\Ogre Meshy.exe'
        DEFAULT_IMAGE_MAGICK_CONVERT = ''
        for name in os.listdir(  'C:\\Program Files' ):
            if name.startswith( 'ImageMagick' ):
                image_magick_path = os.path.join('C:\\Program Files', name)
                DEFAULT_IMAGE_MAGICK_CONVERT = os.path.join(image_magick_path, 'convert.exe');
                break
        DEFAULT_NVIDIATOOLS_EXE = 'C:\\Program Files\\NVIDIA Corporation\\DDS Utilities\\nvdxt.exe'

        DEFAULT_TUNDRA_ROOT = 'C:\\Tundra2'
        DEFAULT_MYSHADERS_DIR = 'C:\\Tundra2\\media\\materials'
        
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):        # OSX patch by FreqMod June6th 2011
        # DEFAULT_TEMP_PATH = '/tmp' 
        # ogre-tools from andrews repo is broken
        #DEFAULT_OGRETOOLS_XML_CONVERTER = '/usr/bin/OgreXMLConverter'	# apt-get ogre-tools
        DEFAULT_OGRETOOLS_XML_CONVERTER = '/usr/local/bin/OgreXMLConverter' # prefer source builds

        DEFAULT_OGRETOOLS_MESH_MAGICK = '/usr/bin/MeshMagick'
        DEFAULT_TUNDRA_ROOT = '%s/Tundra2' %os.environ['HOME']
        DEFAULT_MYSHADERS_DIR = '%s/Tundra2/media/materials' %os.environ['HOME']

        if not os.path.isfile( DEFAULT_OGRETOOLS_XML_CONVERTER ):
            if os.path.isfile( '/usr/bin/OgreXMLConverter'):
                DEFAULT_OGRETOOLS_XML_CONVERTER = '/usr/bin/OgreXMLConverter'
            elif os.path.isfile( '%s/.wine/drive_c/OgreCommandLineTools/OgreXmlConverter.exe' %os.environ['HOME'] ):
                DEFAULT_OGRETOOLS_XML_CONVERTER = '%s/.wine/drive_c/OgreCommandLineTools/OgreXmlConverter.exe' %os.environ['HOME']
                DEFAULT_OGRETOOLS_MESH_MAGICK = '%s/.wine/drive_c/OgreCommandLineTools/MeshMagick.exe' %os.environ['HOME']


        DEFAULT_OGRE_MESHY = '%s/OgreMeshy/Ogre Meshy.exe' %os.environ['HOME']

        DEFAULT_IMAGE_MAGICK_CONVERT = '/usr/bin/convert/convert'
        if not os.path.isfile( DEFAULT_IMAGE_MAGICK_CONVERT ): DEFAULT_IMAGE_MAGICK_CONVERT = '/usr/local/bin/convert/convert'

        DEFAULT_NVIDIATOOLS_EXE = '%s/.wine/drive_c/Program Files/NVIDIA Corporation/DDS Utilities' %os.environ['HOME']
        
    # Compose the path to the config file, in the config/scripts subfolder
    config_path = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
    config_filepath = os.path.join(config_path, CONFIG_FILENAME)

    # Read the blender2ogre.cfg config file for addon options (or create a 'paths' section if not present)
    print('Opening config file %s ...' % config_filepath)
    config = configparser.ConfigParser()
    config.read(config_filepath)
    if not config.has_section('paths'):
        config.add_section('paths')

    ################ Read (or create default) config values ##################
    for tag in 'OGRETOOLS_XML_CONVERTER OGRETOOLS_MESH_MAGICK TUNDRA_ROOT OGRE_MESHY IMAGE_MAGICK_CONVERT NVIDIATOOLS_EXE MYSHADERS_DIR TEMP_DIR'.split():
        default = readOrCreateConfigValue( config, 'paths', tag, locals()['DEFAULT_'+tag] )
        globals().update( {'CONFIG_'+tag : default})
        func = eval( 'lambda self,con: globals().update( {"CONFIG_%s" : self.%s} )' %(tag,tag) )
        prop = StringProperty(
            name=tag, description='updates path setting', maxlen=128, default=default, 
            options={'SKIP_SAVE'}, update=func
        )
        setattr( bpy.types.WindowManager, tag, prop )
        print( 'CONFIG: %s = %s' %(tag, default) )

    # Write the blender2ogre.cfg config file 
    with open(config_filepath, 'w') as configfile:
        config.write(configfile)
        print('config file %s written.' % config_filepath)


class Blender2Ogre_ConfigOp(bpy.types.Operator):
    '''operator: finds missing textures - checks directories with textures to see if missing are there.'''  
    bl_idname = "ogre.save_config"  
    bl_label = "save config file"
    bl_options = {'REGISTER'}
    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        config_path = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
        config_filepath = os.path.join(config_path, CONFIG_FILENAME)
        config = configparser.ConfigParser()
        config.add_section('paths')

        for tag in 'OGRETOOLS_XML_CONVERTER OGRETOOLS_MESH_MAGICK TUNDRA_ROOT OGRE_MESHY IMAGE_MAGICK_CONVERT NVIDIATOOLS_EXE MYSHADERS_DIR TEMP_DIR'.split():
            value = globals()['CONFIG_'+tag]
            config.set('paths', tag, value)

        with open(config_filepath, 'w') as configfile:
            config.write(configfile)
            print('config file %s written.' % config_filepath)

        Report.reset()
        Report.messages.append('SAVED %s' %config_filepath)
        Report.show()

        return {'FINISHED'}


# customize missing material - red flags for users so they can quickly see what they forgot to assign a material to.
# (do not crash if no material on object - thats annoying for the user)
MISSING_MATERIAL = '''
material _missing_material_ 
{
    receive_shadows off
    technique
    {
        pass
        {
            ambient 0.1 0.1 0.1 1.0
            diffuse 0.8 0.0 0.0 1.0
            specular 0.5 0.5 0.5 1.0 12.5
            emissive 0.3 0.3 0.3 1.0
        }
    }
}
'''



############# helper functions ##############

def has_property( a, name ):
    for prop in a.items():
        n,val = prop
        if n == name: return True


# a default plane, with simple-subsurf and displace modifier on Z
def is_strictly_simple_terrain( ob ):
    if len(ob.data.vertices) != 4 and len(ob.data.faces) != 1: return False
    elif len(ob.modifiers) < 2: return False
    elif ob.modifiers[0].type != 'SUBSURF' or ob.modifiers[1].type != 'DISPLACE': return False
    elif ob.modifiers[0].subdivision_type != 'SIMPLE': return False
    elif ob.modifiers[1].direction != 'Z': return False # disallow NORMAL and other modes
    else: return True

def get_image_textures( mat ):
    r = []
    for s in mat.texture_slots:
        if s and s.texture.type == 'IMAGE': r.append( s )
    return r


def indent( level, *args ):
    if not args: return '\t' * level
    else:
        a = ''
        for line in args:
            a += '\t' * level
            a += line
            a += '\n'
        return a

def gather_instances():
    instances = {}
    for ob in bpy.context.scene.objects:
        if ob.data and ob.data.users > 1:
            if ob.data not in instances: instances[ ob.data ] = []
            instances[ ob.data ].append( ob )
    return instances

def select_instances( context, name ):
    for ob in bpy.context.scene.objects: ob.select = False
    ob = bpy.context.scene.objects[ name ]
    if ob.data:
        inst = gather_instances()
        for ob in inst[ ob.data ]: ob.select = True
        bpy.context.scene.objects.active = ob


def select_group( context, name, options={} ):
    for ob in bpy.context.scene.objects: ob.select = False
    for grp in bpy.data.groups:
        if grp.name == name:
            #context.scene.objects.active = grp.objects
            #Note that the context is read-only. These values cannot be modified directly, though they may be changed by running API functions or by using the data API. So bpy.context.object = obj will raise an error. But bpy.context.scene.objects.active = obj will work as expected. - http://wiki.blender.org/index.php?title=Dev:2.5/Py/API/Intro&useskin=monobook
            bpy.context.scene.objects.active = grp.objects[0]
            for ob in grp.objects: ob.select = True
        else: pass


def get_objects_using_materials( mats ):
    obs = []
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            for mat in ob.data.materials:
                if mat in mats:
                    if ob not in obs: obs.append( ob )
                    break
    return obs

def get_materials_using_image( img ):
    mats = []
    for mat in bpy.data.materials:
        for slot in get_image_textures( mat ):
            if slot.texture.image == img:
                if mat not in mats: mats.append( mat )
    return mats



###############################################
class Ogre_relocate_textures_op(bpy.types.Operator):
    '''operator: finds missing textures - checks directories with textures to see if missing are there.'''  
    bl_idname = "ogre.relocate_textures"  
    bl_label = "relocate textures"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        Report.reset()
        badmats = []
        for img in bpy.data.images:
            url = bpy.path.abspath( img.filepath )
            path,name = os.path.split(url)
            if not name: continue        # user cleared the value

            if os.path.isfile( url ):
                if path not in Report.paths: Report.paths.append( path )
                #Report.messages.append( 'OK: %s' %name )
            else:
                Report.messages.append( 'MISSING: %s' %name )
                found = None
                for p in Report.paths:
                    if os.path.isfile( os.path.join(p,name) ):
                        Report.messages.append( '  found texture in: %s' %p )
                        found = os.path.join( p,name )
                        break
                if not found:        # try lower case
                    for p in Report.paths:
                        name = name.lower()
                        if os.path.isfile( os.path.join(p,name) ):
                            Report.messages.append( '  found texture in (lower-case): %s' %p )
                            found = os.path.join( p,name )
                            break
                if found:
                    img.filepath = bpy.path.relpath( found )
                    Report.messages.append( '  reassigned to -> %s ' %img.filepath )
                else:
                    for mat in get_materials_using_image( img ):
                        if mat not in badmats:
                            badmats.append( mat )

        for ob in get_objects_using_materials(badmats): ob.select=True
        for mat in badmats:
            Report.warnings.append( 'BAD-MATERIAL:  %s' %material_name(mat) )

        if not Report.messages and not badmats: Report.messages.append( 'Everything is OK' )

        bpy.ops.wm.call_menu( name='Ogre_User_Report' )
        return {'FINISHED'}



class ReportSingleton(object):
    def show(self): bpy.ops.wm.call_menu( name='Ogre_User_Report' )
    def __init__(self): self.reset()
    def reset(self):
        self.materials = []
        self.meshes = []
        self.lights = []
        self.cameras = []
        self.armatures = []
        self.armature_animations = []
        self.shape_animations = []
        self.textures = []
        self.vertices = 0
        self.orig_vertices = 0
        self.faces = 0
        self.triangles = 0
        self.warnings = []
        self.errors = []
        self.messages = []
        self.paths = []

    def report(self):
        r = ['Report:']
        ex = ['Extended Report:']
        if self.errors:
            r.append( '  ERRORS:' )
            for a in self.errors: r.append( '    . %s' %a )

        #if not bpy.context.selected_objects:
        #    self.warnings.append('YOU DID NOT SELECT ANYTHING TO EXPORT')
        if self.warnings:
            r.append( '  WARNINGS:' )
            for a in self.warnings: r.append( '    . %s' %a )

        if self.messages:
            r.append( '  MESSAGES:' )
            for a in self.messages: r.append( '    . %s' %a )
        if self.paths:
            r.append( '  PATHS:' )
            for a in self.paths: r.append( '    . %s' %a )


        if self.vertices:
            r.append( '  Original Vertices: %s' %self.orig_vertices)
            r.append( '  Exported Vertices: %s' %self.vertices )
            r.append( '  Original Faces: %s' %self.faces )
            r.append( '  Exported Triangles: %s' %self.triangles )
            ## TODO report file sizes, meshes and textures

        for tag in 'meshes lights cameras armatures armature_animations shape_animations materials textures'.split():
            attr = getattr(self, tag)
            if attr:
                name = tag.replace('_',' ').upper()
                r.append( '  %s: %s' %(name, len(attr)) )
                if attr:
                    ex.append( '  %s:' %name )
                    for a in attr: ex.append( '    . %s' %a )

        txt = '\n'.join( r )
        ex = '\n'.join( ex )        # console only - extended report
        print('_'*80)
        print(txt)
        print(ex)
        print('_'*80)
        return txt

Report = ReportSingleton()



class MyShadersSingleton(object):
    def get(self, name):
        if name in self.vertex_progs_by_name: return self.vertex_progs_by_name[ name ]
        elif name in self.fragment_progs_by_name: return self.fragment_progs_by_name[ name ]
            
    def __init__(self):
        self.path = CONFIG_MYSHADERS_DIR
        self.files = []
        self.vertex_progs = []
        self.vertex_progs_by_name = {}
        self.fragment_progs = []
        self.fragment_progs_by_name = {}
        if os.path.isdir( self.path ):
            for name in os.listdir( self.path ):
                if name.endswith('.program'):
                    url = os.path.join( self.path, name )
                    #self.parse(url)
                    try: self.parse( url )
                    except: print('WARNING: syntax error in .program!')

    def parse(self, url ):
        print('parsing .program', url )
        data = open( url, 'rb' ).read().decode()
        lines = data.splitlines()
        lines.reverse()
        while lines:
            line = lines.pop().strip()
            if line:
                if line.startswith('vertex_program') or line.startswith('fragment_program'):
                    ptype, name, tech = line.split()
                    if tech == 'asm':
                        print('Warning: asm programs not supported')
                    else:
                        prog = Program(name, tech, url)
                        if ptype == 'vertex_program':
                            self.vertex_progs.append( prog ); prog.type = 'vertex'
                            self.vertex_progs_by_name[ prog.name ] = prog
                        else:
                            self.fragment_progs.append( prog ); prog.type = 'fragment'
                            self.fragment_progs_by_name[ prog.name ] = prog

                        while lines:        # continue parsing
                            subA = lines.pop()
                            if subA.startswith('}'): break
                            else:
                                a = subA = subA.strip()
                                if a.startswith('//') and len(a) > 2: prog.comments.append( a[2:] )
                                elif subA.startswith('source'): prog.source = subA.split()[-1]
                                elif subA.startswith('entry_point'): prog.entry_point = subA.split()[-1]
                                elif subA.startswith('profiles'): prog.profiles = subA.split()[-1]
                                elif subA.startswith('compile_arguments'): prog.compile_args = ' '.join( subA.split()[-1].split('-D') )
                                elif subA.startswith('default_params'):
                                    while lines:
                                        b = lines.pop().strip()
                                        if b.startswith('}'): break
                                        else:
                                            if b.startswith('param_named_auto'):
                                                s = b.split('param_named_auto')[-1].strip()
                                                prog.add_param( s, auto=True )
                                            elif b.startswith('param_named'):
                                                s = b.split('param_named')[-1].strip()
                                                prog.add_param( s )

        # end ugly-simple parser #
        self.files.append( url )
        print('----------------vertex programs----------------')
        for p in self.vertex_progs: p.debug()
        print('----------------fragment programs----------------')
        for p in self.fragment_progs: p.debug()

class Program(object):
    def debug( self ):
        print('GPU Program')
        print('  ', self.name)
        print('  ', self.technique)
        print('  ', self.file)
        for p in self.params + self.params_auto: print('    ', p)

    def __init__(self, name, tech, file):
        if len(name) >= 31:        #KeyError: 'the length of IDProperty names is limited to 31 characters'
            if '/' in name: name = name.split('/')[-1]
            if len(name) >= 31: name = name[ : 29 ] + '..'
        self.name = name; self.technique = tech; self.file = file
        self.source = self.entry_point = self.profiles = self.compile_args = self.type = None
        self.params = []; self.params_auto = []
        self.comments = []

    def add_param( self, line, auto=False ):
        name = line.split()[0]
        value_code = line.split()[1]
        p = {'name': name, 'value-code': value_code }
        if auto: self.params_auto.append( p )
        else: self.params.append( p )
        if len( line.split() ) >= 3:
            args = line.split( p['value-code'] )[-1]
            p['args'] = args.strip()

    def get_param( self, name ):
        for p in self.params + self.params_auto:
            if p['name'] == name: return p

class Ogre_User_Report(bpy.types.Menu):
    bl_label = "Mini-Report | (see console for full report)"
    def draw(self, context):
        layout = self.layout
        txt = Report.report()
        for line in txt.splitlines():
            layout.label(text=line)


#################### New Physics ####################

_physics_modes =  [
    ('NONE', 'NONE', 'no physics'),
    ('RIGID_BODY', 'RIGID_BODY', 'rigid body'),
    ('SOFT_BODY', 'SOFT_BODY', 'soft body'),
]

bpy.types.Object.physics_mode = EnumProperty(
    items = _physics_modes, 
    name = 'physics mode', 
    description='physics mode', 
    default='NONE'
)

bpy.types.Object.physics_friction = FloatProperty(
    name='Simple Friction', description='physics friction', default=0.1, min=0.0, max=1.0)

bpy.types.Object.physics_bounce = FloatProperty(
    name='Simple Bounce', description='physics bounce', default=0.01, min=0.0, max=1.0)


bpy.types.Object.collision_terrain_x_steps = IntProperty(
    name="Ogre Terrain: x samples", description="resolution in X of height map", 
    default=64, min=4, max=8192)
bpy.types.Object.collision_terrain_y_steps = IntProperty(
    name="Ogre Terrain: y samples", description="resolution in Y of height map", 
    default=64, min=4, max=8192)

_collision_modes =  [
    ('NONE', 'NONE', 'no collision'),
    ('PRIMITIVE', 'PRIMITIVE', 'primitive collision type'),
    ('MESH', 'MESH', 'triangle-mesh or convex-hull collision type'),
    ('DECIMATED', 'DECIMATED', 'auto-decimated collision type'),
    ('COMPOUND', 'COMPOUND', 'children primitive compound collision type'),
    ('TERRAIN', 'TERRAIN', 'terrain (height map) collision type'),
]

bpy.types.Object.collision_mode = EnumProperty(
    items = _collision_modes, 
    name = 'primary collision mode', 
    description='collision mode', 
    default='NONE'
)


bpy.types.Object.subcollision = BoolProperty(
    name="collision compound", description="member of a collision compound", default=False)


######################

def _get_proxy_decimate_mod( ob ):
    proxy = None
    for child in ob.children:
        if child.subcollision and child.name.startswith('DECIMATED'):
            for mod in child.modifiers:
                if mod.type == 'DECIMATE': return mod

def bake_terrain( ob, normalize=True ):
    assert ob.collision_mode == 'TERRAIN'
    terrain = None
    for child in ob.children:
        if child.subcollision and child.name.startswith('TERRAIN'):
            terrain = child
            break
    assert terrain
    data = terrain.to_mesh(bpy.context.scene, True, "PREVIEW")
    raw = [ v.co.z for v in data.vertices ]
    Zmin = min( raw )
    Zmax = max( raw )
    depth = Zmax-Zmin
    m = 1.0 / depth

    rows = []
    i = 0
    for x in range( ob.collision_terrain_x_steps ):
        row = []
        for y in range( ob.collision_terrain_y_steps ):
            v = data.vertices[ i ]
            if normalize: z = (v.co.z - Zmin) * m
            else: z = v.co.z
            row.append( z )
            i += 1
        if x%2: row.reverse()   # blender grid prim zig-zags
        rows.append( row )

    return {'data':rows, 'min':Zmin, 'max':Zmax, 'depth':depth}

def save_terrain_as_NTF( path, ob ):    # Tundra format - hardcoded 16x16 patch format
    info = bake_terrain( ob )
    url = os.path.join( path, '%s.ntf'%ob.data.name )
    f = open(url, "wb")
    buf = array.array("I")  # header
    xs = ob.collision_terrain_x_steps
    ys = ob.collision_terrain_y_steps
    xpatches = int(xs/16)
    ypatches = int(ys/16)
    header = [ xpatches, ypatches ]
    buf.fromlist( header )
    buf.tofile(f)
    ########## body ###########
    rows = info['data']
    for x in range( xpatches ):
        for y in range( ypatches ):
            patch = []
            for i in range(16):
                for j in range(16):
                    v = rows[ (x*16)+i ][ (y*16)+j ]
                    patch.append( v )
            buf = array.array("f")
            buf.fromlist( patch )
            buf.tofile(f)
    f.close()
    path,name = os.path.split(url)
    R = {
        'url':url, 'min':info['min'], 'max':info['max'], 'path':path, 'name':name,
        'xpatches': xpatches, 'ypatches': ypatches,
        'depth':info['depth'],
    }
    return R


class OgreCollisionOp(bpy.types.Operator):
    '''ogre collision'''  
    bl_idname = "ogre.set_collision"  
    bl_label = "modify collision"
    bl_options = {'REGISTER'}

    MODE = StringProperty(name="toggle mode", description="...", maxlen=32, default="disable")

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type == 'MESH': return True

    def get_subcollisions( self, ob, create=True ):
        r = get_subcollisions( ob )
        if not r and create:
            method = getattr(self, 'create_%s'%ob.collision_mode)
            p = method(ob)
            p.name = '%s.%s' %(ob.collision_mode, ob.name)
            p.subcollision = True
            r.append( p )
        return r

    def create_DECIMATED(self, ob):
        child = ob.copy()
        bpy.context.scene.objects.link( child )
        child.matrix_local = mathutils.Matrix()
        child.parent = ob
        child.hide_select = True
        child.draw_type = 'WIRE'
        #child.select = False
        child.lock_location = [True]*3
        child.lock_rotation = [True]*3
        child.lock_scale = [True]*3
        decmod = child.modifiers.new('proxy', type='DECIMATE')
        decmod.ratio = 0.5
        return child

    def create_TERRAIN(self, ob):
        x = ob.collision_terrain_x_steps
        y = ob.collision_terrain_y_steps
        #################################
        #pos = ob.matrix_world.to_translation()
        bpy.ops.mesh.primitive_grid_add(
            x_subdivisions=x, 
            y_subdivisions=y, 
            size=1.0 )      #, location=pos )
        grid = bpy.context.active_object
        assert grid.name.startswith('Grid')
        grid.collision_terrain_x_steps = x
        grid.collision_terrain_y_steps = y
        #############################
        x,y,z = ob.dimensions
        sx,sy,sz = ob.scale
        x *= 1.0/sx
        y *= 1.0/sy
        z *= 1.0/sz
        grid.scale.x = x/2
        grid.scale.y = y/2
        grid.location.z -= z/2
        grid.data.show_all_edges = True
        grid.draw_type = 'WIRE'
        grid.hide_select = True
        #grid.select = False
        grid.lock_location = [True]*3
        grid.lock_rotation = [True]*3
        grid.lock_scale = [True]*3
        grid.parent = ob
        bpy.context.scene.objects.active = ob
        mod = grid.modifiers.new(name='temp', type='SHRINKWRAP')
        mod.wrap_method = 'PROJECT'
        mod.use_project_z = True
        mod.target = ob
        mod.cull_face = 'FRONT'
        return grid


    def invoke(self, context, event):
        ob = context.active_object
        game = ob.game

        subtype = None
        if ':' in self.MODE:
            mode, subtype = self.MODE.split(':')
            ##BLENDERBUG##ob.game.collision_bounds_type = subtype   # BUG this can not come before
            if subtype in 'BOX SPHERE CYLINDER CONE CAPSULE'.split():
                ob.draw_bounds_type = subtype
            else:
                ob.draw_bounds_type = 'POLYHEDRON'
            ob.game.collision_bounds_type = subtype  # BLENDERBUG - this must come after draw_bounds_type assignment
        else:
            mode = self.MODE
        ob.collision_mode = mode

        if ob.data.show_all_edges: ob.data.show_all_edges = False
        if ob.show_texture_space: ob.show_texture_space = False
        if ob.show_bounds: ob.show_bounds = False
        if ob.show_wire: ob.show_wire = False
        for child in ob.children:
            if child.subcollision and not child.hide: child.hide = True


        if mode == 'NONE':
            game.use_ghost = True
            game.use_collision_bounds = False

        elif mode == 'PRIMITIVE':
            game.use_ghost = False
            game.use_collision_bounds = True
            ob.show_bounds = True

        elif mode == 'MESH':
            game.use_ghost = False
            game.use_collision_bounds = True
            ob.show_wire = True

            if game.collision_bounds_type == 'CONVEX_HULL':
                ob.show_texture_space = True
            else:
                ob.data.show_all_edges = True

        elif mode == 'DECIMATED':
            game.use_ghost = True
            game.use_collision_bounds = False
            game.use_collision_compound = True

            proxy = self.get_subcollisions(ob)[0]
            if proxy.hide: proxy.hide = False
            ob.game.use_collision_compound = True  # proxy
            mod = _get_proxy_decimate_mod( ob )
            mod.show_viewport = True
            if not proxy.select:    # ugly (but works)
                proxy.hide_select = False
                proxy.select = True
                proxy.hide_select = True

            if game.collision_bounds_type == 'CONVEX_HULL':
                ob.show_texture_space = True


        elif mode == 'TERRAIN':
            game.use_ghost = True
            game.use_collision_bounds = False
            game.use_collision_compound = True

            proxy = self.get_subcollisions(ob)[0]
            if proxy.hide: proxy.hide = False


        elif mode == 'COMPOUND':
            game.use_ghost = True
            game.use_collision_bounds = False
            game.use_collision_compound = True

        else: assert 0    # unknown mode

        return {'FINISHED'}

################################
class PhysicsPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Physics"
    @classmethod
    def poll(cls, context):
        if context.active_object: return True
        else: return False

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        game = ob.game

        if ob.type != 'MESH': return
        elif ob.subcollision == True:
            box = layout.box()
            if ob.parent:
                box.label(text='object is a collision proxy for: %s' %ob.parent.name)
            else:
                box.label(text='WARNING: collision proxy missing parent')
            return

        #####################
        box = layout.box()
        box.prop(ob, 'physics_mode')
        if ob.physics_mode != 'NONE':
            box.prop(game, 'mass', text='Mass')
            box.prop(ob, 'physics_friction', text='Friction', slider=True)
            box.prop(ob, 'physics_bounce', text='Bounce', slider=True)

            box.label(text="Damping:")
            box.prop(game, 'damping', text='Translation', slider=True)
            box.prop(game, 'rotation_damping', text='Rotation', slider=True)

            box.label(text="Velocity:")
            box.prop(game, "velocity_min", text="Minimum")
            box.prop(game, "velocity_max", text="Maximum")


################################
class CollisionPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Collision"
    @classmethod
    def poll(cls, context):
        if context.active_object: return True
        else: return False

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        game = ob.game

        if ob.type != 'MESH': return
        elif ob.subcollision == True:
            box = layout.box()
            if ob.parent:
                box.label(text='object is a collision proxy for: %s' %ob.parent.name)
            else:
                box.label(text='WARNING: collision proxy missing parent')
            return

        #####################
        mode = ob.collision_mode
        if mode == 'NONE':
            box = layout.box()
            op = box.operator( 'ogre.set_collision', text='Enable Collision', icon='PHYSICS' )
            op.MODE = 'PRIMITIVE:%s' %game.collision_bounds_type

        else:
            prim = game.collision_bounds_type

            box = layout.box()
            op = box.operator( 'ogre.set_collision', text='Disable Collision', icon='X' )
            op.MODE = 'NONE'
            box.prop(game, "collision_margin", text="Collision Margin", slider=True)


            box = layout.box()
            if mode == 'PRIMITIVE': box.label(text='Primitive: %s' %prim)
            else: box.label(text='Primitive')
            row = box.row()
            _icons = {
                'BOX':'MESH_CUBE', 'SPHERE':'MESH_UVSPHERE', 'CYLINDER':'MESH_CYLINDER',
                'CONE':'MESH_CONE', 'CAPSULE':'META_CAPSULE'}
            for a in 'BOX SPHERE CYLINDER CONE CAPSULE'.split():
                if prim == a and mode == 'PRIMITIVE':
                    op = row.operator( 'ogre.set_collision', text='', icon=_icons[a], emboss=True )
                    op.MODE = 'PRIMITIVE:%s' %a
                else:
                    op = row.operator( 'ogre.set_collision', text='', icon=_icons[a], emboss=False )
                    op.MODE = 'PRIMITIVE:%s' %a

            box = layout.box()
            if mode == 'MESH': box.label(text='Mesh: %s' %prim.split('_')[0] )
            else: box.label(text='Mesh')
            row = box.row()
            row.label(text='- - - - - - - - - - - - - -')
            _icons = {'TRIANGLE_MESH':'MESH_ICOSPHERE', 'CONVEX_HULL':'SURFACE_NCURVE'}
            for a in 'TRIANGLE_MESH CONVEX_HULL'.split():
                if prim == a and mode == 'MESH':
                    op = row.operator( 'ogre.set_collision', text='', icon=_icons[a], emboss=True )
                    op.MODE = 'MESH:%s' %a
                else:
                    op = row.operator( 'ogre.set_collision', text='', icon=_icons[a], emboss=False )
                    op.MODE = 'MESH:%s' %a

            box = layout.box()
            if mode == 'DECIMATED':
                box.label(text='Decimate: %s' %prim.split('_')[0] )
                row = box.row()
                mod = _get_proxy_decimate_mod( ob )
                assert mod  # decimate modifier is missing
                row.label(text='Faces: %s' %mod.face_count )
                box.prop( mod, 'ratio', text='' )

            else:
                box.label(text='Decimate')
                row = box.row()
                row.label(text='- - - - - - - - - - - - - -')

            _icons = {'TRIANGLE_MESH':'MESH_ICOSPHERE', 'CONVEX_HULL':'SURFACE_NCURVE'}
            for a in 'TRIANGLE_MESH CONVEX_HULL'.split():
                if prim == a and mode == 'DECIMATED':
                    op = row.operator( 'ogre.set_collision', text='', icon=_icons[a], emboss=True )
                    op.MODE = 'DECIMATED:%s' %a
                else:
                    op = row.operator( 'ogre.set_collision', text='', icon=_icons[a], emboss=False )
                    op.MODE = 'DECIMATED:%s' %a

            box = layout.box()
            if mode == 'TERRAIN':
                terrain = get_subcollisions( ob )[0]
                if ob.collision_terrain_x_steps != terrain.collision_terrain_x_steps or ob.collision_terrain_y_steps != terrain.collision_terrain_y_steps:
                    op = box.operator( 'ogre.set_collision', text='Rebuild Terrain', icon='MESH_GRID' )
                    op.MODE = 'TERRAIN'
                else:
                    box.label(text='Terrain:')

                row = box.row()
                row.prop( ob, 'collision_terrain_x_steps', 'X' )
                row.prop( ob, 'collision_terrain_y_steps', 'Y' )
                #box.prop( terrain.modifiers[0], 'offset' ) # gets normalized away
                box.prop( terrain.modifiers[0], 'cull_face', text='Cull' )
                box.prop( terrain, 'location' )     # TODO hide X and Y

            else:
                op = box.operator( 'ogre.set_collision', text='Terrain Collision', icon='MESH_GRID' )
                op.MODE = 'TERRAIN'

            box = layout.box()
            if mode == 'COMPOUND':
                op = box.operator( 'ogre.set_collision', text='Compound Collision', icon='ROTATECOLLECTION' )
            else:
                op = box.operator( 'ogre.set_collision', text='Compound Collision', icon='ROTATECOLLECTION' )
            op.MODE = 'COMPOUND'


class ConfigurePanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_label = "Ogre Configuration File"
    def draw(self, context):
        layout = self.layout
        op = layout.operator( 'ogre.save_config', text='update config file', icon='FILE' )
        for tag in 'OGRETOOLS_XML_CONVERTER OGRETOOLS_MESH_MAGICK TUNDRA_ROOT OGRE_MESHY IMAGE_MAGICK_CONVERT NVIDIATOOLS_EXE MYSHADERS_DIR TEMP_DIR'.split():
            layout.prop( context.window_manager, tag )



############### extra tools #############
'''
Getting a UV texture's pixel value per vertex, the stupid way.
(this should be rewritten as a C function exposed to Python)
This script does the following hack to get the pixel value:
  1. copy the object
  2. apply a displace modifier
  3. for each RGB set the ImageTexture.<color>_factor to 1.0 and other to 0.0
  4. for each RGB bake a mesh (apply the displace modifier)
  5. for each RGB find the difference of vertex locations
  6. apply the differences as vertex colors

'''
class Harts_Tools(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_label = "Ogre Extra Tools"
    @classmethod
    def poll(cls, context):
        if context.active_object: return True
        else: return False
    def draw(self, context):
        layout = self.layout
        layout.operator(Ogre_relocate_textures_op.bl_idname)

        ob = context.active_object
        if ob.type != 'MESH': return
        slot = context.texture_slot
        node = context.texture_node
        space = context.space_data
        tex = context.texture
        #idblock = context_tex_datablock(context)
        idblock = ob.active_material
        tex_collection = space.pin_id is None and type(idblock) != bpy.types.Brush and not node
        if not tex_collection: return

        box = layout.box()
        box.label(text='bake selected texture to vertex colors')
        if not ob.data.vertex_colors.active:
            box.label(text='please select a vertex color channel to bake to')
        else:
            row = box.row()
            row.operator( "harts.bake_texture_to_vertexcolors", text='bake' )
            row.template_list(idblock, "texture_slots", idblock, "active_texture_index", rows=2)



class Harts_bake_texture_vc_op(bpy.types.Operator):
    '''operator: bakes texture to vertex colors'''
    bl_idname = "harts.bake_texture_to_vertexcolors"  
    bl_label = "harts extra tools"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        ob = context.active_object
        #tex = context.texture
        tex = ob.active_material.active_texture        # slot

        o2 = ob.copy()
        #bpy.context.scene.objects.link( o2 )#; o2.select = True
        while o2.modifiers: o2.modifiers.remove( o2.modifiers[0] )
        mod = o2.modifiers.new('_hack_', type='DISPLACE')
        mod.texture = tex
        mod.texture_coords = 'UV'
        mod.mid_level = 1.0
        #print(dir(tex))
        image = None
        mult = 1.0
        baked = []
        if hasattr(tex, 'image'):
            image = tex.image
            ua = tex.use_alpha
            tex.use_alpha = False

            tex.factor_red = 1.0
            tex.factor_green = .0
            tex.factor_blue = .0
            _data = o2.to_mesh(bpy.context.scene, True, "PREVIEW")
            baked.append( [] )
            for v1 in ob.data.vertices:
                v2 = _data.vertices[ v1.index ]
                baked[-1].append( (v1.co-v2.co).magnitude*mult )
            print('red', baked[-1])

            tex.factor_red = .0
            tex.factor_green = 1.0
            tex.factor_blue = .0
            _data = o2.to_mesh(bpy.context.scene, True, "PREVIEW")
            baked.append( [] )
            for v1 in ob.data.vertices:
                v2 = _data.vertices[ v1.index ]
                baked[-1].append( (v1.co-v2.co).magnitude*mult )
            print('green', baked[-1])

            tex.factor_red = .0
            tex.factor_green = .0
            tex.factor_blue = 1.0
            _data = o2.to_mesh(bpy.context.scene, True, "PREVIEW")
            baked.append( [] )
            for v1 in ob.data.vertices:
                v2 = _data.vertices[ v1.index ]
                baked[-1].append( (v1.co-v2.co).magnitude*mult )
            print('blue', baked[-1])


            tex.factor_red = 1.0
            tex.factor_green = 1.0
            tex.factor_blue = 1.0
            tex.use_alpha = ua

            #while o2.modifiers: o2.modifiers.remove( o2.modifiers[0] )

            vchan = ob.data.vertex_colors.active
            for f in ob.data.faces:
                for i,vidx in enumerate(f.vertices):
                    r = baked[0][ vidx ]
                    g = baked[1][ vidx ]
                    b = baked[2][ vidx ]
                    #color = vchan.data[ f.index ].color1
                    color = getattr( vchan.data[ f.index ], 'color%s' %(i+1) )
                    color.r = 1.0-r
                    color.g = 1.0-g
                    color.b = 1.0-b

        return {'FINISHED'}



##################################################################
_game_logic_intro_doc_ = '''
Hijacking the BGE

Blender contains a fully functional game engine (BGE) that is highly useful for learning the concepts of game programming by breaking it down into three simple parts: Sensor, Controller, and Actuator.  An Ogre based game engine will likely have similar concepts in its internal API and game logic scripting.  Without a custom interface to define game logic, very often game designers may have to resort to having programmers implement their ideas in purely handwritten script.  This is prone to breakage because object names then end up being hard-coded.  Not only does this lead to non-reusable code, its also a slow process.  Why should we have to resort to this when Blender already contains a very rich interface for game logic?  By hijacking a subset of the BGE interface we can make this workflow between game designer and game programmer much better.

The OgreDocScene format can easily be extened to include extra game logic data.  While the BGE contains some features that can not be easily mapped to other game engines, there are many are highly useful generic features we can exploit, including many of the Sensors and Actuators.  Blender uses the paradigm of: 1. Sensor -> 2. Controller -> 3. Actuator.  In pseudo-code, this can be thought of as: 1. on-event -> 2. conditional logic -> 3. do-action.  The designer is most often concerned with the on-events (the Sensors), and the do-actions (the Actuators); and the BGE interface provides a clear way for defining and editing those.  Its a harder task to provide a good interface for the conditional logic (Controller), that is flexible enough to fit everyones different Ogre engine and requirements, so that is outside the scope of this exporter at this time.  A programmer will still be required to fill the gap between Sensor and Actuator, but hopefully his work is greatly reduced and can write more generic/reuseable code.

The rules for which Sensors trigger which Actuators is left undefined, as explained above we are hijacking the BGE interface not trying to export and reimplement everything.  BGE Controllers and all links are ignored by the exporter, so whats the best way to define Sensor/Actuator relationships?  One convention that seems logical is to group Sensors and Actuators by name.  More complex syntax could be used in Sensor/Actuators names, or they could be completely ignored and instead all the mapping is done by the game programmer using other rules.  This issue is not easily solved so designers and the engine programmers will have to decide upon their own conventions, there is no one size fits all solution.
'''


_ogre_logic_types_doc_ = '''
Supported Sensors:
    . Collision
    . Near
    . Radar
    . Touching
    . Raycast
    . Message

Supported Actuators:
    . Shape Action*
    . Edit Object
    . Camera
    . Constraint
    . Message
    . Motion
    . Sound
    . Visibility

*note: Shape Action
The most common thing a designer will want to do is have an event trigger an animation.  The BGE contains an Actuator called "Shape Action", with useful properties like: start/end frame, and blending.  It also contains a property called "Action" but this is hidden because the exporter ignores action names and instead uses the names of NLA strips when exporting Ogre animation tracks.  The current workaround is to hijack the "Frame Property" attribute and change its name to "animation".  The designer can then simply type the name of the animation track (NLA strip).  Any custom syntax could actually be implemented here for calling animations, its up to the engine programmer to define how this field will be used.  For example: "*.explode" could be implemented to mean "on all objects" play the "explode" animation.

'''





class Ogre_game_logic_op(bpy.types.Operator):
    '''helper to hijack BGE logic'''
    bl_idname = "ogre.gamelogic"
    bl_label = "ogre game logic helper"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type
    logictype = StringProperty(name="logic-type", description="...", maxlen=32, default="")
    subtype = StringProperty(name="logic-subtype", description="...", maxlen=32, default="")

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        if self.logictype == 'sensor':
            bpy.ops.logic.sensor_add( type=self.subtype )
        elif self.logictype == 'actuator':
            bpy.ops.logic.actuator_add( type=self.subtype )

        return {'FINISHED'}

class _WrapLogic(object):
    ## custom name hacks ##
    SwapName = {
        'frame_property' : 'animation',
    }
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


#class Ogre_Logic_Sensors(bpy.types.Panel):
class Deprecated1:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    #bl_context = "physics"        # selects tab within the properties
    bl_label = "Ogre Game Logic | Sensors"

    @classmethod
    def poll(cls, context):
        if context.active_object: return True
        else: return False

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        game = ob.game

        split = layout.split()

        col = split.column()
        col.label( text='New Sensor:' )

        row = col.row()
        op = row.operator( 'ogre.gamelogic', text='Near' )
        op.logictype = 'sensor'
        op.subtype = 'NEAR'
        op = row.operator( 'ogre.gamelogic', text='Collision' )
        op.logictype = 'sensor'
        op.subtype = 'COLLISION'
        op = row.operator( 'ogre.gamelogic', text='Radar' )
        op.logictype = 'sensor'
        op.subtype = 'RADAR'

        row = col.row()
        op = row.operator( 'ogre.gamelogic', text='Touching' )
        op.logictype = 'sensor'
        op.subtype = 'TOUCH'
        op = row.operator( 'ogre.gamelogic', text='Raycast' )
        op.logictype = 'sensor'
        op.subtype = 'RAY'
        op = row.operator( 'ogre.gamelogic', text='Message' )
        op.logictype = 'sensor'
        op.subtype = 'MESSAGE'

        layout.separator()
        split = layout.split()
        left = split.column()
        right = split.column()
        mid = len(game.sensors)/2
        for i,sen in enumerate(game.sensors):
            w = WrapSensor( sen )
            if i < mid: w.widget( left )
            else: w.widget( right )

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


#class Ogre_Logic_Actuators(bpy.types.Panel):
class Deprecated2:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "physics"
    bl_label = "Ogre Game Logic | Actuators"

    @classmethod
    def poll(cls, context):
        if context.active_object: return True
        else: return False

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        game = ob.game

        split = layout.split()

        ### actuators
        col = split.column()
        col.label( text='New Actuator:' )

        row = col.row()
        op = row.operator( 'ogre.gamelogic', text='Camera' )
        op.logictype = 'actuator'
        op.subtype = 'CAMERA'
        op = row.operator( 'ogre.gamelogic', text='Constrain' )
        op.logictype = 'actuator'
        op.subtype = 'CONSTRAINT'
        op = row.operator( 'ogre.gamelogic', text='Message' )
        op.logictype = 'actuator'
        op.subtype = 'MESSAGE'
        op = row.operator( 'ogre.gamelogic', text='Animation' )
        op.logictype = 'actuator'
        op.subtype = 'SHAPE_ACTION'

        row = col.row()
        op = row.operator( 'ogre.gamelogic', text='Motion' )
        op.logictype = 'actuator'
        op.subtype = 'OBJECT'        # blender bug? 'MOTION'
        op = row.operator( 'ogre.gamelogic', text='Sound' )
        op.logictype = 'actuator'
        op.subtype = 'SOUND'
        op = row.operator( 'ogre.gamelogic', text='Visibility' )
        op.logictype = 'actuator'
        op.subtype = 'VISIBILITY'
        op = row.operator( 'ogre.gamelogic', text='Change' )
        op.logictype = 'actuator'
        op.subtype = 'EDIT_OBJECT'


        layout.separator()
        split = layout.split()
        left = split.column()
        right = split.column()
        mid = len(game.actuators)/2
        for i,act in enumerate(game.actuators):
            w = WrapActuator( act )
            if i < mid: w.widget( left )
            else: w.widget( right )





def _helper_ogre_material_draw_options( parent, mat ):
    box = parent.box()
    box.prop(mat, 'ogre_parent_material')
    box.prop(mat, 'ogre_scene_blend')
    box.prop(mat, "use_shadows")

    row = box.row()
    row.prop(mat, "use_transparency", text="Transparent")
    if mat.use_transparency: row.prop(mat, "alpha")

    box = parent.box()
    box.prop( mat, 'use_fixed_pipeline', text='Generate Fixed Pipeline', icon='LAMP_SUN' )
    if mat.use_fixed_pipeline:
        row = box.row()
        row.prop(mat, "diffuse_color")
        row.prop(mat, "diffuse_intensity")
        row = box.row()
        row.prop(mat, "specular_color")
        row.prop(mat, "specular_intensity")
        row = box.row()
        row.prop(mat, "specular_hardness")
        row = box.row()
        row.prop(mat, "emit")
        row.prop(mat, "ambient")
        row.prop(mat, "use_vertex_color_paint", text="Vertex Colors")


    box.prop(mat, 'use_ogre_advanced_options', text='----------------------advanced options----------------------' )

    if mat.use_ogre_advanced_options:
        box.prop(mat, 'ogre_disable_depth_write' )

        for tag in 'ogre_colour_write ogre_lighting ogre_normalize_normals ogre_light_clip_planes ogre_light_scissor ogre_alpha_to_coverage ogre_depth_check'.split():
            box.prop(mat, tag)

        for tag in 'ogre_polygon_mode ogre_shading ogre_cull_hardware ogre_transparent_sorting ogre_illumination_stage ogre_depth_func ogre_scene_blend_op'.split():
            box.prop(mat, tag)

        box = parent.box()



class Ogre_Material_Panel( bpy.types.Panel ):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_label = "Ogre Material (pass0)"

    def draw(self, context):
        if not hasattr(context, "material"): return
        if not context.active_object: return
        if not context.active_object.active_material: return

        mat = context.material
        ob = context.object
        slot = context.material_slot
        layout = self.layout

        _helper_ogre_material_draw_options( layout, mat )

        if not mat.use_material_passes:
            box = layout.box()
            box.operator( 'ogre.force_setup_material_passes', text="Use Extra Material Layers", icon='SCENE_DATA' )



class _OgreMatPass( object ):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.active_material and context.active_object.active_material.use_material_passes:
            return True


    def draw(self, context):
        if not hasattr(context, "material"): return
        if not context.active_object: return
        if not context.active_object.active_material: return

        mat = context.material
        ob = context.object
        slot = context.material_slot
        layout = self.layout

        if mat.use_material_passes:
            db = layout.box()
            nodes = get_or_create_material_passes( mat )
            node = nodes[ self.INDEX ]
            split = db.row()
            if node.material: split.prop( node.material, 'use_in_ogre_material_pass', text='' )
            split.prop( node, 'material' )
            op = split.operator( 'ogre.helper_create_attach_material_layer', icon="PLUS", text='' )
            op.INDEX = self.INDEX

            dbb = db.box()
            if node.material and node.material.use_in_ogre_material_pass:
                _helper_ogre_material_draw_options( dbb, node.material )

## operator ##
class _create_new_material_layer_helper(bpy.types.Operator):
    '''helper to create new material layer'''
    bl_idname = "ogre.helper_create_attach_material_layer"
    bl_label = "creates and assigns new material to layer"
    bl_options = {'REGISTER', 'UNDO'}
    INDEX = IntProperty(name="material layer index", description="index", default=0, min=0, max=8)
    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.active_material and context.active_object.active_material.use_material_passes:
            return True

    def execute(self, context):
        mat = context.active_object.active_material
        nodes = get_or_create_material_passes( mat )
        node = nodes[ self.INDEX ]
        node.material = bpy.data.materials.new( name='OgreLayer' )
        return {'FINISHED'}

class MatPass1( _OgreMatPass, bpy.types.Panel ): INDEX = 0; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass2( _OgreMatPass, bpy.types.Panel ): INDEX = 1; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass3( _OgreMatPass, bpy.types.Panel ): INDEX = 2; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass4( _OgreMatPass, bpy.types.Panel ): INDEX = 3; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass5( _OgreMatPass, bpy.types.Panel ): INDEX = 4; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass6( _OgreMatPass, bpy.types.Panel ): INDEX = 5; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass7( _OgreMatPass, bpy.types.Panel ): INDEX = 6; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass8( _OgreMatPass, bpy.types.Panel ): INDEX = 7; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)




class Ogre_Texture_Panel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "texture"
    bl_label = "Ogre Texture"
    @classmethod
    def poll(cls, context):
        if not hasattr(context, "texture_slot"):
            return False
        else: return True

    def draw(self, context):
        #if not hasattr(context, "texture_slot"):
        #    return False
        layout = self.layout
        #idblock = context_tex_datablock(context)
        slot = context.texture_slot
        if not slot or not slot.texture: return

        box = layout.box()
        row = box.row()
        row.label(text="Mapping:")
        row.prop(slot, "texture_coords", text="")
        if slot.texture_coords == 'UV':
            row.label(text="UV Layer:")
            row.prop(slot, "uv_layer", text="")
        else:
            row.label(text="Projection:")
            row.prop(slot, "mapping", text="")

        if hasattr(slot.texture, 'image') and slot.texture.image:
            row = box.row()
            row.label(text="Repeat Mode:")
            row.prop(slot.texture, "extension", text="")
            if slot.texture.extension == 'CLIP':
                row.label(text="Border Color:")
                row.prop(slot, "color", text="")

        box = layout.box()
        row = box.row()
        row.label(text="Blending:")
        row.prop(slot, "blend_type", text="")
        row.label(text="Alpha Stencil:")
        row.prop(slot, "use_stencil", text="")
        row = box.row()
        if slot.blend_type == 'MIX':
            row.label(text="Mixing:")
            row.prop(slot, "diffuse_color_factor", text="")
            #row.label(text="Enable:")
            #row.prop(slot, "use_map_color_diffuse", text="")

        row = box.row()
        row.label(text="Enable Alpha:")
        row.prop(slot, "use_map_alpha", text="")
        if context.active_object and context.active_object.active_material:
            row.label(text="Transparent:")
            row.prop(context.active_object.active_material, "use_transparency", text="")
            

        box = layout.box()
        box.prop(slot, "offset", text="X,Y = offset.  Z=rotation")

        box = layout.box()
        box.prop(slot, "scale", text="Scale in X,Y.   (Z ignored)")

        box = layout.box()
        row = box.row()
        row.label(text='scrolling animation')
        #cant use if its enabled by default row.prop(slot, "use_map_density", text="")
        row.prop(slot, "use_map_scatter", text="")
        row = box.row()
        row.prop(slot, "density_factor", text="X")
        row.prop(slot, "emission_factor", text="Y")

        box = layout.box()
        row = box.row()
        row.label(text='rotation animation')
        row.prop(slot, "emission_color_factor", text="")
        row.prop(slot, "use_from_dupli", text="")



def find_uv_layer_index( material, uvname ):
    idx = 0
    for mesh in bpy.data.meshes:
        if material.name in mesh.materials:
            if mesh.uv_textures:
                names = [ uv.name for uv in mesh.uv_textures ]
                if uvname in names:
                    idx = names.index( uvname )
                    break   # should we check all objects using material and enforce the same index?
    return idx


def guess_uv_layer( layer ):    # DEPRECATED - this fails because the users will often change the UV name
    ## small issue: in blender layer is a string, multiple objects may have the same material assigned, 
    ## but having different named UVTex slots, most often the user will never rename these so they get
    ## named UVTex.000 etc...   assume this to always be true.
    idx = 0
    if '.' in layer:
        a = layer.split('.')[-1]
        if a.isdigit(): idx = int(a)+1
        else: print('WARNING: it is not allowed to give custom names to UVTexture channels ->', layer)
    return idx


###################


class _MatNodes_(object):       # Material Node methods
    def ancestors(self):
        if not self.parents: return []
        else: c = []; self._ancestors(c); return c
    def _ancestors(self, c):
        for p in self.parents: c.append( p ); p._ancestors( c )

    def decendents(self):
        if not self.children: return []
        else: c = []; self._decendents(c); return c
    def _decendents(self, c):
        for p in self.children: c.append( p ); p._decendents( c )

    def is_ogre_branch( self ):
        ancestors = []
        self._ancestors( ancestors )
        for parent in ancestors:
            if parent.node.name == ShaderTree.Output.name: return True
        print('node not in ogre branch', self.node)


    ## returns height sorted materials, 'passes' in Ogre speak ##
    # called after tree=ShaderTree.parse( nodedmat ); mats=tree.get_passes()
    def get_passes( self ):
        mats = []
        for mat in ShaderTree.Materials:
            print('            checking material ancestors:', mat)
            # only consider materials that are connected to the ogre Output
            #if self.Output in ancestors:
            if mat.is_ogre_branch():
                print('            material is in ogre branch->', mat)
                mats.append( mat )
        mats.sort( key=lambda x: x.node.location.y, reverse=True )
        if not mats: print('WARNING: no materials connected to Output node')
        ## collect and sort textures of a material ##
        for mat in mats:
            mat.textures = []
            d = mat.decendents()
            for child in d:
                if child.node.type == 'TEXTURE': mat.textures.append( child )
            mat.textures.sort( key=lambda x: x.node.location.y, reverse=True )
        return mats

    def get_texture_attributes(self):
        M = ''
        ops = {}
        for prop in self.node.texture.items():
            name,value = prop
            ops[name]=value
            M += indent(4, '%s %s' %prop )

        d = self.decendents()
        for child in d:
            if child.type == 'GEOMETRY' and child.node.uv_layer:
                idx = guess_uv_layer( child.node.uv_layer )
                M += indent(4, 'tex_coord_set %s' %idx)

            elif child.type == 'MAPPING':
                snode = child.node
                x,y,z = snode.location            # bpy bug, mapping node has two .location attrs
                if x or y:
                    M += indent(4, 'scroll %s %s' %(x,y))
                angle = math.degrees(snode.rotation.x)
                if angle:
                    M += indent(4, 'rotate %s' %angle)
                x,y,z = snode.scale
                if x != 1.0 or y != 1.0:
                    M += indent(4, 'scale %s %s' %(1.0/x,1.0/y))    # reported by Sanni and Reyn

        return M



class ShaderTree( _MatNodes_ ):

    Materials = []
    Output = None


    @staticmethod
    def is_valid_node_material( mat ):  # just incase the user enabled nodes but didn't do anything, then disabled nodes
        if mat.node_tree and len(mat.node_tree.nodes):
            for node in mat.node_tree.nodes:
                if node.type == 'MATERIAL':
                    if node.material: return True


    @staticmethod
    def parse( mat ):        # only called for noded materials
        print('        parsing node_tree')
        ShaderTree.Materials = []
        ShaderTree.Output = None
        outputs = []
        for link in mat.node_tree.links:
            if link.to_node and link.to_node.type == 'OUTPUT': outputs.append( link )

        root = None
        for link in outputs:
            if root is None or link.to_node.name.lower().startswith('ogre'): root = link
        if root:
            ShaderTree.Output = root.to_node
            print('setting Output node', root.to_node)
            #tree = ShaderTree( root.from_node, mat )
            #tree.parents.append( root.to_node )
            tree = ShaderTree( node=root.to_node, parent_material=mat )
            return tree
        else:
            print('warning: no Output shader node found')

    def __init__(self, node=None, material=None, parent_material=None ):
        if node: print('        shader node ->', node)
        if node and node.type.startswith('MATERIAL'):
            assert 0    # DEPRECATED - TODO clean up
            ShaderTree.Materials.append( self )
            self.material = node.material
        elif material:        # standard material
            self.material = material
            self.textures = []

        self.node = node
        if node:
            self.type = node.type
            self.name = node.name
        self.children = []
        self.parents = []
        self.inputs = {}        # socket name : child
        self.outputs = {}    # parent : socket name
        #if parent_material:
        if False:   # DEPRECATED - TODO cleanup
            for link in parent_material.node_tree.links:
                if link.to_node and link.to_node.name == self.name:
                    branch = ShaderTree(
                        node=link.from_node, 
                        parent_material=parent_material
                    )
                    self.children.append( branch )
                    self.inputs[ link.to_socket.name ] = branch
                    branch.outputs[ self ] = link.from_socket.name
                    branch.parents.append( self )


    def dotmat_texture(self, texture, texwrapper=None, slot=None):
        if not hasattr(texture, 'image'):
            print('WARNING: texture must be of type IMAGE->', texture)
            return ''
        if not texture.image:
            print('WARNING: texture has no image assigned->', texture)
            return ''
        #if slot: print(dir(slot))
        if slot and not slot.use: return ''

        path = OPTIONS['PATH']
        M = ''; _alphahack = None
        M += indent(3, 'texture_unit b2ogre_%s' %time.time(), '{' )

        if texture.library: # support library linked textures
            libpath = os.path.split( bpy.path.abspath(texture.library.filepath) )[0]
            iurl = bpy.path.abspath( texture.image.filepath, libpath )
        else:
            iurl = bpy.path.abspath( texture.image.filepath )

        postname = texname = os.path.split(iurl)[-1]
        destpath = path

        ## packed images - dec10th 2010 ##
        if texture.image.packed_file:
            orig = texture.image.filepath
            if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
                iurl = '/tmp/%s' %texname
            else:
                iurl = 'C:\\tmp\\%s' %texname
                if not os.path.isdir( 'C:\\tmp' ):
                    print('creating tmp directory' )
                    os.makedirs( 'C:\\tmp' )
            if not os.path.isfile( iurl ):
                print('MESSAGE: unpacking image: ', iurl)
                texture.image.filepath = iurl
                texture.image.save()
                texture.image.filepath = orig
            else:
                print('MESSAGE: packed image already in temp, not updating', iurl)

        if OPTIONS['FORCE_IMAGE_FORMAT']:
            postname = self._reformat( texname )        #texname.split('.')[0]+'.dds'
        #if OPTIONS['TEXTURES_SUBDIR']:
        #    destpath = os.path.join(path,'textures')
        #    if not os.path.isdir( destpath ): os.mkdir( destpath )
        #    M += indent(4, 'texture textures/%s' %postname )    
        #else: 
        M += indent(4, 'texture %s' %postname )    

        exmode = texture.extension
        if exmode == 'REPEAT':
            M += indent(4, 'tex_address_mode wrap' )
        elif exmode == 'EXTEND':
            M += indent(4, 'tex_address_mode clamp' )
        elif exmode == 'CLIP':
            M += indent(4, 'tex_address_mode border' )
        elif exmode == 'CHECKER':
            M += indent(4, 'tex_address_mode mirror' )

        if texwrapper:    # shader node options
            M += texwrapper.get_texture_attributes()

        elif slot:        # class blender material slot options
            if exmode == 'CLIP': M += indent(4, 'tex_border_colour %s %s %s' %(slot.color.r, slot.color.g, slot.color.b) )    
            M += indent(4, 'scale %s %s' %(1.0/slot.scale.x, 1.0/slot.scale.y) )    # thanks Reyn
            if slot.texture_coords != 'UV':
                if slot.mapping == 'SPHERE':
                    M += indent(4, 'env_map spherical' )
                elif slot.mapping == 'FLAT':
                    M += indent(4, 'env_map planar' )
                else: print('WARNING: <%s> has a non-UV mapping type (%s) and not picked a proper projection type of: Sphere or Flat' %(texture.name, slot.mapping))

            ox,oy,oz = slot.offset
            if ox or oy:
                M += indent(4, 'scroll %s %s' %(ox,oy) )
            if oz:
                M += indent(4, 'rotate %s' %oz )

            #if slot.use_map_emission:    # problem, user will want to use emission sometimes
            if slot.use_from_dupli:    # hijacked again - june7th
                M += indent(4, 'rotate_anim %s' %slot.emission_color_factor )
            if slot.use_map_scatter:    # hijacked from volume shaders
                M += indent(4, 'scroll_anim %s %s ' %(slot.density_factor, slot.emission_factor) )


            ## set uv layer
            if slot.uv_layer:
                idx = find_uv_layer_index( self.material, slot.uv_layer )
                #idx = guess_uv_layer( slot.uv_layer )
                M += indent(4, 'tex_coord_set %s' %idx)

            rgba = False
            if texture.image.depth == 32: rgba = True

            btype = slot.blend_type

            if rgba and slot.use_stencil:
                texop =     'blend_current_alpha'        # 'blend_texture_alpha' shadeless
            elif btype == 'MIX':
                texop = 'add_signed'    #'blend_manual'  # problem with blend manual it kills shading at 1.0
            elif btype == 'MULTIPLY':
                texop = 'modulate'
            elif btype == 'SCREEN':
                texop = 'modulate_x2'
            elif btype == 'LIGHTEN':
                texop = 'modulate_x4'
            elif btype == 'ADD':
                texop = 'add'
            elif btype == 'SUBTRACT':
                texop = 'subtract'
            elif btype == 'OVERLAY':
                texop = 'blend_manual'  #'add_signed'        
            elif btype == 'DIFFERENCE':
                texop = 'dotproduct'        # nothing closely matches blender
            else:
                texop = 'blend_diffuse_colour'

            # add_smooth not very useful?
            #factor = .0
            #if slot.use_map_color_diffuse:
            factor = 1.0 - slot.diffuse_color_factor

            #M += indent(4, 'alpha_op_ex source1 src_manual src_current %s' %factor )
            #M += indent(4, 'alpha_op_ex modulate src_texture src_manual %s' %factor )
            #M += indent(4, 'alpha_op_ex subtract src_manual src_current %s' %factor )

            if texop == 'blend_manual':
                M += indent(4, 'colour_op_ex %s src_current src_texture %s' %(texop, factor) )
            else:
                #M += indent(4, 'colour_op_ex %s src_manual src_current %s' %(texop, factor) )
                M += indent(4, 'colour_op_ex %s src_texture src_current' %texop )
                #M += indent(4, 'colour_op_ex blend_current_alpha src_texture src_current' )


                #M += indent(4, 'colour_op_ex %s src_manual src_diffuse %s' %(texop, 1.0-factor) )
                #M += indent(4, 'alpha_op_ex blend_manual src_current src_current %s' %factor )
            if slot.use_map_alpha:
                #alphafactor = 1.0 - slot.alpha_factor
                #M += indent(4, 'colour_op_ex blend_manual src_current src_texture %s' %factor )
                M += indent(4, 'alpha_op_ex modulate src_current src_texture' )


        #else:        # fallback to default options
        #    M += indent(4, 'filtering trilinear' )

        M += indent(3, '}' )    # end texture

        if OPTIONS['TOUCH_TEXTURES']:
            ## copy texture only if newer ##
            if not os.path.isfile( iurl ): Report.warnings.append( 'missing texture: %s' %iurl )
            else:
                desturl = os.path.join( destpath, texname )
                if not os.path.isfile( desturl ) or os.stat( desturl ).st_mtime < os.stat( iurl ).st_mtime:
                    f = open( desturl, 'wb' )
                    f.write( open(iurl,'rb').read() )
                    f.close()
                if OPTIONS['FORCE_IMAGE_FORMAT']:        # bug fix jan7th 2011
                    if OPTIONS['FORCE_IMAGE_FORMAT'] == '.dds': self.DDS_converter( desturl )
                    else: self.image_magick( desturl )

        return M


    ## this writes multiple passes ##
    def dotmat_pass(self):    # must be a standard-material
        if not self.material:
            print('ERROR: material node with no submaterial block chosen')
            return ''

        passes = []
        passes.append( self._helper_dotmat_pass( self.material ) )
        ########## Material Layers ###########
        if self.material.use_material_passes:
            nodes = get_or_create_material_passes( self.material )
            for i,node in enumerate(nodes):
                if node.material and node.material.use_in_ogre_material_pass:
                    s = self._helper_dotmat_pass(node.material, pass_name='b2ogre_pass%s'%str(i))
                    print( s )
                    passes.append( s )

        return '\n'.join( passes )

    def _helper_dotmat_pass( self, mat, pass_name=None ):
        color = mat.diffuse_color
        alpha = 1.0
        if mat.use_transparency: alpha = mat.alpha

        ## textures ##
        if not self.textures:        ## class style materials
            slots = get_image_textures( mat )        # returns texture_slot object
            print('*'*80)
            print('TEXTURE SLOTS', slots)
            print('*'*80)
            usealpha = False
            for slot in slots:
                if slot.use_map_alpha and slot.texture.use_alpha: usealpha = True; break
            if usealpha: alpha = 1.0    # reported by f00bar june 18th

        def _helper( child, opname, f ):        # python note, define inline function shares variables - copies?
            if child.type == 'RGB':
                print('warning: RGB shader node bpy rna is incomplete, missing color attributes' )
                return indent(3, '%s %s %s %s %s' %(opname, color.r*f, color.g*f, color.b*f, alpha) )
            elif child.type == 'GEOMETRY':
                if child.outputs[self] != 'Vertex Color': print('warning: you are supposed to connect the vertex color output of geometry')
                return indent(3, '%s vertexcolour' %opname)
            elif child.type == 'TEXTURE':
                print( 'TODO: connecting a texture to this slot will be supported for program-shaders in the future' )
                #return indent(3, '%s 1.0 0.0 0.0 1.0' %opname)
                return indent(3, '%s %s %s %s %s' %(opname, color.r*f, color.g*f, color.b*f, alpha) )

        M = ''
        if pass_name:
            M += indent(2, 'pass %s'%pass_name, '{' )

        elif self.node:        # ogre combines passes with the same name, be careful!   # TODO DEPRECATED
            passname = '%s__%s' %(self.node.name,material_name(mat))
            passname = passname.replace(' ','_')
            M += indent(2, 'pass %s' %passname, '{' )        # be careful with pass names
        else:
            M += indent(2, 'pass b2ogre_%s'%time.time(), '{' )

        #M += indent(3, 'cull_hardware none' )        # directx and opengl are reversed? TODO
        #if mat.ogre_disable_depth_write:
        #    M += indent(3, 'depth_write off' ) # once per pass (global attributes)

        if mat.use_fixed_pipeline:
            f = mat.ambient
            if 'Ambient' in self.inputs:
                child = self.inputs['Ambient']
                M += _helper( child, 'ambient', f )
            elif mat.use_vertex_color_paint:
                M += indent(3, 'ambient vertexcolour' )
            else:        # fall back to basic material
                M += indent(3, 'ambient %s %s %s %s' %(color.r*f, color.g*f, color.b*f, alpha) )

            f = mat.diffuse_intensity
            if 'Color' in self.inputs:
                child = self.inputs['Color']
                M += _helper( child, 'diffuse', f )
            elif mat.use_vertex_color_paint:
                M += indent(3, 'diffuse vertexcolour' )
            else:        # fall back to basic material 
                M += indent(3, 'diffuse %s %s %s %s' %(color.r*f, color.g*f, color.b*f, alpha) )

            f = mat.specular_intensity
            if 'Spec' in self.inputs:
                child = self.inputs['Spec']
                M += _helper( child, 'specular', f ) + ' %s'%(mat.specular_hardness/4.0)
            else:
                s = mat.specular_color
                M += indent(3, 'specular %s %s %s %s %s' %(s.r*f, s.g*f, s.b*f, alpha, mat.specular_hardness/4.0) )

            f = mat.emit        # remains valid even if material_ex inputs a color node
            if 'Emit' in self.inputs:
                child = self.inputs['Emit']
                M += _helper( child, 'emissive', f )
            elif mat.use_vertex_color_light:
                M += indent(3, 'emissive vertexcolour' )
            elif mat.use_shadeless:     # requested by Borris
                M += indent(3, 'emissive %s %s %s 1.0' %(color.r, color.g, color.b) )
            else:
                M += indent(3, 'emissive %s %s %s %s' %(color.r*f, color.g*f, color.b*f, alpha) )

        #M += indent( 3, 'scene_blend %s' %mat.ogre_scene_blend )
        for name in dir(mat):   #mat.items():
            if name.startswith('ogre_') and name != 'ogre_parent_material':
                var = getattr(mat,name)
                op = name.replace('ogre_', '')
                val = var
                if type(var) == bool:
                    if var: val = 'on'
                    else: val = 'off'
                M += indent( 3, '%s %s' %(op,val) )


        ## textures ##
        if not self.textures:        ## classic materials
            slots = get_image_textures( mat )        # returns texture_slot object
            usealpha = False
            for slot in slots:
                #if slot.use_map_alpha and slot.texture.use_alpha: usealpha = True; break
                if slot.use_map_alpha: usealpha = True; break
            if usealpha:
                if mat.use_transparency:
                    M += indent(3, 'depth_write off' ) # once per pass (global attributes)
            ## write shader programs before textures
            M += self._write_shader_programs( mat )
            for slot in slots: M += self.dotmat_texture( slot.texture, slot=slot )

        elif self.node:        # TODO redo shader nodes - new rule: unconnect only
            M += self._write_shader_programs( mat )
            for wrap in self.textures:
                M += self.dotmat_texture( wrap.node.texture, texwrapper=wrap )

        M += indent(2, '}' )    # end pass

        return M




    def _write_shader_programs( self, mat ):    # DEPRECATED TODO
        M = ''
        for prop in mat.items():
            name,val = prop
            if name in '_vprograms_ _fprograms_'.split():
                for progname in val:
                    if name=='_vprograms_':        # TODO over-ridden default params
                        M += indent( 3, 'vertex_program_ref %s' %progname, '{', '}' )
                    else:
                        M += indent( 3, 'fragment_program_ref %s' %progname, '{', '}' )
        return M




    ############################################
    def _reformat( self, image ): return image[ : image.rindex('.') ] + OPTIONS['FORCE_IMAGE_FORMAT']
    def image_magick( self, infile ):
        print('[Image Magick Wrapper]', infile )
        exe = CONFIG_IMAGE_MAGICK_CONVERT
        if not os.path.isfile( exe ):
            Report.warnings.append( 'ImageMagick not installed!' )
            print( 'ERROR: can not find Image Magick - convert', exe ); return
        path,name = os.path.split( infile )
        outfile = os.path.join( path, self._reformat( name ) )
        opts = [ infile, outfile ]
        subprocess.call( [exe]+opts )
        print( 'image magick->', outfile )

    EX_DDS_MIPS = 3    # default
    def DDS_converter(self, infile ):
        print('[NVIDIA DDS Wrapper]', infile )
        exe = CONFIG_NVIDIATOOLS_EXE
        if not os.path.isfile( exe ):
            Report.warnings.append( 'Nvidia DDS tools not installed!' )
            print( 'ERROR: can not find nvdxt.exe', exe ); return
        opts = '-quality_production -nmips %s -rescale nearest' %self.EX_DDS_MIPS
        path,name = os.path.split( infile )
        outfile = os.path.join( path, self._reformat( name ) )        #name.split('.')[0]+'.dds' )
        opts = opts.split() + ['-file', infile, '-output', '_tmp_.dds']
        if sys.platform.startswith('linux') or sys.platform.startswith('darwin'): subprocess.call( ['/usr/bin/wine', exe]+opts )
        else: subprocess.call( [exe]+opts )         ## TODO support OSX
        data = open( '_tmp_.dds', 'rb' ).read()
        f = open( outfile, 'wb' )
        f.write(data)
        f.close()






########################################
############### OgreMeshy ##############
class Ogre_ogremeshy_op(bpy.types.Operator):
    '''helper to open ogremeshy'''
    bl_idname = 'ogre.preview_ogremeshy'
    bl_label = "opens ogremeshy in a subprocess"
    bl_options = {'REGISTER'}
    preview = BoolProperty(name="preview", description="fast preview", default=True)
    groups = BoolProperty(name="preview merge groups", description="use merge groups", default=False)
    mesh = BoolProperty(name="update mesh", description="update mesh (disable for fast material preview", default=True)
    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type in ('MESH','EMPTY') and context.mode != 'EDIT_MESH':
            if context.active_object.type == 'EMPTY' and context.active_object.dupli_type != 'GROUP': return False
            else: return True

    def execute(self, context):
        Report.reset()
        Report.messages.append('running %s' %CONFIG_OGRE_MESHY)
        Report.messages.append('please wait...')
        Report.show()

        if sys.platform == 'linux2':
            path = '%s/.wine/drive_c/tmp' %os.environ['HOME']
        else:
            path = 'C:\\tmp'

        mat = None
        mgroup = merged = None
        umaterials = []
        
        if context.active_object.type == 'MESH': mat = context.active_object.active_material
        elif context.active_object.type == 'EMPTY':     # assume group
            obs = []
            for e in context.selected_objects:
                if e.type != 'EMPTY' and e.dupli_group: continue
                grp = e.dupli_group
                subs = []
                for o in grp.objects:
                    if o.type=='MESH': subs.append( o )
                if subs:
                    m = merge_objects( subs, transform=e.matrix_world )
                    obs.append( m )
            if obs:
                merged = merge_objects( obs )
                umaterials = dot_mesh( merged, path=path, force_name='preview' )
                for o in obs: context.scene.objects.unlink(o)

        
        if not self.mesh:
            for ob in context.selected_objects:
                if ob.type == 'MESH':
                    for mat in ob.data.materials:
                        if mat and mat not in umaterials: umaterials.append( mat )

        if not merged:
            mgroup = MeshMagick.get_merge_group( context.active_object )
            if not mgroup and self.groups:
                group = get_merge_group( context.active_object )
                if group:
                    print('--------------- has merge group ---------------' )
                    merged = merge_group( group )
                else:
                    print('--------------- NO merge group ---------------' )
            elif len(context.selected_objects)>1 and context.selected_objects:
                merged = merge_objects( context.selected_objects )

            if mgroup:
                for ob in mgroup.objects:
                    nmats = dot_mesh( ob, path=path, normals=not self.preview )
                    for m in nmats:
                        if m not in umaterials: umaterials.append( m )
                MeshMagick.merge( mgroup, path=path, force_name='preview' )
            elif merged:
                umaterials = dot_mesh( merged, path=path, force_name='preview' )
            else:
                umaterials = dot_mesh( context.active_object, path=path, force_name='preview' )

        if mat or umaterials:
            OPTIONS['TOUCH_TEXTURES'] = True
            OPTIONS['PATH'] = path
            data = ''
            for umat in umaterials:
                data += INFO_OT_createOgreExport.gen_dot_material( umat, path=path )
            f=open( os.path.join( path, 'preview.material' ), 'wb' )
            f.write( bytes(data,'utf-8') ); f.close()

        if merged: context.scene.objects.unlink( merged )

        if sys.platform == 'linux2':
            if CONFIG_OGRE_MESHY.endswith('.exe'):
                cmd = [CONFIG_OGRE_MESHY, 'c:\\tmp\\preview.mesh' ]
            else:
                cmd = [CONFIG_OGRE_MESHY, '/tmp/preview.mesh']
            print( cmd )
            #subprocess.call(cmd)
            subprocess.Popen(cmd)

        else:
            #subprocess.call([CONFIG_OGRE_MESHY, 'C:\\tmp\\preview.mesh'])
            subprocess.Popen( [CONFIG_OGRE_MESHY, 'C:\\tmp\\preview.mesh'] )

        return {'FINISHED'}



#############################

def wordwrap( txt ):
    r = ['']
    for word in txt.split(' '):    # do not split on tabs
        word = word.replace('\t', ' '*3)
        r[-1] += word + ' '
        if len(r[-1]) > 90: r.append( '' )
    return r



_OGRE_DOCS_ = []

def ogredoc( cls ):
    tag = cls.__name__.split('_ogredoc_')[-1]
    cls.bl_label = tag.replace('_', ' ')
    _OGRE_DOCS_.append( cls )
    return cls



class ogre_dot_mat_preview(bpy.types.Menu):
    bl_label = 'preview'
    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material
        if mat:
            OPTIONS['TOUCH_TEXTURES'] = False
            preview = INFO_OT_createOgreExport.gen_dot_material( mat )
            for line in preview.splitlines():
                if line.strip():
                    for ww in wordwrap( line ): layout.label(text=ww)


############ USED BY DOCS ##########
class INFO_MT_ogre_helper(bpy.types.Menu):
    bl_label = '_overloaded_'
    def draw(self, context):
        layout = self.layout
        #row = self.layout.box().split(percentage=0.05)
        #col = row.column(align=False)
        #print(dir(col))
        #row.scale_x = 0.1
        #row.alignment = 'RIGHT'

        for line in self.mydoc.splitlines():
            if line.strip():
                for ww in wordwrap( line ): layout.label(text=ww)
        layout.separator()


class INFO_MT_ogre_docs(bpy.types.Menu):
    bl_label = "Ogre Help"
    def draw(self, context):
        layout = self.layout
        for cls in _OGRE_DOCS_:
            layout.menu( cls.__name__ )
            layout.separator()
        layout.separator()
        layout.label(text='bug reports to: bhartsho@yahoo.com')

class INFO_MT_ogre_shader_pass_attributes(bpy.types.Menu):
    bl_label = "Shader-Pass"
    def draw(self, context):
        layout = self.layout
        for cls in _OGRE_SHADER_REF_:
            layout.menu( cls.__name__ )

class INFO_MT_ogre_shader_texture_attributes(bpy.types.Menu):
    bl_label = "Shader-Texture"
    def draw(self, context):
        layout = self.layout
        for cls in _OGRE_SHADER_REF_TEX_:
            layout.menu( cls.__name__ )


@ogredoc
class _ogredoc_Installing( INFO_MT_ogre_helper ):
    mydoc = _doc_installing_

@ogredoc
class _ogredoc_FAQ( INFO_MT_ogre_helper ):
    mydoc = _faq_

@ogredoc
class _ogredoc_Exporter_Features( INFO_MT_ogre_helper ):
    mydoc = '''
Ogre Exporter Features:
    Export .scene:
        pos, rot, scl
        environment colors
        fog settings
        lights, colors
        array modifier (constant offset only)
        optimize instances
        selected only
        force cameras
        force lamps
        BGE physics
        collisions prims and external meshes

    Export .mesh

        verts, normals, uv
        LOD (Ogre Command Line Tools)
        export `meshes` subdirectory
        bone weights
        shape animation (using NLA-hijacking)

    Export .material
        diffuse color
        ambient intensity
        emission
        specular
        receive shadows on/off
        multiple materials per mesh
        exports `textures` subdirectory

    Export .skeleton
        bones
        animation
        multi-tracks using NLA-hijacking
'''



_ogre_doc_classic_textures_ = '''
==Supported Blending Modes:==
    * Mix                - blend_manual -
    * Multiply        - modulate -
    * Screen            - modulate_x2 -
    * Lighten        - modulate_x4 -
    * Add                - add -
    * Subtract        - subtract -
    * Overlay        - add_signed -
    * Difference    - dotproduct -

==Mapping Types:==
    * UV
    * Sphere environment mapping
    * Flat environment mapping

==Animation:==
    * scroll animation
    * rotation animation
'''

@ogredoc
class _ogredoc_Texture_Options( INFO_MT_ogre_helper ):
    mydoc = _ogre_doc_classic_textures_



@ogredoc
class _ogredoc_Animation_System( INFO_MT_ogre_helper ):
    mydoc = '''
Armature Animation System | OgreDotSkeleton
    Quick Start:
        1. select your armature and set a single keyframe on the object (loc,rot, or scl)
            . note, this step is just a hack for creating an action so you can then create an NLA track.
            . do not key in pose mode, unless you want to only export animation on the keyed bones.
        2. open the NLA, and convert the action into an NLA strip
        3. name the NLA strip(s)
        4. set the in and out frames for each strip ( the strip name becomes the Ogre track name )

    How it Works:
        The NLA strips can be blank, they are only used to define Ogre track names, and in and out frame ranges.  You are free to animate the armature with constraints (no baking required), or you can used baked animation and motion capture.  Blending that is driven by the NLA is also supported, if you don't want blending, put space between each strip.

    The OgreDotSkeleton (.skeleton) format supports multiple named tracks that can contain some or all of the bones of an armature.  This feature can be exploited by a game engine for segmenting and animation blending.  For example: lets say we want to animate the upper torso independently of the lower body while still using a single armature.  This can be done by hijacking the NLA of the armature.

    Advanced NLA Hijacking (selected-bones-animation):
        . define an action and keyframe only the bones you want to 'group', ie. key all the upper torso bones
        . import the action into the NLA
        . name the strip (this becomes the track name in Ogre)
        . adjust the start and end frames of each strip
        ( you may use multiple NLA tracks, multiple strips per-track is ok, and strips may overlap in time )

'''


@ogredoc
class _ogredoc_Physics( INFO_MT_ogre_helper ):
    mydoc = '''
Ogre Dot Scene + BGE Physics
    extended format including external collision mesh, and BGE physics settings
<node name="...">
    <entity name="..." meshFile="..." collisionFile="..." collisionPrim="..." [and all BGE physics attributes] />
</node>

collisionFile : sets path to .mesh that is used for collision (ignored if collisionPrim is set)
collisionPrim : sets optimal collision type [ cube, sphere, capsule, cylinder ]
*these collisions are static meshes, animated deforming meshes should give the user a warning that they have chosen a static mesh collision type with an object that has an armature

Blender Collision Setup:
    1. If a mesh object has a child mesh with a name starting with 'collision', then the child becomes the collision mesh for the parent mesh.

    2. If 'Collision Bounds' game option is checked, the bounds type [box, sphere, etc] is used. This will override above rule.

    3. Instances (and instances generated by optimal array modifier) will share the same collision type of the first instance, you DO NOT need to set the collision type for each instance.

    Tips and Tricks:
        . instance your mesh, parent it under the source, add a Decimate modifier, set the draw type to wire.  boom! easy optimized collision mesh
        . sphere collision type is the fastest

    TODO support composite collision objects?

'''

@ogredoc
class _ogredoc_Warnings( INFO_MT_ogre_helper ):
    mydoc = '''
Warnings:
    . extra vertex groups, can mess up an armature weights (new vgroups must come after armature assignment, not before)
    . quadratic lights falloff not supported (needs pre calc)
    . do not enable subsurf modifier on meshes that have shape or armature animation.  
        (Any modifier that changes the vertex count is bad with shape anim or armature anim)

'''


@ogredoc
class _ogredoc_Bugs( INFO_MT_ogre_helper ):
    mydoc = '''
Known Issues:
    . shape animation breaks when using modifiers that change the vertex count

'''



############ Ogre v.17 Doc ######

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
    ## custom user props ##
    for prop in mesh.items():
        propname, propvalue = prop
        if not propname.startswith('_'):
            user = doc.createElement('user_data')
            o.appendChild( user )
            user.setAttribute( 'name', propname )
            user.setAttribute( 'value', str(propvalue) )
            user.setAttribute( 'type', type(propvalue).__name__ )


# Ogre supports .dds in both directx and opengl
# http://www.ogre3d.org/forums/viewtopic.php?f=5&t=46847
IMAGE_FORMATS = {
    'dds',
    'png',
    'jpg',
}

#class _type(bpy.types.IDPropertyGroup):
#    name = StringProperty(name="jpeg format", description="", maxlen=64, default="")

OptionsEx = {
    'mesh-sub-dir' : False,
    'shape-anim' : True,
    'trim-bone-weights' : 0.01,
    'armature-anim' : True,

    'lodLevels' : 0,
    'lodDistance' : 100,
    'lodPercent' : 40,
    'nuextremityPoints' : 0,
    'generateEdgeLists' : False,

    'generateTangents' : False,
    'tangentSemantic' : "uvw", 
    'tangentUseParity' : 4,
    'tangentSplitMirrored' : False,
    'tangentSplitRotated' : False,
    'reorganiseBuffers' : True,
    'optimiseAnimations' : True,

}



class _TXML_(object):

    '''
  <component type="EC_Script" sync="1" name="myscript">
   <attribute value="" name="Script ref"/>
   <attribute value="false" name="Run on load"/>
   <attribute value="0" name="Run mode"/>
   <attribute value="" name="Script application name"/>
   <attribute value="" name="Script class name"/>
  </component>
    '''


    def create_tundra_document( self, context ):
        proto = 'local://'      # antont says file:// is also valid

        doc = RDocument()
        scn = doc.createElement('scene')
        doc.appendChild( scn )

        if 0:       # Tundra bug
            e = doc.createElement( 'entity' )
            doc.documentElement.appendChild( e )
            e.setAttribute('id', len(doc.documentElement.childNodes)+1 )

            c = doc.createElement( 'component' ); e.appendChild( c )
            c.setAttribute( 'type', 'EC_Script' )
            c.setAttribute( 'sync', '1' )
            c.setAttribute( 'name', 'myscript' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Script ref')
            #a.setAttribute('value', "%s%s"%(proto,TUNDRA_GEN_SCRIPT_PATH) )
            
            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Run on load')
            a.setAttribute('value', 'true' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Run mode')
            a.setAttribute('value', '0' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Script application name')
            a.setAttribute('value', 'blender2ogre' )


        if context.scene.world.ogre_skyX:

            ############### environment light ################
            e = doc.createElement( 'entity' )
            doc.documentElement.appendChild( e )
            e.setAttribute('id', len(doc.documentElement.childNodes)+1 )

            c = doc.createElement( 'component' ); e.appendChild( c )
            c.setAttribute( 'type', 'EC_EnvironmentLight' )
            c.setAttribute( 'sync', '1' )
            c.setAttribute( 'name', 'blender-environment-light' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Sun color')
            a.setAttribute('value', '0.638999999 0.638999999 0.638999999 1')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Ambient color')
            a.setAttribute('value', '0.363999993 0.363999993 0.363999993 1')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Sun diffuse color')
            a.setAttribute('value', '0.930000007 0.930000007 0.930000007 1')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Sun direction vector')
            a.setAttribute('value', '-1.0 -1.0 -1.0')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Use fixed time')
            a.setAttribute('value', 'false')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Current time')
            a.setAttribute('value', '0.67')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Sun cast shadows')
            a.setAttribute('value', 'true')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Use Caelum')
            a.setAttribute('value', 'true')

            ################# SKYX ################
            c = doc.createElement( 'component' ); e.appendChild( c )
            c.setAttribute( 'type', 'EC_SkyX' )
            c.setAttribute( 'sync', '1' )
            c.setAttribute( 'name', 'myskyx' )

            a = doc.createElement('attribute'); a.setAttribute('name', 'Weather (volumetric clouds only)')
            den = (
                context.scene.world.ogre_skyX_cloud_density_x, 
                context.scene.world.ogre_skyX_cloud_density_y
            )
            a.setAttribute('value', '%s %s' %den)
            c.appendChild( a )

            config = (
                ('time', 'Time multiplier'), 
                ('volumetric_clouds','Volumetric clouds'), 
                ('wind','Wind direction'),
            )
            for bname, aname in config:
                a = doc.createElement('attribute')
                a.setAttribute('name', aname)
                s = str( getattr(context.scene.world, 'ogre_skyX_'+bname) )
                a.setAttribute('value', s.lower())
                c.appendChild( a )

        return doc

    ########################################
    def tundra_entity( self, doc, ob, path='/tmp', collision_proxies=[] ):
        assert not ob.subcollision
        # txml has flat hierarchy
        e = doc.createElement( 'entity' )
        doc.documentElement.appendChild( e )
        e.setAttribute('id', len(doc.documentElement.childNodes)+1 )

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Name")
        c.setAttribute('sync', '1')
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "name" )
        a.setAttribute('value', ob.name )
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "description" )
        a.setAttribute('value', "" )


        ############ Tundra TRANSFORM ####################
        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Placeable")
        c.setAttribute('sync', '1')
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Transform" )
        x,y,z = swap(ob.matrix_world.to_translation())
        loc = '%6f,%6f,%6f' %(x,y,z)
        x,y,z = swap(ob.matrix_world.to_euler())
        x = math.degrees( x ); y = math.degrees( y ); z = math.degrees( z )
        rot = '%6f,%6f,%6f' %(x,y,z)
        x,y,z = swap(ob.matrix_world.to_scale())
        scl = '%6f,%6f,%6f' %(abs(x),abs(y),abs(z))		# Tundra2 clamps any negative to zero
        a.setAttribute('value', "%s,%s,%s" %(loc,rot,scl) )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Show bounding box" )
        if ob.show_bounds or ob.type != 'MESH': a.setAttribute('value', "true" )
        else: a.setAttribute('value', "false" )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Visible" )
        a.setAttribute('value', 'true')

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Selection layer" )
        a.setAttribute('value', 1)

        #<attribute value="1" name="Selection layer"/>
        #<attribute value="" name="Parent entity ref"/>
        #<attribute value="" name="Parent bone name"/>

        if ob.type != 'MESH':
            c = doc.createElement('component'); e.appendChild( c )
            c.setAttribute('type', 'EC_TransformGizmo')
            c.setAttribute('sync', '1')

        if ob.type == 'CAMERA':
            c = doc.createElement('component'); e.appendChild( c )
            c.setAttribute('type', 'EC_Camera')
            c.setAttribute('sync', '1')

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Up vector" )
            a.setAttribute('value', '0.0 1.0 0.0')

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Near plane" )
            a.setAttribute('value', '0.01')

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Far plane" )
            a.setAttribute('value', '2000')

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Vertical FOV" )
            a.setAttribute('value', '45')

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Aspect ratio" )
            a.setAttribute('value', '')


        ## any object can have physics ##
        #if ob.game.physics_type == 'RIGID_BODY':
        #if not ob.game.use_ghost and ob.game.physics_type in 'RIGID_BODY SENSOR'.split():
        NTF = None

        if ob.physics_mode != 'NONE' or ob.collision_mode != 'NONE':
            TundraTypes = {
                'BOX' : 0,
                'SPHERE' : 1,
                'CYLINDER' : 2,
                'CONE' : 0,    # tundra is missing
                'CAPSULE' : 3,
                'TRIANGLE_MESH' : 4,
                #'HEIGHT_FIELD': 5, #blender is missing
                'CONVEX_HULL' : 6
            }


            com = doc.createElement('component'); e.appendChild( com )
            com.setAttribute('type', 'EC_RigidBody')
            com.setAttribute('sync', '1')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Mass')
            if ob.physics_mode == 'RIGID_BODY':
                a.setAttribute('value', ob.game.mass)
            else:
                a.setAttribute('value', '0.0')  # disables physics in Tundra?


            SHAPE = a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Shape type')
            a.setAttribute('value', TundraTypes[ ob.game.collision_bounds_type ] )

            M = ob.game.collision_margin
            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Size')
            if ob.game.collision_bounds_type in 'TRIANGLE_MESH CONVEX_HULL'.split():
                a.setAttribute('value', '%s %s %s' %(1.0+M, 1.0+M, 1.0+M) )
            else:
                #x,y,z = swap(ob.matrix_world.to_scale())
                x,y,z = swap(ob.dimensions)
                a.setAttribute('value', '%s %s %s' %(abs(x)+M,abs(y)+M,abs(z)+M) )

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Collision mesh ref')
            #if ob.game.use_collision_compound:
            if ob.collision_mode == 'DECIMATED':
                proxy = None
                for child in ob.children:
                    if child.subcollision and child.name.startswith('DECIMATED'):
                        proxy = child; break
                if proxy:
                    a.setAttribute('value', 'local://_collision_%s.mesh' %proxy.data.name)
                    if proxy not in collision_proxies: collision_proxies.append( proxy )
                else:
                    print( 'WARN: collision proxy mesh not found' )
                    assert 0

            elif ob.collision_mode == 'TERRAIN':
                NTF = save_terrain_as_NTF( path, ob )
                SHAPE.setAttribute( 'value', '5' )  # HEIGHT_FIELD

            elif ob.type == 'MESH':
                a.setAttribute('value', 'local://%s.mesh' %ob.data.name)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Friction')
            #avg = sum( ob.game.friction_coefficients ) / 3.0
            a.setAttribute('value', ob.physics_friction)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Restitution')
            a.setAttribute('value', ob.physics_bounce)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Linear damping')
            a.setAttribute('value', ob.game.damping)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Angular damping')
            a.setAttribute('value', ob.game.rotation_damping)


            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Linear factor')
            a.setAttribute('value', '1.0 1.0 1.0')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Angular factor')
            a.setAttribute('value', '1.0 1.0 1.0')


            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Kinematic')
            a.setAttribute('value', 'false' )

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Phantom')        # this must mean no-collide
            if ob.collision_mode == 'NONE':
                a.setAttribute('value', 'true' )
            else:
                a.setAttribute('value', 'false' )

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Draw Debug')
            if ob.collision_mode == 'NONE':
                a.setAttribute('value', 'false' )
            else:
                a.setAttribute('value', 'true' )


            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Linear velocity')
            a.setAttribute('value', '0.0 0.0 0.0')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Angular velocity')
            a.setAttribute('value', '0.0 0.0 0.0')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Collision Layer')
            a.setAttribute('value', -1)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Collision Mask')
            a.setAttribute('value', -1)

        if NTF:     # Terrain
            xp = NTF['xpatches']
            yp = NTF['ypatches']
            depth = NTF['depth']
            com = doc.createElement('component'); e.appendChild( com )
            com.setAttribute('type', 'EC_Terrain')
            com.setAttribute('sync', '1')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Transform')
            x,y,z = ob.dimensions
            sx,sy,sz = ob.scale
            x *= 1.0/sx
            y *= 1.0/sy
            z *= 1.0/sz
            #trans = '%s,%s,%s,' %(-xp/4, -z/2, -yp/4)
            trans = '%s,%s,%s,' %(-xp/4, -depth, -yp/4)
            # scaling in Tundra happens after translation
            nx = x/(xp*16)
            ny = y/(yp*16)
            trans += '0,0,0,%s,%s,%s' %(nx,depth, ny)
            a.setAttribute('value', trans )

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Grid Width')
            a.setAttribute('value', xp)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Grid Height')
            a.setAttribute('value', yp)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Tex. U scale')
            a.setAttribute('value', 1.0)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Tex. V scale')
            a.setAttribute('value', 1.0)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Material')
            a.setAttribute('value', '')

            for i in range(4):
                a = doc.createElement('attribute'); com.appendChild( a )
                a.setAttribute('name', 'Texture %s' %i)
                a.setAttribute('value', '')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Heightmap')
            a.setAttribute('value', NTF['name'] )


        return e


    def tundra_mesh( self, e, ob, url, exported_meshes ):
        if self.EX_MESH:
            murl = os.path.join( os.path.split(url)[0], '%s.mesh'%ob.data.name )
            exists = os.path.isfile( murl )
            if not exists or (exists and self.EX_MESH_OVERWRITE):
                if ob.data.name not in exported_meshes:
                    if '_update_mesh_' in ob.data.keys() and not ob.data['_update_mesh_']: print('    skipping', ob.data)
                    else:
                        exported_meshes.append( ob.data.name )
                        self.dot_mesh( ob, os.path.split(url)[0] )



        doc = e.document
        proto = 'local://'      # antont says file:// is also valid

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Mesh")
        c.setAttribute('sync', '1')

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Mesh ref" )
        a.setAttribute('value', "%s%s.mesh"%(proto,ob.data.name) )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Mesh materials" )
        #a.setAttribute('value', "%s%s.material"%(proto,bpy.context.scene.name) )       # pre-pforces-patch
        # Query object its materials and make a proper material ref string of it.
        # note: We assume blindly here that the 'submesh' indexes are correct in the material list.
        #       the most common usecase is to have one material per object for rex artists.
        #       They can now assign multiple and they will at least go to the .txml data but I cant
        #       guarantee that they are in correct submesh index slots! At least they have the refs and 
        #       can manually shift them around in the viewer.
        mymaterials = ob.data.materials
        if mymaterials is not None and len(mymaterials) > 0:
            mymatstring = ''
            # generate ; separated material list
            for mymat in mymaterials: 
                if mymat is None:
                    continue
                mymatstring += proto + material_name(mymat) + '.material;'
            mymatstring = mymatstring[:-1]  # strip ending ;
            a.setAttribute('value', mymatstring )
        else:
            # default to nothing to avoid error prints in .txml import
            a.setAttribute('value', "" ) 

        if ob.find_armature():
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Skeleton ref" )
            a.setAttribute('value', "%s%s.skeleton"%(proto,ob.data.name) )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Draw distance" )
        a.setAttribute('value', "0" )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Cast shadows" )	# cast shadows is per object? not per material?
        a.setAttribute('value', "false" )

    def tundra_light( self, e, ob ):
        '''
          <component type="EC_Light" sync="1" name="mylight">
           <attribute value="0.000000 0.000000 1.000000" name="direction"/>
           <attribute value="0" name="light type"/>
           <attribute value="1 1 1 1" name="diffuse color"/>
           <attribute value="0 0 0 1" name="specular color"/>
           <attribute value="false" name="cast shadows"/>
           <attribute value="100" name="light range"/>
           <attribute value="0" name="constant atten"/>
           <attribute value="0.00999999978" name="linear atten"/>
           <attribute value="0.00999999978" name="quadratic atten"/>
           <attribute value="30" name="light inner angle"/>
           <attribute value="40" name="light outer angle"/>
          </component>
        '''
        doc = e.document

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Light")
        c.setAttribute('sync', '1')

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'direction' )
        a.setAttribute('value', '0.0 0.0 1.0' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'light type' )
        a.setAttribute('value', '0' )

        R,G,B = ob.data.color
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'diffuse color' )
        if ob.data.use_diffuse: a.setAttribute('value', '%s %s %s 1' %(R,G,B) )
        else: a.setAttribute('value', '0 0 0 1' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'specular color' )
        if ob.data.use_specular: a.setAttribute('value', '%s %s %s 1' %(R,G,B) )
        else: a.setAttribute('value', '0 0 0 1' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'cast shadows' )
        if ob.data.type=='HEMI': a.setAttribute('value', 'false' ) # HEMI reported by Reyn
        elif ob.data.shadow_method != 'NOSHADOW': a.setAttribute('value', 'true' )
        else: a.setAttribute('value', 'false' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'light range' )
        a.setAttribute('value', ob.data.distance*2 )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'constant atten' )
        a.setAttribute('value', '0' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'linear atten' )
        #a.setAttribute('value', (1.0/ob.data.distance)*ob.data.energy )
        a.setAttribute('value', 0.05*ob.data.energy )   # sane default

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'quadratic atten' )
        a.setAttribute('value', '0.0' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'light inner angle' )
        a.setAttribute('value', '30' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'light outer angle' )
        a.setAttribute('value', '40' )

class _OgreCommonExport_( _TXML_ ):
    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        wm = context.window_manager
        fs = wm.fileselect_add(self)        # writes to filepath
        return {'RUNNING_MODAL'}
    def execute(self, context): self.ogre_export(  self.filepath, context ); return {'FINISHED'}

    EX_SEP_MATS = BoolProperty(
        name="Separate Materials", 
        description="exports a .material for each material (rather than putting all materials in a single .material file)", 
        default=True)

    _image_formats =  [
        ('','do not convert', 'default'),
        ('jpg', 'jpg', 'jpeg format'),
        ('png', 'png', 'png format'),
        ('dds', 'dds', 'nvidia dds format'),
    ]


    filepath = StringProperty(name="File Path", description="Filepath used for exporting file", maxlen=1024, default="", subtype='FILE_PATH')
    #EXPORT_TYPE = 'OGRE'   # defined in subclass
    EX_ONLY_ANIMATED_BONES = BoolProperty(
        name="Only Animated Bones", 
        description="only exports bones that have been keyframed, useful for run-time animation blending (example: upper/lower torso split)", 
        default=False)

    EX_SCENE = BoolProperty(name="Export Scene", description="export current scene (OgreDotScene xml)", default=True)
    EX_SELONLY = BoolProperty(name="Export Selected Only", description="export selected", default=True)
    EX_FORCE_CAMERA = BoolProperty(name="Force Camera", description="export active camera", default=True)
    EX_FORCE_LAMPS = BoolProperty(name="Force Lamps", description="export all lamps", default=True)
    EX_MESH = BoolProperty(name="Export Meshes", description="export meshes", default=True)
    EX_MESH_OVERWRITE = BoolProperty(name="Export Meshes (overwrite)", description="export meshes (overwrite existing files)", default=True)
    EX_ANIM = BoolProperty(name="Armature Animation", description="export armature animations - updates the .skeleton file", default=True)
    EX_SHAPE_ANIM = BoolProperty(name="Shape Animation", description="export shape animations - updates the .mesh file", default=True)
    EX_INSTANCES = BoolProperty(name="Optimize Instances", description="optimize instances in OgreDotScene xml", default=True)
    EX_ARRAY = BoolProperty(name="Optimize Arrays", description="optimize array modifiers as instances (constant offset only)", default=True)
    EX_MATERIALS = BoolProperty(name="Export Materials", description="exports .material script", default=True)

    EX_FORCE_IMAGE = EnumProperty( items=_image_formats, name='Convert Images',  description='convert all textures to format', default='' )
    EX_DDS_MIPS = IntProperty(name="DDS Mips", description="number of mip maps (DDS)", default=3, min=0, max=16)
    EX_TRIM_BONE_WEIGHTS = FloatProperty(name="Trim Weights", description="ignore bone weights below this value\n(Ogre may only support 4 bones per vertex", default=0.01, min=0.0, max=0.1)
    ## Mesh Options ##
    lodLevels = IntProperty(name="LOD Levels", description="MESH number of LOD levels", default=0, min=0, max=32)
    lodDistance = IntProperty(name="LOD Distance", description="MESH distance increment to reduce LOD", default=100, min=0, max=2000)
    lodPercent = IntProperty(name="LOD Percentage", description="LOD percentage reduction", default=40, min=0, max=99)
    nuextremityPoints = IntProperty(name="Extremity Points", description="MESH Extremity Points", default=0, min=0, max=65536)
    generateEdgeLists = BoolProperty(name="Edge Lists", description="MESH generate edge lists (for stencil shadows)", default=False)
    generateTangents = BoolProperty(name="Tangents", description="MESH generate tangents", default=False)
    tangentSemantic = StringProperty(name="Tangent Semantic", description="MESH tangent semantic", maxlen=3, default="uvw")
    tangentUseParity = IntProperty(name="Tangent Parity", description="MESH tangent use parity", default=4, min=0, max=16)
    tangentSplitMirrored = BoolProperty(name="Tangent Split Mirrored", description="MESH split mirrored tangents", default=False)
    tangentSplitRotated = BoolProperty(name="Tangent Split Rotated", description="MESH split rotated tangents", default=False)
    reorganiseBuffers = BoolProperty(name="Reorganise Buffers", description="MESH reorganise vertex buffers", default=True)
    optimiseAnimations = BoolProperty(name="Optimize Animations", description="MESH optimize animations", default=True)



    def dot_material( self, meshes, path='/tmp', mat_file_name='SceneMaterial'):
        material_files = []
        mats = []
        for ob in meshes:
            if len(ob.data.materials):
                for mat in ob.data.materials:
                    if mat not in mats: mats.append( mat )

        if not mats:
            print('WARNING: no materials, not writting .material script'); return []

        M = MISSING_MATERIAL + '\n'
        for mat in mats:
            if mat is None: continue
            Report.materials.append( material_name(mat) )
            data = self.gen_dot_material( mat, path, convert_textures=True )
            M += data
            if self.EX_SEP_MATS:
                url = self.dot_material_write_separate( mat, data, path )
                material_files.append( url )

        if not self.EX_SEP_MATS:
            url = os.path.join(path, '%s.material' % mat_file_name)
            f = open( url, 'wb' ); f.write( bytes(M,'utf-8') ); f.close()
            print('saved', url)
            material_files.append( url )

        return material_files

    def dot_material_write_separate( self, mat, data, path = '/tmp' ):      # thanks Pforce
        url = os.path.join(path, '%s.material' % material_name(mat))
        f = open(url, 'wb'); f.write( bytes(data,'utf-8') ); f.close()
        print('saved', url)
        return url



    @classmethod
    def gen_dot_material( self, mat, path='/tmp', convert_textures=False ):

        safename = material_name(mat)     # supports blender library linking
        M = '// blender material: %s\n' %(mat.name)
        if mat.ogre_parent_material:    ## NEW: script inheritance
            assert mat.ogre_parent_material in _OGRE_MATERIAL_CLASS_SCRIPT
            dotmaterial = _OGRE_MATERIAL_CLASS_SCRIPT[ mat.ogre_parent_material ]
            M += 'import %s from "%s"\n' %(mat.ogre_parent_material, dotmaterial)
            M += 'material %s : %s \n{\n' %(safename, mat.ogre_parent_material)
        else: M += 'material %s \n{\n'        %safename

        if mat.use_shadows: M += indent(1, 'receive_shadows on')
        else: M += indent(1, 'receive_shadows off')

        M += indent(1, 'technique b2ogre_%s'%time.time(), '{' )    # technique GLSL
        M += self.gen_dot_material_pass( mat, path, convert_textures )
        M += indent(1, '}' )    # end technique

        M += '}\n'    # end material
        return M

    @classmethod
    def gen_dot_material_pass( self, mat, path, convert_textures ):
        print('GEN DOT MATERIAL...', mat)
        OPTIONS['PATH'] = path
        M = ''
        print('        STANDARD MATERIAL')
        tree = ShaderTree( material=mat )
        M += tree.dotmat_pass()
        return M



    def dot_mesh( self, ob, path='/tmp', force_name=None, ignore_shape_animation=False ):
        opts = {
            #'mesh-sub-dir' : self.EX_MESH_SUBDIR,
            'shape-anim' : self.EX_SHAPE_ANIM,
            'trim-bone-weights' : self.EX_TRIM_BONE_WEIGHTS,
            'armature-anim' : self.EX_ANIM,
            'lodLevels' : self.lodLevels,
            'lodDistance' : self.lodDistance,
            'lodPercent' : self.lodPercent,
            'nuextremityPoints' : self.nuextremityPoints,
            'generateEdgeLists' : self.generateEdgeLists,
            'generateTangents' : self.generateTangents,
            'tangentSemantic' : self.tangentSemantic, 
            'tangentUseParity' : self.tangentUseParity,
            'tangentSplitMirrored' : self.tangentSplitMirrored,
            'tangentSplitRotated' : self.tangentSplitRotated,
            'reorganiseBuffers' : self.reorganiseBuffers,
            'optimiseAnimations' : self.optimiseAnimations,
        }
        dot_mesh( ob, path, force_name, ignore_shape_animation=False, opts=opts )



    def ogre_export(self, url, context ):
        global OPTIONS
        OPTIONS['FORCE_IMAGE_FORMAT'] = None
        OPTIONS['TOUCH_TEXTURES'] = True
        OPTIONS['SWAP_AXIS'] = self.EX_SWAP_MODE
        OPTIONS['ONLY_ANIMATED_BONES'] = self.EX_ONLY_ANIMATED_BONES
        Report.reset()

        ShaderTree.EX_DDS_MIPS = self.EX_DDS_MIPS

        if self.EX_FORCE_IMAGE:
            fmt = self.EX_FORCE_IMAGE.lower()
            if not fmt.startswith('.'): fmt = '.'+fmt
            OPTIONS['FORCE_IMAGE_FORMAT'] = fmt


        print('ogre export->', url)
        prefix = url.split('.')[0]
        path = os.path.split(url)[0]

        ## nodes (objects) ##
        objects = []        # gather because macros will change selection state
        linkedgroups = []
        for ob in bpy.context.scene.objects:
            if ob.subcollision: continue
            if self.EX_SELONLY and not ob.select:
                if ob.type == 'CAMERA' and self.EX_FORCE_CAMERA: pass
                elif ob.type == 'LAMP' and self.EX_FORCE_LAMPS: pass
                else: continue
            if ob.type == 'EMPTY' and ob.dupli_group and ob.dupli_type == 'GROUP': 
                linkedgroups.append( ob )
            else: objects.append( ob )

        ######## LINKED GROUPS - allows 3 levels of nested blender library linking ########
        temps = []
        for e in linkedgroups:
            grp = e.dupli_group
            subs = []
            for o in grp.objects:
                if o.type=='MESH': subs.append( o )
                elif o.type == 'EMPTY' and o.dupli_group and o.dupli_type == 'GROUP':
                    for oo in o.dupli_group.objects:
                        if oo.type=='MESH': subs.append( oo )
                        elif oo.type == 'EMPTY' and oo.dupli_group and oo.dupli_type == 'GROUP':
                            for ooo in oo.dupli_group.objects:
                                if ooo.type=='MESH': subs.append( ooo )

            if subs:
                m = merge_objects( subs, name=e.name, transform=e.matrix_world )
                objects.append( m )
                temps.append( m )


        ## find merge groups
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

        ## gather roots because ogredotscene supports parents and children ##
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
            if root not in roots: roots.append( root )

            if ob.type=='MESH': meshes.append( ob )

        mesh_collision_prims = {}
        mesh_collision_files = {}

        exported_meshes = []        # don't export same data multiple times

        if self.EX_MATERIALS:
            material_file_name_base=os.path.split(url)[1].replace('.scene', '').replace('.txml', '')
            material_files = self.dot_material( meshes, path, material_file_name_base)
        else:
            material_files = []


        if self.EXPORT_TYPE == 'REX':
            ################# TUNDRA #################
            rex = self.create_tundra_document( context )
            ##########################################
            proxies = []
            for ob in objects:
                TE = self.tundra_entity( rex, ob, path=path, collision_proxies=proxies )
                if ob.type == 'MESH' and len(ob.data.faces):
                    self.tundra_mesh( TE, ob, url, exported_meshes )
                    #meshes.append( ob )
                elif ob.type == 'LAMP':
                    self.tundra_light( TE, ob )


            for proxy in proxies:
                self.dot_mesh( 
                    proxy, 
                    path=os.path.split(url)[0], 
                    force_name='_collision_%s' %proxy.data.name
                )


            if self.EX_SCENE:
                if not url.endswith('.txml'): url += '.txml'
                data = rex.toprettyxml()
                f = open( url, 'wb' ); f.write( bytes(data,'utf-8') ); f.close()
                print('realxtend scene dumped', url)


        elif self.EXPORT_TYPE == 'OGRE':       # ogre-dot-scene
            ############# OgreDotScene ###############
            doc = self.create_ogre_document( context, material_files )
            ##########################################


            for root in roots:
                print('--------------- exporting root ->', root )
                self._node_export( 
                    root, 
                    url=url,
                    doc = doc,
                    exported_meshes = exported_meshes, 
                    meshes = meshes,
                    mesh_collision_prims = mesh_collision_prims,
                    mesh_collision_files = mesh_collision_files,
                    prefix = prefix,
                    objects=objects, 
                    xmlparent=doc._scene_nodes 
                )


            if self.EX_SCENE:
                if not url.endswith('.scene'): url += '.scene'
                data = doc.toprettyxml()
                f = open( url, 'wb' ); f.write( bytes(data,'utf-8') ); f.close()
                print('ogre scene dumped', url)

        for ob in temps: context.scene.objects.unlink( ob )
        bpy.ops.wm.call_menu( name='Ogre_User_Report' )

    def create_ogre_document(self, context, material_files=[] ):
        now = time.time()
        doc = RDocument()
        scn = doc.createElement('scene'); doc.appendChild( scn )
        scn.setAttribute('export_time', str(now))
        scn.setAttribute('formatVersion', '1.0.1')
        bscn = bpy.context.scene
        if '_previous_export_time_' in bscn.keys(): scn.setAttribute('previous_export_time', str(bscn['_previous_export_time_']))
        else: scn.setAttribute('previous_export_time', '0')
        bscn[ '_previous_export_time_' ] = now
        scn.setAttribute('exported_by', getpass.getuser())

        nodes = doc.createElement('nodes')
        doc._scene_nodes = nodes
        extern = doc.createElement('externals')
        environ = doc.createElement('environment')
        for n in (nodes,extern,environ): scn.appendChild( n )
        ############################

        ## extern files ##
        for url in material_files:
            item = doc.createElement('item'); extern.appendChild( item )
            item.setAttribute('type','material')
            a = doc.createElement('file'); item.appendChild( a )
            a.setAttribute('name', url)


        ## environ settings ##
        world = context.scene.world
        if world:   # multiple scenes - other scenes may not have a world
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
            if mist_falloff == 'QUADRATIC': a.setAttribute('mode', 'exp')	# on DTD spec (none | exp | exp2 | linear)
            elif mist_falloff == 'LINEAR': a.setAttribute('mode', 'linear')
            else: a.setAttribute('mode', 'exp2')
            #a.setAttribute('mode', world.mist_settings.falloff.lower() )	# not on DTD spec
            a.setAttribute('linearEnd', '%s' %(world.mist_settings.start+world.mist_settings.depth))
            a.setAttribute('expDensity', world.mist_settings.intensity)
            a.setAttribute('colourR', world.horizon_color.r)
            a.setAttribute('colourG', world.horizon_color.g)
            a.setAttribute('colourB', world.horizon_color.b)

        return doc

    ############# node export - recursive ###############
    def _node_export( self, ob, url='', doc=None, rex=None, exported_meshes=[], meshes=[], mesh_collision_prims={}, mesh_collision_files={}, prefix='', objects=[], xmlparent=None ):

        o = _ogre_node_helper( doc, ob, objects )
        xmlparent.appendChild(o)

        ## custom user props ##
        for prop in ob.items():
            propname, propvalue = prop
            if not propname.startswith('_'):
                user = doc.createElement('user_data')
                o.appendChild( user )
                user.setAttribute( 'name', propname )
                user.setAttribute( 'value', str(propvalue) )
                user.setAttribute( 'type', type(propvalue).__name__ )

        ## BGE subset ##
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

        if ob.type == 'MESH' and len(ob.data.faces):

            collisionFile = None
            collisionPrim = None
            if ob.data.name in mesh_collision_prims: collisionPrim = mesh_collision_prims[ ob.data.name ]
            if ob.data.name in mesh_collision_files: collisionFile = mesh_collision_files[ ob.data.name ]

            #meshes.append( ob )
            e = doc.createElement('entity') 
            o.appendChild(e); e.setAttribute('name', ob.data.name)
            prefix = ''
            #if self.EX_MESH_SUBDIR: prefix = 'meshes/'
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

            if collisionPrim: e.setAttribute('collisionPrim', collisionPrim )
            elif collisionFile: e.setAttribute('collisionFile', collisionFile )

            _mesh_entity_helper( doc, ob, e )

            if self.EX_MESH:
                murl = os.path.join( os.path.split(url)[0], '%s.mesh'%ob.data.name )
                exists = os.path.isfile( murl )
                if not exists or (exists and self.EX_MESH_OVERWRITE):
                    if ob.data.name not in exported_meshes:
                        if '_update_mesh_' in ob.data.keys() and not ob.data['_update_mesh_']: print('    skipping', ob.data)
                        else:
                            exported_meshes.append( ob.data.name )
                            self.dot_mesh( ob, os.path.split(url)[0] )

            ## deal with Array mod ##
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
            # fov in degree
            fov = fovY*180.0/math.pi
            c.setAttribute('fov', '%s'%fov)
            c.setAttribute('projectionType', "perspective")
            a = doc.createElement('clipping'); c.appendChild( a )
            a.setAttribute('nearPlaneDist', '%s' %ob.data.clip_start)
            a.setAttribute('farPlaneDist', '%s' %ob.data.clip_end)


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

            if ob.data.type == 'POINT': l.setAttribute('type', 'point')
            elif ob.data.type == 'SPOT': l.setAttribute('type', 'spot')
            elif ob.data.type == 'SUN': l.setAttribute('type', 'directional')

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
        ## end _node_export




################################################################



class INFO_OT_createOgreExport(bpy.types.Operator, _OgreCommonExport_):
    '''Export Ogre Scene'''
    bl_idname = "ogre.export"
    bl_label = "Export Ogre"
    bl_options = {'REGISTER'}
    filepath= StringProperty(name="File Path", description="Filepath used for exporting Ogre .scene file", maxlen=1024, default="", subtype='FILE_PATH')
    EXPORT_TYPE = 'OGRE'

    EX_SWAP_MODE = EnumProperty( 
        items=AXIS_MODES, 
        name='swap axis',  
        description='axis swapping mode', 
        default='xz-y' 
    )

    EX_SCENE = BoolProperty(name="Export Scene", description="export current scene (OgreDotScene xml)", default=True)
    EX_SELONLY = BoolProperty(name="Export Selected Only", description="export selected", default=True)
    EX_FORCE_CAMERA = BoolProperty(name="Force Camera", description="export active camera", default=True)
    EX_FORCE_LAMPS = BoolProperty(name="Force Lamps", description="export all lamps", default=True)
    EX_MESH = BoolProperty(name="Export Meshes", description="export meshes", default=True)
    EX_MESH_OVERWRITE = BoolProperty(name="Export Meshes (overwrite)", description="export meshes (overwrite existing files)", default=True)
    EX_ANIM = BoolProperty(name="Armature Animation", description="export armature animations - updates the .skeleton file", default=True)
    EX_SHAPE_ANIM = BoolProperty(name="Shape Animation", description="export shape animations - updates the .mesh file", default=True)
    EX_INSTANCES = BoolProperty(name="Optimize Instances", description="optimize instances in OgreDotScene xml", default=True)
    EX_ARRAY = BoolProperty(name="Optimize Arrays", description="optimize array modifiers as instances (constant offset only)", default=True)
    EX_MATERIALS = BoolProperty(name="Export Materials", description="exports .material script", default=True)

    EX_FORCE_IMAGE = EnumProperty( items=_OgreCommonExport_._image_formats, name='Convert Images',  description='convert all textures to format', default='' )
    EX_DDS_MIPS = IntProperty(name="DDS Mips", description="number of mip maps (DDS)", default=3, min=0, max=16)
    EX_TRIM_BONE_WEIGHTS = FloatProperty(name="Trim Weights", description="ignore bone weights below this value\n(Ogre may only support 4 bones per vertex", default=0.01, min=0.0, max=0.1)
    ## Mesh Options ##
    lodLevels = IntProperty(name="LOD Levels", description="MESH number of LOD levels", default=0, min=0, max=32)
    lodDistance = IntProperty(name="LOD Distance", description="MESH distance increment to reduce LOD", default=100, min=0, max=2000)
    lodPercent = IntProperty(name="LOD Percentage", description="LOD percentage reduction", default=40, min=0, max=99)
    nuextremityPoints = IntProperty(name="Extremity Points", description="MESH Extremity Points", default=0, min=0, max=65536)
    generateEdgeLists = BoolProperty(name="Edge Lists", description="MESH generate edge lists (for stencil shadows)", default=False)
    generateTangents = BoolProperty(name="Tangents", description="MESH generate tangents", default=False)
    tangentSemantic = StringProperty(name="Tangent Semantic", description="MESH tangent semantic", maxlen=3, default="uvw")
    tangentUseParity = IntProperty(name="Tangent Parity", description="MESH tangent use parity", default=4, min=0, max=16)
    tangentSplitMirrored = BoolProperty(name="Tangent Split Mirrored", description="MESH split mirrored tangents", default=False)
    tangentSplitRotated = BoolProperty(name="Tangent Split Rotated", description="MESH split rotated tangents", default=False)
    reorganiseBuffers = BoolProperty(name="Reorganise Buffers", description="MESH reorganise vertex buffers", default=True)
    optimiseAnimations = BoolProperty(name="Optimize Animations", description="MESH optimize animations", default=True)


class INFO_OT_createRealxtendExport( bpy.types.Operator, _OgreCommonExport_ ):
    '''Export RealXtend Scene'''
    bl_idname = "ogre.export_realxtend"
    bl_label = "Export RealXtend"
    bl_options = {'REGISTER', 'UNDO'}
    filepath= StringProperty(name="File Path", description="Filepath used for exporting .txml file", maxlen=1024, default="", subtype='FILE_PATH')
    EXPORT_TYPE = 'REX'

    EX_SWAP_MODE = EnumProperty( 
        items=AXIS_MODES, 
        name='swap axis',  
        description='axis swapping mode', 
        default='xz-y' 
    )

    EX_SCENE = BoolProperty(name="Export Scene", description="export current scene (OgreDotScene xml)", default=True)
    EX_SELONLY = BoolProperty(name="Export Selected Only", description="export selected", default=True)
    EX_FORCE_CAMERA = BoolProperty(name="Force Camera", description="export active camera", default=True)
    EX_FORCE_LAMPS = BoolProperty(name="Force Lamps", description="export all lamps", default=True)
    EX_MESH = BoolProperty(name="Export Meshes", description="export meshes", default=True)
    EX_MESH_OVERWRITE = BoolProperty(name="Export Meshes (overwrite)", description="export meshes (overwrite existing files)", default=True)
    EX_ANIM = BoolProperty(name="Armature Animation", description="export armature animations - updates the .skeleton file", default=True)
    EX_SHAPE_ANIM = BoolProperty(name="Shape Animation", description="export shape animations - updates the .mesh file", default=True)
    EX_INSTANCES = BoolProperty(name="Optimize Instances", description="optimize instances in OgreDotScene xml", default=True)
    EX_ARRAY = BoolProperty(name="Optimize Arrays", description="optimize array modifiers as instances (constant offset only)", default=True)
    EX_MATERIALS = BoolProperty(name="Export Materials", description="exports .material script", default=True)

    EX_FORCE_IMAGE = EnumProperty( items=_OgreCommonExport_._image_formats, name='Convert Images',  description='convert all textures to format', default='' )
    EX_DDS_MIPS = IntProperty(name="DDS Mips", description="number of mip maps (DDS)", default=3, min=0, max=16)
    EX_TRIM_BONE_WEIGHTS = FloatProperty(name="Trim Weights", description="ignore bone weights below this value\n(Ogre may only support 4 bones per vertex", default=0.01, min=0.0, max=0.1)
    ## Mesh Options ##
    lodLevels = IntProperty(name="LOD Levels", description="MESH number of LOD levels", default=0, min=0, max=32)
    lodDistance = IntProperty(name="LOD Distance", description="MESH distance increment to reduce LOD", default=100, min=0, max=2000)
    lodPercent = IntProperty(name="LOD Percentage", description="LOD percentage reduction", default=40, min=0, max=99)
    nuextremityPoints = IntProperty(name="Extremity Points", description="MESH Extremity Points", default=0, min=0, max=65536)
    generateEdgeLists = BoolProperty(name="Edge Lists", description="MESH generate edge lists (for stencil shadows)", default=False)
    generateTangents = BoolProperty(name="Tangents", description="MESH generate tangents", default=False)
    tangentSemantic = StringProperty(name="Tangent Semantic", description="MESH tangent semantic", maxlen=3, default="uvw")
    tangentUseParity = IntProperty(name="Tangent Parity", description="MESH tangent use parity", default=4, min=0, max=16)
    tangentSplitMirrored = BoolProperty(name="Tangent Split Mirrored", description="MESH split mirrored tangents", default=False)
    tangentSplitRotated = BoolProperty(name="Tangent Split Rotated", description="MESH split rotated tangents", default=False)
    reorganiseBuffers = BoolProperty(name="Reorganise Buffers", description="MESH reorganise vertex buffers", default=True)
    optimiseAnimations = BoolProperty(name="Optimize Animations", description="MESH optimize animations", default=True)


def get_parent_matrix( ob, objects ):
    if not ob.parent:
        return mathutils.Matrix(((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)))   # Requiered for Blender SVN > 2.56
    else:
        if ob.parent in objects:
            return ob.parent.matrix_world.copy()
        else:
            return get_parent_matrix(ob.parent, objects)

def _ogre_node_helper( doc, ob, objects, prefix='', pos=None, rot=None, scl=None ):
    mat = get_parent_matrix(ob, objects).inverted() * ob.matrix_world   # shouldn't this be matrix_local?

    o = doc.createElement('node')
    o.setAttribute('name',prefix+ob.name)
    p = doc.createElement('position')
    q = doc.createElement('rotation')       #('quaternion')
    s = doc.createElement('scale')
    for n in (p,q,s): o.appendChild(n)

    if pos: v = swap(pos)
    else: v = swap( mat.to_translation() )
    p.setAttribute('x', '%6f'%v.x)
    p.setAttribute('y', '%6f'%v.y)
    p.setAttribute('z', '%6f'%v.z)

    if rot: v = swap(rot)
    else: v = swap( mat.to_quaternion() )
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

def merge_group( group ):
    print('--------------- merge group ->', group )
    copies = []
    for ob in group.objects:
        if ob.type == 'MESH':
            print( '\t group member', ob.name )
            o2 = ob.copy(); copies.append( o2 )
            o2.data = o2.to_mesh(bpy.context.scene, True, "PREVIEW")    # collaspe modifiers
            while o2.modifiers: o2.modifiers.remove( o2.modifiers[0] )
            bpy.context.scene.objects.link( o2 )#; o2.select = True
    merged = merge( copies )
    merged.name = group.name
    merged.data.name = group.name
    return merged

def merge_objects( objects, name='_temp_', transform=None ):
    assert objects
    copies = []
    for ob in objects:
        ob.select = False
        if ob.type == 'MESH':
            o2 = ob.copy(); copies.append( o2 )
            o2.data = o2.to_mesh(bpy.context.scene, True, "PREVIEW")    # collaspe modifiers
            while o2.modifiers: o2.modifiers.remove( o2.modifiers[0] )
            if transform: o2.matrix_world =  transform * o2.matrix_local
            bpy.context.scene.objects.link( o2 )#; o2.select = True
    merged = merge( copies )
    merged.name = name
    merged.data.name = name
    return merged


def merge( objects ):
    print('MERGE', objects)
    for ob in bpy.context.selected_objects: ob.select = False
    for ob in objects:
        print('\t'+ob.name)
        ob.select = True
        assert not ob.library
    bpy.context.scene.objects.active = ob
    bpy.ops.object.join()
    return bpy.context.active_object

def get_merge_group( ob, prefix='merge' ):
    m = []
    for grp in ob.users_group:
        if grp.name.lower().startswith(prefix): m.append( grp )
    if len(m)==1:
        #if ob.data.users != 1:
        #    print( 'WARNING: an instance can not be in a merge group' )
        #    return
        return m[0]
    elif m:
        print('WARNING: an object can not be in two merge groups at the same time', ob)
        return


############ Ogre Command Line Tools ###########
class MeshMagick(object):
    ''' Usage: MeshMagick [global_options] toolname [tool_options] infile(s) -- [outfile(s)]
    Available Tools
    ===============
    info - print information about the mesh.
    meshmerge - Merge multiple submeshes into a single mesh.
    optimise - Optimise meshes and skeletons.
    rename - Rename different elements of meshes and skeletons.
    transform - Scale, rotate or otherwise transform a mesh.
    '''

    @staticmethod
    def get_merge_group( ob ): return get_merge_group( ob, prefix='magicmerge' )

    @staticmethod
    def merge( group, path='/tmp', force_name=None ):
        print('-'*80)
        print(' mesh magick - merge ')
        exe = CONFIG_OGRETOOLS_MESH_MAGICK
        if not os.path.isfile( exe ):
            print( 'ERROR: can not find MeshMagick.exe' )
            print( exe )
            return

        files = []
        for ob in group.objects:
            if ob.data.users == 1:    # single users only
                files.append( os.path.join( path, ob.data.name+'.mesh' ) )
                print( files[-1] )

        opts = 'meshmerge'
        if sys.platform == 'linux2': cmd = '/usr/bin/wine %s %s' %(exe, opts)
        else: cmd = '%s %s' %(exe, opts)
        if force_name: output = force_name + '.mesh'
        else: output = '_%s_.mesh' %group.name
        cmd = cmd.split() + files + ['--', os.path.join(path,output) ]
        subprocess.call( cmd )
        print(' mesh magick - complete ')
        print('-'*80)

_ogre_command_line_tools_doc = '''
Bug reported by CLB: converter expects .mesh.xml or .skeleton.xml to determine the type - fixed nov24

Usage: OgreXMLConverter [options] sourcefile [destfile]

Available options:
    -i             = interactive mode - prompt for options
    (The next 4 options are only applicable when converting XML to Mesh)
    -l lodlevels   = number of LOD levels
    -d loddist     = distance increment to reduce LOD
    -p lodpercent  = Percentage triangle reduction amount per LOD

    -f lodnumtris  = Fixed vertex reduction per LOD

    -e             = DON'T generate edge lists (for stencil shadows)

    -r             = DON'T reorganise vertex buffers to OGRE recommended format.
    -t             = Generate tangents (for normal mapping)

    -o             = DON'T optimise out redundant tracks & keyframes
    -d3d           = Prefer D3D packed colour formats (default on Windows)


    -gl            = Prefer GL packed colour formats (default on non-Windows)
    -E endian      = Set endian mode 'big' 'little' or 'native' (default)
    -q             = Quiet mode, less output

    -log filename  = name of the log file (default: 'OgreXMLConverter.log')
    sourcefile     = name of file to convert

    destfile       = optional name of file to write to. If you don't
                       specify this OGRE works it out through the extension
                       and the XML contents if the source is XML. For example

                       test.mesh becomes test.xml, test.xml becomes test.mesh
                       if the XML document root is <mesh> etc.

'''

def OgreXMLConverter( infile, opts ):
    print('[Ogre Tools Wrapper]', infile )

    exe = CONFIG_OGRETOOLS_XML_CONVERTER
    if not os.path.isfile( exe ):
        print( 'ERROR: can not find OgreXMLConverter' )
        print( exe )
        return

    basicArguments = ''

    if opts['lodLevels']:
        basicArguments += ' -l %s -d %s -p %s' %(opts['lodLevels'], opts['lodDistance'], opts['lodPercent'])
        
    if opts['nuextremityPoints'] > 0:
        basicArguments += ' -x %s' %opts['nuextremityPoints']

    if not opts['generateEdgeLists']:
        basicArguments += ' -e'

    if opts['generateTangents']:
        basicArguments += ' -t'
        if opts['tangentSemantic']:
            basicArguments += ' -td %s' %opts['tangentSemantic']
        if opts['tangentUseParity']:
            basicArguments += ' -ts %s' %opts['tangentUseParity']
        if opts['tangentSplitMirrored']:
            basicArguments += ' -tm'
        if opts['tangentSplitRotated']:
            basicArguments += ' -tr'
    if not opts['reorganiseBuffers']:
        basicArguments += ' -r'
    if not opts['optimiseAnimations']:
        basicArguments += ' -o'

    opts = '-log _ogre_debug.txt %s' %basicArguments
    path,name = os.path.split( infile )

    cmd = '%s %s' %(exe, opts)
    print('-'*80)
    print(cmd)
    print('_'*80)
    cmd = cmd.split() + [infile]
    subprocess.call( cmd )




def find_bone_index( ob, arm, groupidx):    # sometimes the groups are out of order, this finds the right index.
    vg = ob.vertex_groups[ groupidx ]
    for i,bone in enumerate(arm.pose.bones):
        if bone.name == vg.name: return i

def mesh_is_smooth( mesh ):
    for face in mesh.faces:
        if face.use_smooth: return True




class Bone(object):
    ''' EditBone
    ['__doc__', '__module__', '__slots__', 'align_orientation', 'align_roll', 'bbone_in', 'bbone_out', 'bbone_segments', 'bl_rna', 'envelope_distance', 'envelope_weight', 'head', 'head_radius', 'hide', 'hide_select', 'layers', 'lock', 'matrix', 'name', 'parent', 'rna_type', 'roll', 'select', 'select_head', 'select_tail', 'show_wire', 'tail', 'tail_radius', 'transform', 'use_connect', 'use_cyclic_offset', 'use_deform', 'use_envelope_multiply', 'use_inherit_rotation', 'use_inherit_scale', 'use_local_location']
    '''

    def __init__(self, matrix, pbone, skeleton):
        if OPTIONS['SWAP_AXIS'] == 'xyz':
            self.fixUpAxis = False

        else:
            self.fixUpAxis = True
            if OPTIONS['SWAP_AXIS'] == '-xzy':      # Tundra1
                self.flipMat = mathutils.Matrix(((-1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)))
            elif OPTIONS['SWAP_AXIS'] == 'xz-y':    # Tundra2
                self.flipMat = mathutils.Matrix(((1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)))
            else:
                print( 'ERROR - TODO: axis swap mode not supported with armature animation' )
                assert 0

        self.skeleton = skeleton
        self.name = pbone.name
        #self.matrix = self.flipMat * matrix
        self.matrix = matrix
        self.bone = pbone        # safe to hold pointer to pose bone, not edit bone!
        if not pbone.bone.use_deform: print('warning: bone <%s> is non-deformabled, this is inefficient!' %self.name)
        #TODO test#if pbone.bone.use_inherit_scale: print('warning: bone <%s> is using inherit scaling, Ogre has no support for this' %self.name)
        self.parent = pbone.parent
        self.children = []

    def update(self):        # called on frame update
        pose =  self.bone.matrix.copy()
        #pose = self.bone.matrix * self.skeleton.object_space_transformation
        #pose =  self.skeleton.object_space_transformation * self.bone.matrix
        self._inverse_total_trans_pose = pose.inverted()

        # calculate difference to parent bone
        if self.parent:
            pose = self.parent._inverse_total_trans_pose* pose
        elif self.fixUpAxis:
            #pose = mathutils.Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1))) * pose   # Requiered for Blender SVN > 2.56
            pose = self.flipMat * pose
        else:
            pass

        # get transformation values
        # translation relative to parent coordinate system orientation
        # and as difference to rest pose translation
        #blender2.49#translation -= self.ogreRestPose.translationPart()
        self.pose_location =  pose.to_translation()  -  self.ogre_rest_matrix.to_translation()

        # rotation (and scale) relative to local coordiante system
        # calculate difference to rest pose
        #blender2.49#poseTransformation *= self.inverseOgreRestPose
        #pose = pose * self.inverse_ogre_rest_matrix        # this was wrong, fixed Dec3rd
        pose = self.inverse_ogre_rest_matrix * pose
        self.pose_rotation = pose.to_quaternion()
        self.pose_scale = pose.to_scale()

        #self.pose_location = self.bone.location.copy()
        #self.pose_rotation = self.bone.rotation_quaternion.copy()
        for child in self.children: child.update()


    def rebuild_tree( self ):        # called first on all bones
        if self.parent:
            self.parent = self.skeleton.get_bone( self.parent.name )
            self.parent.children.append( self )

    def compute_rest( self ):    # called after rebuild_tree, recursive roots to leaves
        if self.parent:
            inverseParentMatrix = self.parent.inverse_total_trans
        elif self.fixUpAxis:
            inverseParentMatrix = self.flipMat
        else:
            inverseParentMatrix = mathutils.Matrix(((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)))

        # bone matrix relative to armature object
        self.ogre_rest_matrix = self.matrix.copy()
        # relative to mesh object origin
        #self.ogre_rest_matrix *= self.skeleton.object_space_transformation        # 2.49 style

        ##not correct - june18##self.ogre_rest_matrix = self.skeleton.object_space_transformation * self.ogre_rest_matrix
        #self.ogre_rest_matrix -= self.skeleton.object_space_transformation


        # store total inverse transformation
        self.inverse_total_trans = self.ogre_rest_matrix.inverted()

        # relative to OGRE parent bone origin
        #self.ogre_rest_matrix *= inverseParentMatrix        # 2.49 style
        self.ogre_rest_matrix = inverseParentMatrix * self.ogre_rest_matrix
        self.inverse_ogre_rest_matrix = self.ogre_rest_matrix.inverted()

        ## recursion ##
        for child in self.children:
            child.compute_rest()

class Skeleton(object):
    def get_bone( self, name ):
        for b in self.bones:
            if b.name == name: return b

    def __init__(self, ob ):
        self.object = ob
        self.bones = []
        mats = {}
        self.arm = arm = ob.find_armature()
        arm.hide = False
        self._restore_layers = list(arm.layers)
        #arm.layers = [True]*20      # can not have anything hidden - REQUIRED?
        prev = bpy.context.scene.objects.active
        bpy.context.scene.objects.active = arm        # arm needs to be in edit mode to get to .edit_bones
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        for bone in arm.data.edit_bones: mats[ bone.name ] = bone.matrix.copy()
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        #bpy.ops.object.mode_set(mode='POSE', toggle=False)
        bpy.context.scene.objects.active = prev

        for pbone in arm.pose.bones:
            mybone = Bone( mats[pbone.name] ,pbone, self )
            self.bones.append( mybone )

        if arm.name not in Report.armatures: Report.armatures.append( arm.name )

        # additional transformation for root bones:
        # from armature object space into mesh object space, i.e.,
        # (x,y,z,w)*AO*MO^(-1)
        self.object_space_transformation = arm.matrix_local * ob.matrix_local.inverted()

        ## setup bones for Ogre format ##
        for b in self.bones: b.rebuild_tree()
        ## walk bones, convert them ##
        self.roots = []
        for b in self.bones:
            if not b.parent:
                b.compute_rest()
                self.roots.append( b )

    def to_xml( self ):
        _fps = float( bpy.context.scene.render.fps )

        doc = RDocument()
        root = doc.createElement('skeleton'); doc.appendChild( root )
        bones = doc.createElement('bones'); root.appendChild( bones )
        bh = doc.createElement('bonehierarchy'); root.appendChild( bh )
        for i,bone in enumerate(self.bones):
            b = doc.createElement('bone')
            b.setAttribute('name', bone.name)
            b.setAttribute('id', str(i) )
            bones.appendChild( b )
            mat = bone.ogre_rest_matrix.copy()
            if bone.parent:
                bp = doc.createElement('boneparent')
                bp.setAttribute('bone', bone.name)
                bp.setAttribute('parent', bone.parent.name)
                bh.appendChild( bp )

            pos = doc.createElement( 'position' ); b.appendChild( pos )
            x,y,z = mat.to_translation()
            pos.setAttribute('x', '%6f' %x )
            pos.setAttribute('y', '%6f' %y )
            pos.setAttribute('z', '%6f' %z )
            rot =  doc.createElement( 'rotation' )        # note "rotation", not "rotate"
            b.appendChild( rot )

            q = mat.to_quaternion()
            rot.setAttribute('angle', '%6f' %q.angle )
            axis = doc.createElement('axis'); rot.appendChild( axis )
            x,y,z = q.axis
            axis.setAttribute('x', '%6f' %x )
            axis.setAttribute('y', '%6f' %y )
            axis.setAttribute('z', '%6f' %z )

            ## Ogre bones do not have initial scaling? ##
            ## NOTE: Ogre bones by default do not pass down their scaling in animation,
            ## so in blender all bones are like 'do-not-inherit-scaling'
            if 0:
                scale = doc.createElement('scale'); b.appendChild( scale )
                x,y,z = swap( mat.to_scale() )
                scale.setAttribute('x', str(x))
                scale.setAttribute('y', str(y))
                scale.setAttribute('z', str(z))

        arm = self.arm
        if not arm.animation_data or (arm.animation_data and not arm.animation_data.nla_tracks):  # assume animated via constraints and use blender timeline.
            anims = doc.createElement('animations'); root.appendChild( anims )
            anim = doc.createElement('animation'); anims.appendChild( anim )
            tracks = doc.createElement('tracks'); anim.appendChild( tracks )
            anim.setAttribute('name', 'my_animation')
            start = bpy.context.scene.frame_start; end = bpy.context.scene.frame_end
            anim.setAttribute('length', str( (end-start)/_fps ) )

            _keyframes = {}
            _bonenames_ = []
            for bone in arm.pose.bones:
                _bonenames_.append( bone.name )
                track = doc.createElement('track')
                track.setAttribute('bone', bone.name)
                tracks.appendChild( track )
                keyframes = doc.createElement('keyframes')
                track.appendChild( keyframes )
                _keyframes[ bone.name ] = keyframes

            for frame in range( int(start), int(end), bpy.context.scene.frame_step):
                bpy.context.scene.frame_set(frame)
                for bone in self.roots: bone.update()
                print('\t\t Frame:', frame)
                for bonename in _bonenames_:
                    bone = self.get_bone( bonename )
                    _loc = bone.pose_location
                    _rot = bone.pose_rotation
                    _scl = bone.pose_scale

                    keyframe = doc.createElement('keyframe')
                    keyframe.setAttribute('time', str((frame-start)/_fps))
                    _keyframes[ bonename ].appendChild( keyframe )
                    trans = doc.createElement('translate')
                    keyframe.appendChild( trans )
                    x,y,z = _loc
                    trans.setAttribute('x', '%6f' %x)
                    trans.setAttribute('y', '%6f' %y)
                    trans.setAttribute('z', '%6f' %z)

                    rot =  doc.createElement( 'rotate' )
                    keyframe.appendChild( rot )
                    q = _rot
                    rot.setAttribute('angle', '%6f' %q.angle )
                    axis = doc.createElement('axis'); rot.appendChild( axis )
                    x,y,z = q.axis
                    axis.setAttribute('x', '%6f' %x )
                    axis.setAttribute('y', '%6f' %y )
                    axis.setAttribute('z', '%6f' %z )

                    scale = doc.createElement('scale')
                    keyframe.appendChild( scale )
                    x,y,z = _scl
                    scale.setAttribute('x', '%6f' %x)
                    scale.setAttribute('y', '%6f' %y)
                    scale.setAttribute('z', '%6f' %z)


        elif arm.animation_data:
            anims = doc.createElement('animations'); root.appendChild( anims )
            if not len( arm.animation_data.nla_tracks ):
                Report.warnings.append('you must assign an NLA strip to armature (%s) that defines the start and end frames' %arm.name)

            for nla in arm.animation_data.nla_tracks:        # NLA required, lone actions not supported
                if not len(nla.strips): print( 'skipping empty NLA track: %s' %nla.name ); continue
                for strip in nla.strips:
                    anim = doc.createElement('animation'); anims.appendChild( anim )
                    tracks = doc.createElement('tracks'); anim.appendChild( tracks )
                    Report.armature_animations.append( '%s : %s [start frame=%s  end frame=%s]' %(arm.name, nla.name, strip.frame_start, strip.frame_end) )

                    #anim.setAttribute('animation_group', nla.name)        # this is extended xml format not useful?
                    anim.setAttribute('name', strip.name)                       # USE the action's name
                    anim.setAttribute('length', str( (strip.frame_end-strip.frame_start)/_fps ) )
                    ## using the fcurves directly is useless, because:
                    ## we need to support constraints and the interpolation between keys
                    ## is Ogre smart enough that if a track only has a set of bones, then blend animation with current animation?
                    ## the exporter will not be smart enough to know which bones are active for a given track...
                    ## can hijack blender NLA, user sets a single keyframe for only selected bones, and keys last frame
                    stripbones = []
                    if OPTIONS['ONLY_ANIMATED_BONES']:
                        for group in strip.action.groups:        # check if the user has keyed only some of the bones (for anim blending)
                            if group.name in arm.pose.bones: stripbones.append( group.name )

                        if not stripbones:                                    # otherwise we use all bones
                            stripbones = [ bone.name for bone in arm.pose.bones ]
                    else:
                        stripbones = [ bone.name for bone in arm.pose.bones ]

                    print('NLA-strip:',  nla.name)
                    _keyframes = {}
                    for bonename in stripbones:
                        track = doc.createElement('track')
                        track.setAttribute('bone', bonename)
                        tracks.appendChild( track )
                        keyframes = doc.createElement('keyframes')
                        track.appendChild( keyframes )
                        _keyframes[ bonename ] = keyframes
                        print('\t Bone:', bonename)

                    for frame in range( int(strip.frame_start), int(strip.frame_end), bpy.context.scene.frame_step):
                        bpy.context.scene.frame_set(frame)
                        for bone in self.roots: bone.update()
                        print('\t\t Frame:', frame)
                        for bonename in stripbones:
                            bone = self.get_bone( bonename )
                            _loc = bone.pose_location
                            _rot = bone.pose_rotation
                            _scl = bone.pose_scale

                            keyframe = doc.createElement('keyframe')
                            keyframe.setAttribute('time', str((frame-strip.frame_start)/_fps))
                            _keyframes[ bonename ].appendChild( keyframe )
                            trans = doc.createElement('translate')
                            keyframe.appendChild( trans )
                            x,y,z = _loc
                            trans.setAttribute('x', '%6f' %x)
                            trans.setAttribute('y', '%6f' %y)
                            trans.setAttribute('z', '%6f' %z)

                            rot =  doc.createElement( 'rotate' )
                            keyframe.appendChild( rot )
                            q = _rot
                            rot.setAttribute('angle', '%6f' %q.angle )
                            axis = doc.createElement('axis'); rot.appendChild( axis )
                            x,y,z = q.axis
                            axis.setAttribute('x', '%6f' %x )
                            axis.setAttribute('y', '%6f' %y )
                            axis.setAttribute('z', '%6f' %z )

                            scale = doc.createElement('scale')
                            keyframe.appendChild( scale )
                            x,y,z = _scl
                            scale.setAttribute('x', '%6f' %x)
                            scale.setAttribute('y', '%6f' %y)
                            scale.setAttribute('z', '%6f' %z)

        return doc.toprettyxml()





class INFO_MT_instances(bpy.types.Menu):
    bl_label = "Instances"

    def draw(self, context):
        layout = self.layout
        inst = gather_instances()
        for data in inst:
            ob = inst[data][0]
            op = layout.operator(INFO_MT_instance.bl_idname, text=ob.name)    # operator has no variable for button name?
            op.mystring = ob.name
        layout.separator()

class INFO_MT_instance(bpy.types.Operator):
    '''select instance group'''
    bl_idname = "ogre.select_instances"
    bl_label = "Select Instance Group"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type
    mystring= StringProperty(name="MyString", description="...", maxlen=1024, default="my string")
    @classmethod
    def poll(cls, context):
        return True
    def invoke(self, context, event):
        print( 'invoke select_instances op', event )
        select_instances( context, self.mystring )
        return {'FINISHED'}


class INFO_MT_groups(bpy.types.Menu):
    bl_label = "Groups"
    def draw(self, context):
        layout = self.layout
        for group in bpy.data.groups:
            #op = layout.operator(INFO_MT_group_mark.bl_idname)
            #op.groupname = group.name
            op = layout.operator(INFO_MT_group.bl_idname, text=group.name)    # operator no variable for button name?
            op.mystring = group.name
        layout.separator()

#TODO - is this being used?
class INFO_MT_group_mark(bpy.types.Operator):
    '''mark group auto combine on export'''
    bl_idname = "ogre.mark_group_export_combine"
    bl_label = "Group Auto Combine"
    bl_options = {'REGISTER'}                              # Options for this panel type
    mybool= BoolProperty(name="groupautocombine", description="set group auto-combine", default=False)
    mygroups = {}
    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        self.mygroups[ op.groupname ] = self.mybool
        return {'FINISHED'}

class INFO_MT_group(bpy.types.Operator):
    '''select group'''
    bl_idname = "ogre.select_group"
    bl_label = "Select Group"
    bl_options = {'REGISTER'}                              # Options for this panel type
    mystring= StringProperty(name="MyString", description="...", maxlen=1024, default="my string")
    @classmethod
    def poll(cls, context):
        return True
    def invoke(self, context, event):
        select_group( context, self.mystring )
        return {'FINISHED'}

#############
class INFO_MT_actors(bpy.types.Menu):
    bl_label = "Actors"
    def draw(self, context):
        layout = self.layout
        for ob in bpy.context.scene.objects:
            if ob.game.use_actor:
                op = layout.operator(INFO_MT_actor.bl_idname, text=ob.name)
                op.mystring = ob.name
        layout.separator()

class INFO_MT_actor(bpy.types.Operator):
    '''select actor'''
    bl_idname = "ogre.select_actor"
    bl_label = "Select Actor"
    bl_options = {'REGISTER'}                              # Options for this panel type
    mystring= StringProperty(name="MyString", description="...", maxlen=1024, default="my string")
    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        bpy.data.objects[self.mystring].select = True
        return {'FINISHED'}

class INFO_MT_dynamics(bpy.types.Menu):
    bl_label = "Dynamics"
    def draw(self, context):
        layout = self.layout
        for ob in bpy.data.objects:
            if ob.game.physics_type in 'DYNAMIC SOFT_BODY RIGID_BODY'.split():
                op = layout.operator(INFO_MT_dynamic.bl_idname, text=ob.name)
                op.mystring = ob.name
        layout.separator()

class INFO_MT_dynamic(bpy.types.Operator):
    '''select dynamic'''
    bl_idname = "ogre.select_dynamic"
    bl_label = "Select Dynamic"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type
    mystring= StringProperty(name="MyString", description="...", maxlen=1024, default="my string")
    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        bpy.context.scene.objects[self.mystring].select = True
        return {'FINISHED'}





NVDXT_DOC = '''
Version 8.30
NVDXT
This program
   compresses images
   creates normal maps from color or alpha
   creates DuDv map
   creates cube maps
   writes out .dds file
   does batch processing
   reads .tga, .bmp, .gif, .ppm, .jpg, .tif, .cel, .dds, .png, .psd, .rgb, *.bw and .rgba
   filters MIP maps

Options:
  -profile <profile name> : Read a profile created from the Photoshop plugin
  -quick : use fast compression method
  -quality_normal : normal quality compression
  -quality_production : production quality compression
  -quality_highest : highest quality compression (this can be very slow)
  -rms_threshold <int> : quality RMS error. Above this, an extensive search is performed.
  -prescale <int> <int>: rescale image to this size first
  -rescale <nearest | hi | lo | next_lo>: rescale image to nearest, next highest or next lowest power of two
  -rel_scale <float, float> : relative scale of original image. 0.5 is half size Default 1.0, 1.0

Optional Filtering for rescaling. Default cube filter:
  -RescalePoint
  -RescaleBox
  -RescaleTriangle
  -RescaleQuadratic
  -RescaleCubic
  -RescaleCatrom
  -RescaleMitchell
  -RescaleGaussian
  -RescaleSinc
  -RescaleBessel
  -RescaleHanning
  -RescaleHamming
  -RescaleBlackman
  -RescaleKaiser
  -clamp <int, int> : maximum image size. image width and height are clamped
  -clampScale <int, int> : maximum image size. image width and height are scaled 
  -window <left, top, right, bottom> : window of original window to compress
  -nomipmap : don't generate MIP maps
  -nmips <int> : specify the number of MIP maps to generate
  -rgbe : Image is RGBE format
  -dither : add dithering
  -sharpenMethod <method>: sharpen method MIP maps
  <method> is 
        None
        Negative
        Lighter
        Darker
        ContrastMore
        ContrastLess
        Smoothen
        SharpenSoft
        SharpenMedium
        SharpenStrong
        FindEdges
        Contour
        EdgeDetect
        EdgeDetectSoft
        Emboss
        MeanRemoval
        UnSharp <radius, amount, threshold>
        XSharpen <xsharpen_strength, xsharpen_threshold>
        Custom
  -pause : wait for keyboard on error
  -flip : flip top to bottom 
  -timestamp : Update only changed files
  -list <filename> : list of files to convert
  -cubeMap : create cube map . 
            Cube faces specified with individual files with -list option
                  positive x, negative x, positive y, negative y, positive z, negative z
                  Use -output option to specify filename
            Cube faces specified in one file.  Use -file to specify input filename

  -volumeMap : create volume texture. 
            Volume slices specified with individual files with -list option
                  Use -output option to specify filename
            Volume specified in one file.  Use -file to specify input filename

  -all : all image files in current directory
  -outdir <directory>: output directory
  -deep [directory]: include all subdirectories
  -outsamedir : output directory same as input
  -overwrite : if input is .dds file, overwrite old file
  -forcewrite : write over readonly files
  -file <filename> : input file to process. Accepts wild cards
  -output <filename> : filename to write to [-outfile can also be specified]
  -append <filename_append> : append this string to output filename
  -8  <dxt1c | dxt1a | dxt3 | dxt5 | u1555 | u4444 | u565 | u8888 | u888 | u555 | L8 | A8>  : compress 8 bit images with this format
  -16 <dxt1c | dxt1a | dxt3 | dxt5 | u1555 | u4444 | u565 | u8888 | u888 | u555 | A8L8> : compress 16 bit images with this format
  -24 <dxt1c | dxt1a | dxt3 | dxt5 | u1555 | u4444 | u565 | u8888 | u888 | u555> : compress 24 bit images with this format
  -32 <dxt1c | dxt1a | dxt3 | dxt5 | u1555 | u4444 | u565 | u8888 | u888 | u555> : compress 32 bit images with this format

  -swapRB : swap rb
  -swapRG : swap rg
  -gamma <float value>: gamma correcting during filtering
  -outputScale <float, float, float, float>: scale the output by this (r,g,b,a)
  -outputBias <float, float, float, float>: bias the output by this amount (r,g,b,a)
  -outputWrap : wraps overflow values modulo the output format 
  -inputScale <float, float, float, float>: scale the inpput by this (r,g,b,a)
  -inputBias <float, float, float, float>: bias the input by this amount (r,g,b,a)
  -binaryalpha : treat alpha as 0 or 1
  -alpha_threshold <byte>: [0-255] alpha reference value 
  -alphaborder : border images with alpha = 0
  -alphaborderLeft : border images with alpha (left) = 0
  -alphaborderRight : border images with alpha (right)= 0
  -alphaborderTop : border images with alpha (top) = 0
  -alphaborderBottom : border images with alpha (bottom)= 0
  -fadeamount <int>: percentage to fade each MIP level. Default 15

  -fadecolor : fade map (color, normal or DuDv) over MIP levels
  -fadetocolor <hex color> : color to fade to
  -custom_fade <n> <n fadeamounts> : set custom fade amount.  n is number number of fade amounts. fadeamount are [0,1]
  -fadealpha : fade alpha over MIP levels
  -fadetoalpha <byte>: [0-255] alpha to fade to
  -border : border images with color
  -bordercolor <hex color> : color for border
  -force4 : force DXT1c to use always four colors
  -weight <float, float, float>: Compression weightings for R G and B
  -luminance :  convert color values to luminance for L8 formats
  -greyScale : Convert to grey scale
  -greyScaleWeights <float, float, float, float>: override greyscale conversion weights of (0.3086, 0.6094, 0.0820, 0)  
  -brightness <float, float, float, float>: per channel brightness. Default 0.0  usual range [0,1]
  -contrast <float, float, float, float>: per channel contrast. Default 1.0  usual range [0.5, 1.5]

Texture Format  Default DXT3:
  -dxt1c   : DXT1 (color only)
  -dxt1a   : DXT1 (one bit alpha)
  -dxt3    : DXT3
  -dxt5    : DXT5n
  -u1555   : uncompressed 1:5:5:5
  -u4444   : uncompressed 4:4:4:4
  -u565    : uncompressed 5:6:5
  -u8888   : uncompressed 8:8:8:8
  -u888    : uncompressed 0:8:8:8
  -u555    : uncompressed 0:5:5:5
  -p8c     : paletted 8 bit (256 colors)
  -p8a     : paletted 8 bit (256 colors with alpha)
  -p4c     : paletted 4 bit (16 colors)
  -p4a     : paletted 4 bit (16 colors with alpha)
  -a8      : 8 bit alpha channel
  -cxv8u8  : normal map format
  -v8u8    : EMBM format (8, bit two component signed)
  -v16u16  : EMBM format (16 bit, two component signed)
  -A8L8    : 8 bit alpha channel, 8 bit luminance
  -fp32x4  : fp32 four channels (A32B32G32R32F)
  -fp32    : fp32 one channel (R32F)
  -fp16x4  : fp16 four channels (A16B16G16R16F)
  -dxt5nm  : dxt5 style normal map
  -3Dc     : 3DC
  -g16r16  : 16 bit in, two component
  -g16r16f : 16 bit float, two components

Mip Map Filtering Options. Default box filter:
  -Point
  -Box
  -Triangle
  -Quadratic
  -Cubic
  -Catrom
  -Mitchell
  -Gaussian
  -Sinc
  -Bessel
  -Hanning
  -Hamming
  -Blackman
  -Kaiser

***************************
To make a normal or dudv map, specify one of
  -n4 : normal map 4 sample
  -n3x3 : normal map 3x3 filter
  -n5x5 : normal map 5x5 filter
  -n7x7 : normal map 7x7 filter
  -n9x9 : normal map 9x9 filter
  -dudv : DuDv

and source of height info:
  -alpha : alpha channel
  -rgb : average rgb
  -biased : average rgb biased
  -red : red channel
  -green : green channel
  -blue : blue channel
  -max : max of (r,g,b)
  -colorspace : mix of r,g,b

-norm : normalize mip maps (source is a normal map)

-toHeight : create a height map (source is a normal map)


Normal/DuDv Map dxt:
  -aheight : store calculated height in alpha field
  -aclear : clear alpha channel
  -awhite : set alpha channel = 1.0
  -scale <float> : scale of height map. Default 1.0
  -wrap : wrap texture around. Default off
  -minz <int> : minimum value for up vector [0-255]. Default 0

***************************
To make a depth sprite, specify:
  -depth

and source of depth info:
  -alpha  : alpha channel
  -rgb    : average rgb (default)
  -red    : red channel
  -green  : green channel
  -blue   : blue channel
  -max    : max of (r,g,b)
  -colorspace : mix of r,g,b

Depth Sprite dxt:
  -aheight : store calculated depth in alpha channel
  -aclear : store 0.0 in alpha channel
  -awhite : store 1.0 in alpha channel
  -scale <float> : scale of depth sprite (default 1.0)
  -alpha_modulate : multiplies color by alpha during filtering
  -pre_modulate : multiplies color by alpha before processing

Examples
  nvdxt -cubeMap -list cubemapfile.lst -output cubemap.dds
  nvdxt -cubeMap -file cubemapfile.tga
  nvdxt -file test.tga -dxt1c
  nvdxt -file *.tga
  nvdxt -file c:\temp\*.tga
  nvdxt -file temp\*.tga
  nvdxt -file height_field_in_alpha.tga -n3x3 -alpha -scale 10 -wrap
  nvdxt -file grey_scale_height_field.tga -n5x5 -rgb -scale 1.3
  nvdxt -file normal_map.tga -norm
  nvdxt -file image.tga -dudv -fade -fadeamount 10
  nvdxt -all -dxt3 -gamma -outdir .\dds_dir -time
  nvdxt -file *.tga -depth -max -scale 0.5

'''


def material_name( mat ):
    if type(mat) is str: return mat
    elif not mat.library: return mat.name
    else: return mat.name + mat.library.filepath.replace('/','_')






try: import io_export_rogremesh.rogremesh as Rmesh
except:
    Rmesh = None
    print( 'WARNING: "io_export_rogremesh" is missing' )

if Rmesh and Rmesh.rpy.load(): _USE_RPYTHON_ = True
else:
    _USE_RPYTHON_ = False
    print( 'Rpython module is not cached, you must exit Blender to compile the module:' )
    print( 'cd io_export_rogremesh; python rogremesh.py' )


class VertexNoPos(object):
    def __init__(self, ogre_vidx, nx,ny,nz, r,g,b,ra, vert_uvs):
        self.ogre_vidx = ogre_vidx
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.r = r
        self.g = g
        self.b = b
        self.ra = ra
        self.vert_uvs = vert_uvs

    '''does not compare ogre_vidx (and position at the moment) [ no need to compare position ]'''
    def __eq__(self, o):
        if self.nx != o.nx or self.ny != o.ny or self.nz != o.nz: return False
        elif self.r != o.r or self.g != o.g or self.b != o.b or self.ra != o.ra: return False
        elif len(self.vert_uvs) != len(o.vert_uvs): return False
        elif self.vert_uvs:
            for i, uv1 in enumerate( self.vert_uvs ):
                uv2 = o.vert_uvs[ i ]
                if uv1 != uv2: return False
        return True


#######################################################################################
def dot_mesh( ob, path='/tmp', force_name=None, ignore_shape_animation=False, opts=OptionsEx, normals=True ):
    start = time.time()
    print('mesh to Ogre mesh XML format', ob.name)

    if not os.path.isdir( path ):
        print('creating directory', path )
        os.makedirs( path )

    Report.meshes.append( ob.data.name )
    Report.faces += len( ob.data.faces )
    Report.orig_vertices += len( ob.data.vertices )

    cleanup = False
    if ob.modifiers:
        cleanup = True
        copy = ob.copy()
        #bpy.context.scene.objects.link(copy)
        rem = []
        for mod in copy.modifiers:        # remove armature and array modifiers before collaspe
            if mod.type in 'ARMATURE ARRAY'.split(): rem.append( mod )
        for mod in rem: copy.modifiers.remove( mod )
        ## bake mesh ##
        mesh = copy.to_mesh(bpy.context.scene, True, "PREVIEW")    # collaspe
    else:
        copy = ob
        mesh = ob.data

    print('creating document...')

    name = force_name or ob.data.name
    xmlfile = os.path.join(path, '%s.mesh.xml' %name )

    if _USE_RPYTHON_ and False:
        Rmesh.save( ob, xmlfile )

    else:
        f = open( xmlfile, 'w' )
        doc = SimpleSaxWriter(f, 'UTF-8', "mesh", {})

        #//very ugly, have to replace number of vertices later
        doc.start_tag('sharedgeometry', {'vertexcount' : '__TO_BE_REPLACED_VERTEX_COUNT__'})

        print('    writing shared geometry')
        doc.start_tag('vertexbuffer', {
                'positions':'true',
                'normals':'true',
                'colours_diffuse' : str(bool( mesh.vertex_colors )),
                'texture_coords' : '%s' % len(mesh.uv_textures) if mesh.uv_textures.active else '0'
        })

        ## vertex colors ##
        vcolors = None
        vcolors_alpha = None
        if len( mesh.vertex_colors ):
            vcolors = mesh.vertex_colors[0]
            for bloc in mesh.vertex_colors:
                if bloc.name.lower().startswith('alpha'):
                    vcolors_alpha = bloc; break

        ######################################################

        materials = []
        for mat in ob.data.materials:
            if mat: materials.append( mat )
            else:
                print('warning: bad material data', ob)
                materials.append( '_missing_material_' )        # fixed dec22, keep proper index
        if not materials: materials.append( '_missing_material_' )
        _sm_faces_ = []
        for matidx, mat in enumerate( materials ):
            _sm_faces_.append([])


        dotextures = False
        uvcache = []    # should get a little speed boost by this cache
        if mesh.uv_textures.active:
            dotextures = True
            for layer in mesh.uv_textures:
                uvs = []; uvcache.append( uvs ) # layer contains: name, active, data
                for uvface in layer.data:
                    uvs.append( (uvface.uv1, uvface.uv2, uvface.uv3, uvface.uv4) )


        _sm_vertices_ = {}
        _remap_verts_ = []
        numverts = 0
        for F in mesh.faces:
            smooth = F.use_smooth
            #print(F, "is smooth=", smooth)
            faces = _sm_faces_[ F.material_index ]
            ## Ogre only supports triangles
            tris = []
            tris.append( (F.vertices[0], F.vertices[1], F.vertices[2]) )
            if len(F.vertices) >= 4: tris.append( (F.vertices[0], F.vertices[2], F.vertices[3]) )
            if dotextures:
                a = []; b = []
                uvtris = [ a, b ]
                for layer in uvcache:
                    uv1, uv2, uv3, uv4 = layer[ F.index ]
                    a.append( (uv1, uv2, uv3) )
                    b.append( (uv1, uv3, uv4) )
                    
                    
            
            for tidx, tri in enumerate(tris):
                face = []
                for vidx, idx in enumerate(tri):
                    v = mesh.vertices[ idx ]
                    
                    if smooth: nx,ny,nz = swap( v.normal )     # fixed june 17th 2011
                    else: nx,ny,nz = swap( F.normal )
                    
                    r = 1.0
                    g = 1.0
                    b = 1.0
                    ra = 1.0
                    if vcolors:
                        k = list(F.vertices).index(idx)
                        r,g,b = getattr( vcolors.data[ F.index ], 'color%s'%(k+1) )
                        if vcolors_alpha:
                            ra,ga,ba = getattr( vcolors_alpha.data[ F.index ], 'color%s'%(k+1) )
                        else:
                            ra = 1.0

                    ## texture maps ##
                    vert_uvs = []
                    if dotextures:
                        for layer in uvtris[ tidx ]:
                            vert_uvs.append(layer[ vidx ])
                    
                    
                    #check if we already exported that vertex with same normal, do not export in that case, (flat shading in blender seems to 
                    #work with face normals, so we copy each flat face' vertices, if this vertex with same normals was already exported,
                    #TODO: maybe not best solution, check other ways (let blender do all the work, or only support smooth shading, what about seems, smoothing groups, materials, ...)
                    vert = VertexNoPos(numverts, nx, ny, nz, r, g, b, ra, vert_uvs)
                    #print("DEBUG: %i %.9f %.9f %.9f len^2: %.9f" % (numverts, nx, ny, nz, nx*nx+ny*ny+nz*nz))
                    alreadyExported = False
                    if idx in _sm_vertices_:
                        for vert2 in _sm_vertices_[idx]:
                            #does not compare ogre_vidx (and position at the moment)
                            if vert == vert2:
                                face.append(vert2.ogre_vidx)
                                alreadyExported = True
                                #print(idx,numverts, nx,ny,nz, r,g,b,ra, vert_uvs, "already exported")
                                break
                        if not alreadyExported:
                            face.append(vert.ogre_vidx)
                            _sm_vertices_[idx].append(vert)
                            #print(numverts, nx,ny,nz, r,g,b,ra, vert_uvs, "appended")
                    else:
                        face.append(vert.ogre_vidx)
                        _sm_vertices_[idx] = [vert]
                        #print(idx, numverts, nx,ny,nz, r,g,b,ra, vert_uvs, "created")
                    
                    if alreadyExported:
                        continue
                    
                    numverts += 1
                    _remap_verts_.append( v )

                    x,y,z = swap(v.co)        # xz-y is correct!
                    
                    doc.start_tag('vertex', {})
                    doc.leaf_tag('position', {
                            'x' : '%6f' % x,
                            'y' : '%6f' % y,
                            'z' : '%6f' % z
                    })
                    
                    
                    doc.leaf_tag('normal', {
                            'x' : '%6f' % nx,
                            'y' : '%6f' % ny,
                            'z' : '%6f' % nz
                    })

                    if vcolors:
                        doc.leaf_tag('colour_diffuse', {'value' : '%6f %6f %6f %6f' % (r,g,b,ra)})

                    ## texture maps ##
                    if dotextures:
                        for uv in vert_uvs:
                            doc.leaf_tag('texcoord', {
                                    'u' : '%6f' % uv[0],
                                    'v' : '%6f' % (1.0-uv[1])
                            })
                    
                    
                    doc.end_tag('vertex')
                
                faces.append( (face[0], face[1], face[2]) )
                
        del(_sm_vertices_)
        Report.vertices += numverts
        
        doc.end_tag('vertexbuffer')
        doc.end_tag('sharedgeometry')
        print(' time: ', time.time()-start )
        print('    writing submeshes' )
        doc.start_tag('submeshes', {})
        for matidx, mat in enumerate( materials ):
            if not len(_sm_faces_[matidx]): continue	# fixes corrupt unused materials

            doc.start_tag('submesh', {
                    'usesharedvertices' : 'true',
                    'material' : material_name(mat),
                    #maybe better look at index of all faces, if one over 65535 set to true;
                    #problem: we know it too late, postprocessing of file needed
                    "use32bitindexes" : str(bool(numverts > 65535))
            })
            doc.start_tag('faces', {
                    'count' : str(len(_sm_faces_[matidx]))
            })
            for fidx, (v1, v2, v3) in enumerate(_sm_faces_[matidx]):
                doc.leaf_tag('face', {
                    'v1' : str(v1),
                    'v2' : str(v2),
                    'v3' : str(v3)
                })
            doc.end_tag('faces')
            doc.end_tag('submesh')
            Report.triangles += len(_sm_faces_[matidx])
        del(_sm_faces_)
        doc.end_tag('submeshes')

        
        arm = ob.find_armature()
        if arm:
            doc.leaf_tag('skeletonlink', {
                    'name' : '%s.skeleton' %(force_name or ob.data.name)
            })
            doc.start_tag('boneassignments', {})
            badverts = 0
            for vidx, v in enumerate(_remap_verts_):
                check = 0
                for vgroup in v.groups:
                    if vgroup.weight > opts['trim-bone-weights']:        #self.EX_TRIM_BONE_WEIGHTS:        # optimized
                        bnidx = find_bone_index(copy,arm,vgroup.group)
                        if bnidx is not None:        # allows other vertex groups, not just armature vertex groups
                            doc.leaf_tag('vertexboneassignment', {
                                    'vertexindex' : str(vidx),
                                    'boneindex' : str(bnidx),
                                    'weight' : str(vgroup.weight)
                            })
                            check += 1
                if check > 4:
                    badverts += 1
                    print('WARNING: vertex %s is in more than 4 vertex groups (bone weights)\n(this maybe Ogre incompatible)' %vidx)
            if badverts:
                Report.warnings.append( '%s has %s vertices weighted to too many bones (Ogre limits a vertex to 4 bones)\n[try increaseing the Trim-Weights threshold option]' %(mesh.name, badverts) )
            doc.end_tag('boneassignments')

        ############################################
        ## updated June3 2011 - shape animation works ##
        if opts['shape-anim'] and ob.data.shape_keys and len(ob.data.shape_keys.key_blocks):
            print('    writing shape keys')

            doc.start_tag('poses', {})
            for sidx, skey in enumerate(ob.data.shape_keys.key_blocks):
                if sidx == 0: continue
                if len(skey.data) != len( mesh.vertices ):
                    failure = 'FAILED to save shape animation - you can not use a modifier that changes the vertex count! '
                    failure += '[ mesh : %s ]' %mesh.name
                    Report.warnings.append( failure )
                    print( failure )
                    break

                doc.start_tag('pose', {
                        'name' : skey.name,
                        # If target is 'mesh', no index needed, if target is submesh then submesh identified by 'index'
                        #'index' : str(sidx-1),
                        #'index' : '0',
                        'target' : 'mesh'
                })

                for vidx, v in enumerate(_remap_verts_):
                    pv = skey.data[ v.index ]
                    x,y,z = swap( pv.co - v.co )
                    #for i,p in enumerate( skey.data ):
                    #x,y,z = p.co - ob.data.vertices[i].co
                    #x,y,z = swap( ob.data.vertices[i].co - p.co )
                    #if x==.0 and y==.0 and z==.0: continue        # the older exporter optimized this way, is it safe?
                    doc.leaf_tag('poseoffset', {
                            'x' : '%6f' % x,
                            'y' : '%6f' % y,
                            'z' : '%6f' % z,
                            'index' : str(vidx)     # is this required?
                    })
                doc.end_tag('pose')
            doc.end_tag('poses')

            if ob.data.shape_keys.animation_data and len(ob.data.shape_keys.animation_data.nla_tracks):
                print('    writing shape animations')
                doc.start_tag('animations', {})
                _fps = float( bpy.context.scene.render.fps )
                for nla in ob.data.shape_keys.animation_data.nla_tracks:
                    for idx, strip in enumerate(nla.strips):
                        doc.start_tag('animation', {
                                'name' : strip.name,
                                'length' : str((strip.frame_end-strip.frame_start)/_fps)
                        })
                        doc.start_tag('tracks', {})
                        doc.start_tag('track', {
                                'type' : 'pose',
                                'target' : 'mesh'
                                # If target is 'mesh', no index needed, if target is submesh then submesh identified by 'index'
                                #'index' : str(idx)
                                #'index' : '0'
                        })
                        doc.start_tag('keyframes', {})
                        for frame in range( int(strip.frame_start), int(strip.frame_end), bpy.context.scene.frame_step):
                            bpy.context.scene.frame_set(frame)
                            doc.start_tag('keyframe', {
                                    'time' : str((frame-strip.frame_start)/_fps)
                            })
                            for sidx, skey in enumerate( ob.data.shape_keys.key_blocks ):
                                if sidx == 0: continue
                                doc.leaf_tag('poseref', {
                                        'poseindex' : str(sidx-1),
                                        'influence' : str(skey.value)
                                })
                            doc.end_tag('keyframe')
                        doc.end_tag('keyframes')
                        doc.end_tag('track')
                        doc.end_tag('tracks')
                        doc.end_tag('animation')
                doc.end_tag('animations')


        ########## clean up and save #############
        #bpy.context.scene.meshes.unlink(mesh)
        if cleanup:
            #bpy.context.scene.objects.unlink(copy)
            bpy.data.objects.remove(copy)
            bpy.data.meshes.remove(mesh)
            mesh.user_clear()
            copy.user_clear()
            del copy
            del mesh

        del _remap_verts_
        del uvcache

        doc.close()     # reported by Reyn
        f.close()

    #finally:
    #    if doc:
    #        doc.close()
    #    if f:
    #        f.close()


    #very ugly, find better way
    def replaceInplace(f,searchExp,replaceExp):
            import fileinput
            for line in fileinput.input(f, inplace=1):
                if searchExp in line:
                    line = line.replace(searchExp,replaceExp)
                sys.stdout.write(line)
            fileinput.close()   # reported by jakob
    
    replaceInplace(xmlfile, '__TO_BE_REPLACED_VERTEX_COUNT__' + '"', str(numverts) + '"' )#+ ' ' * (ls - lr))
    del(replaceInplace)
    
    
    OgreXMLConverter( xmlfile, opts )

    

    if arm and opts['armature-anim']:
        skel = Skeleton( ob )
        data = skel.to_xml()
        name = force_name or ob.data.name
        xmlfile = os.path.join(path, '%s.skeleton.xml' %name )
        f = open( xmlfile, 'wb' )
        f.write( bytes(data,'utf-8') )
        f.close()
        OgreXMLConverter( xmlfile, opts )

    mats = []
    for mat in materials:
        if mat != '_missing_material_': mats.append( mat )

    print('*'*80)
    print( 'TIME: ', time.time()-start )
    return mats

## end dot_mesh ##


class TundraPreviewOp(bpy.types.Operator,  _OgreCommonExport_):
    '''helper to open Tundra2 (realXtend)'''
    bl_idname = 'tundra.preview'
    bl_label = "opens Tundra2 in a non-blocking subprocess"
    bl_options = {'REGISTER'}

    filepath= StringProperty(name="File Path", description="Filepath used for exporting Tundra .txml file", maxlen=1024, default="/tmp/preview.txml", subtype='FILE_PATH')
    EXPORT_TYPE = 'REX'

    EX_SWAP_MODE = EnumProperty( 
        items=AXIS_MODES, 
        name='swap axis',  
        description='axis swapping mode', 
        default='xz-y' 
    )

    @classmethod
    def poll(cls, context):
        if context.active_object: return True

    def invoke(self, context, event):
        global TundraSingleton
        path = '/tmp/preview.txml'
        self.ogre_export( path, context )
        if not TundraSingleton:
            TundraSingleton = TundraPipe()
        else:   # TODO
            pass    #TundraSingleton.load( path )
        return {'FINISHED'}

TundraSingleton = None

class Tundra_StartPhysicsOp(bpy.types.Operator):
    '''TundraSingleton helper'''
    bl_idname = 'tundra.start_physics'
    bl_label = "start physics"
    bl_options = {'REGISTER'}
    @classmethod
    def poll(cls, context):
        if TundraSingleton: return True
    def invoke(self, context, event):
        TundraSingleton.start()
        return {'FINISHED'}

class Tundra_StopPhysicsOp(bpy.types.Operator):
    '''TundraSingleton helper'''
    bl_idname = 'tundra.stop_physics'
    bl_label = "stop physics"
    bl_options = {'REGISTER'}
    @classmethod
    def poll(cls, context):
        if TundraSingleton: return True
    def invoke(self, context, event):
        TundraSingleton.stop()
        return {'FINISHED'}

class Tundra_PhysicsDebugOp(bpy.types.Operator):
    '''TundraSingleton helper'''
    bl_idname = 'tundra.toggle_physics_debug'
    bl_label = "stop physics"
    bl_options = {'REGISTER'}
    @classmethod
    def poll(cls, context):
        if TundraSingleton: return True
    def invoke(self, context, event):
        TundraSingleton.toggle_physics_debug()
        return {'FINISHED'}



class TundraPipe(object):
    def __init__(self):
        self._physics_debug = True
        exe = os.path.join( CONFIG_TUNDRA_ROOT, 'Tundra.exe' )
        if sys.platform == 'linux2':
            cmd = ['wine', exe, '--file', '/tmp/preview.txml']#, '--config', TUNDRA_CONFIG_XML_PATH]
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        else:
            cmd = [exe, '--file', '/tmp/preview.txml']#, '--config', TUNDRA_CONFIG_XML_PATH]
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        time.sleep(0.1)
        self.stop()

    def load( self, url ):
        self.proc.stdin.write( b'loadscene(/tmp/preview.txml, true, true)\n')
        self.proc.stdin.flush()

    def start( self ):
        self.proc.stdin.write( b'startphysics\n' )
        self.proc.stdin.flush()

    def stop( self ):
        self.proc.stdin.write( b'stopphysics\n' )
        self.proc.stdin.flush()

    def toggle_physics_debug( self ):
        self._physics_debug = not self._physics_debug
        self.proc.stdin.write( b'physicsdebug\n' )
        self.proc.stdin.flush()


class INFO_HT_myheader(bpy.types.Header):
    bl_space_type = 'INFO'
    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        window = context.window
        scene = context.scene
        rd = scene.render
        ob = context.active_object
        screen = context.screen

        layout.separator()
        if _USE_TUNDRA_:
            row = layout.row(align=True)
            op = row.operator( 'tundra.preview', text='', icon='WORLD' )
            if TundraSingleton:
                op = row.operator( 'tundra.start_physics', text='', icon='PLAY' )
                op = row.operator( 'tundra.stop_physics', text='', icon='PAUSE' )
                op = row.operator( 'tundra.toggle_physics_debug', text='', icon='WIRE' )

        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.menu("INFO_MT_file")
        sub.menu("INFO_MT_add")
        if rd.use_game_engine: sub.menu("INFO_MT_game")
        else: sub.menu("INFO_MT_render")

        op = layout.operator( Ogre_ogremeshy_op.bl_idname, text='', icon='PLUGIN' ); op.mesh = True

        row = layout.row(align=False); row.scale_x = 1.25
        row.menu("INFO_MT_instances", icon='NODETREE', text='')
        row.menu("INFO_MT_groups", icon='GROUP', text='')
        #row.menu("INFO_MT_actors", icon='GAME')        # not useful?
        #row.menu("INFO_MT_dynamics", icon='PHYSICS')   # not useful?
        #layout.separator()

        layout.template_header()
        if not context.area.show_menus:
            if window.screen.show_fullscreen: layout.operator("screen.back_to_previous", icon='SCREEN_BACK', text="Back to Previous")
            else: layout.template_ID(context.window, "screen", new="screen.new", unlink="screen.delete")
            layout.template_ID(context.screen, "scene", new="scene.new", unlink="scene.delete")

            layout.separator()
            layout.template_running_jobs()
            layout.template_reports_banner()
            layout.separator()
            if rd.has_multiple_engines: layout.prop(rd, "engine", text="")

            layout.label(text=scene.statistics())
            layout.menu( "INFO_MT_help" )

        else:
            layout.template_ID(context.window, "screen", new="screen.new", unlink="screen.delete")

            if ob:
                row = layout.row(align=True)
                row.prop( ob, 'name', text='' )
                row.prop( ob, 'draw_type', text='' )
                row.prop( ob, 'show_x_ray', text='' )
                row = layout.row()
                row.scale_y = 0.75
                row.prop( ob, 'layers', text='' )

            layout.separator()
            row = layout.row(align=True); row.scale_x = 1.1
            row.prop(scene.game_settings, 'material_mode', text='')
            row.prop(scene, 'camera', text='')



            layout.menu( "INFO_MT_ogre_docs" )
            layout.operator("wm.window_fullscreen_toggle", icon='FULLSCREEN_ENTER', text="")


def export_menu_func_ogre(self, context):
    path,name = os.path.split( context.blend_data.filepath )
    op = self.layout.operator(INFO_OT_createOgreExport.bl_idname, text="Ogre3D (.scene and .mesh)")
    op.filepath = os.path.join( path, name.split('.')[0]+'.scene' )

def export_menu_func_realxtend(self, context):
    path,name = os.path.split( context.blend_data.filepath )
    op = self.layout.operator(INFO_OT_createRealxtendExport.bl_idname, text="RealXtend (.txml and .mesh)")
    op.filepath = os.path.join( path, name.split('.')[0]+'.txml' )



_header_ = None
class OGRE_toggle_toolbar_op(bpy.types.Operator):
    '''Toggle Ogre UI'''
    bl_idname = "ogre.toggle_interface"
    bl_label = "Ogre UI"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        global _header_
        if _header_:
            bpy.utils.unregister_module(__name__)
            bpy.utils.register_class(_header_)
            _header_ = None
            for op in _OGRE_MINIMAL_: bpy.utils.register_class( op )
            bpy.utils.register_class( INFO_HT_microheader )
        else:
            bpy.utils.register_module(__name__)
            _header_ = bpy.types.INFO_HT_header
            bpy.utils.unregister_class(_header_)
            bpy.utils.unregister_class( INFO_HT_microheader )

        return {'FINISHED'}

class INFO_HT_microheader(bpy.types.Header):
    bl_space_type = 'INFO'
    def draw(self, context):
        layout = self.layout
        try: op = layout.operator( 'ogre.toggle_interface' )
        except: pass    # reported by Reyn

_OGRE_MINIMAL_ = ( INFO_OT_createOgreExport, INFO_OT_createRealxtendExport, OGRE_toggle_toolbar_op, Ogre_User_Report)
_USE_TUNDRA_ = False

MyShaders = None
def register():
    print( '-'*80)
    print(VERSION)
    global MyShaders, _header_, _USE_TUNDRA_
    #bpy.utils.register_module(__name__)
    #_header_ = bpy.types.INFO_HT_header
    #bpy.utils.unregister_class(_header_)
    for op in _OGRE_MINIMAL_: bpy.utils.register_class( op )
    bpy.utils.register_class( INFO_HT_microheader )

    readOrCreateConfig()

    ## only test for Tundra2 once ##
    if os.path.isdir( CONFIG_TUNDRA_ROOT ): _USE_TUNDRA_ = True
    else: _USE_TUNDRA_ = False

    MyShaders = MyShadersSingleton()
    bpy.types.INFO_MT_file_export.append(export_menu_func_ogre)
    bpy.types.INFO_MT_file_export.append(export_menu_func_realxtend)

    if os.path.isdir( CONFIG_MYSHADERS_DIR ):
        update_parent_material_path( CONFIG_MYSHADERS_DIR )
    else: print( 'WARNING: invalid my-shaders path' )

    print( '-'*80)

def unregister():
    global _header_
    print('unreg-> ogre exporter')
    bpy.utils.unregister_module(__name__)
    if _header_: bpy.utils.register_class(_header_); _header_ = None
    bpy.types.INFO_MT_file_export.remove(export_menu_func_ogre)
    bpy.types.INFO_MT_file_export.remove(export_menu_func_realxtend)


if __name__ == "__main__":
    register()


###### RPython xml dom ######
class RElement(object):
	def appendChild( self, child ): self.childNodes.append( child )
	def setAttribute( self, name, value ): self.attributes[name]=value

	def __init__(self, tag):
		self.tagName = tag
		self.childNodes = []
		self.attributes = {}

	def toprettyxml(self, lines, indent ):
		s = '<%s ' %self.tagName
		for name in self.attributes:
			value = self.attributes[name]
			s += '%s="%s" ' %(name,value)
		if not self.childNodes:
			s += '/>'; lines.append( ('\t'*indent)+s )
		else:
			s += '>'; lines.append( ('\t'*indent)+s )
			indent += 1
			for child in self.childNodes:
				child.toprettyxml( lines, indent )
			indent -= 1
			lines.append( ('\t'*indent)+'</%s>' %self.tagName )


class RDocument(object):
	def __init__(self): self.documentElement = None
	def appendChild(self,root): self.documentElement = root
	def createElement(self,tag): e = RElement(tag); e.document = self; return e
	def toprettyxml(self):
		indent = 0
		lines = []
		self.documentElement.toprettyxml( lines, indent )
		return '\n'.join( lines )


class SimpleSaxWriter():
    def __init__(self, output, encoding, top_level_tag, attrs):
        xml_writer = XMLGenerator(output, encoding, True)
        xml_writer.startDocument()
        xml_writer.startElement(top_level_tag, attrs)
        self._xml_writer = xml_writer
        self.top_level_tag = top_level_tag
        self.ident=4
        self._xml_writer.characters('\n')

    def start_tag(self, name, attrs):
        self._xml_writer.characters(" " * self.ident)
        self._xml_writer.startElement(name, attrs)
        self.ident += 4
        self._xml_writer.characters('\n')

    def end_tag(self, name):
        self.ident -= 4
        self._xml_writer.characters(" " * self.ident)
        self._xml_writer.endElement(name)
        self._xml_writer.characters('\n')

    def leaf_tag(self, name, attrs):
        self._xml_writer.characters(" " * self.ident)
        self._xml_writer.startElement(name, attrs)
        self._xml_writer.endElement(name)
        self._xml_writer.characters('\n')

    def close(self):
        self._xml_writer.endElement(self.top_level_tag)
        self._xml_writer.endDocument()



bpy.types.World.ogre_skyX = BoolProperty(
    name="enable sky", description="ogre sky",
    default=True
)

bpy.types.World.ogre_skyX_time = FloatProperty(
    name="Time Multiplier",
    description="change speed of day/night cycle", 
    default=0.3, min=0.0, max=5.0
)

bpy.types.World.ogre_skyX_wind = FloatProperty(
    name="Wind Direction",
    description="change direction of wind", 
    default=33.0, min=0.0, max=360.0
)

bpy.types.World.ogre_skyX_volumetric_clouds = BoolProperty(
    name="volumetric clouds", description="toggle ogre volumetric clouds",
    default=True
)
bpy.types.World.ogre_skyX_cloud_density_x = FloatProperty(
    name="Cloud Density X",
    description="change density of volumetric clouds on X", 
    default=0.1, min=0.0, max=5.0
)
bpy.types.World.ogre_skyX_cloud_density_y = FloatProperty(
    name="Cloud Density Y",
    description="change density of volumetric clouds on Y", 
    default=1.0, min=0.0, max=5.0
)



class OgreSkyPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "world"
    bl_label = "Ogre Sky Settings"
    @classmethod
    def poll(cls, context): return True
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.prop( context.world, 'ogre_skyX' )
        if context.world.ogre_skyX:
            box.prop( context.world, 'ogre_skyX_time' )
            box.prop( context.world, 'ogre_skyX_wind' )
            box.prop( context.world, 'ogre_skyX_volumetric_clouds' )
            if context.world.ogre_skyX_volumetric_clouds:
                box.prop( context.world, 'ogre_skyX_cloud_density_x' )
                box.prop( context.world, 'ogre_skyX_cloud_density_y' )



_OGRE_MATERIAL_CLASS_SCRIPT = {}

#####################################################################################










#####################################################################################
###################################### Public API #####################################

def export_mesh( ob, path='/tmp', force_name=None, ignore_shape_animation=False, normals=True ):
    ''' returns materials used by the mesh '''
    return dot_mesh( ob, path, force_name, ignore_shape_animation, opts, normals )


def generate_material( mat, path ):
    ''' returns generated material string '''
    return INFO_OT_createOgreExport.gen_dot_material( mat, path=path )


## updates RNA ##
def update_parent_material_path( path ):
    global _OGRE_MATERIAL_CLASS_SCRIPT
    print( '>>SEARCHING FOR OGRE MATERIALS: %s' %path )
    items = [ ('', '', 'none') ]
    classes = []
    for sub in os.listdir( path ):
        a = os.path.join( path, sub )
        for name in os.listdir( a ):
            if name.endswith( '.material' ):
                print( '>>', name )
                url = os.path.join( a, name )
                data = open( url, 'rb' ).read()
                for line in data.splitlines():
                    line = line.strip()
                    if line.startswith(b'material'):
                        cls = line.split()[-1].decode('utf-8')
                        print('>>>>', cls )
                        if cls not in classes:
                            classes.append( cls )
                            items.append( (cls,cls,url) )
                            _OGRE_MATERIAL_CLASS_SCRIPT[ cls ] = name   # name.material

    bpy.types.Material.ogre_parent_material = EnumProperty(
        name="Script Inheritence", 
        description='ogre parent material class', default='',
        items=items,
    )





def get_subcollision_meshes():
    ''' returns all collision meshes found in the scene '''
    r = []
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH' and ob.subcollision: r.append( ob )
    return r

def get_objects_with_subcollision():
    ''' returns objects that have active sub-collisions '''
    r = []
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH' and ob.collision_mode not in ('NONE', 'PRIMITIVE'):
            r.append( ob )
    return r

def get_subcollisions(ob):
    prefix = '%s.' %ob.collision_mode
    r = []
    for child in ob.children:
        if child.subcollision and child.name.startswith( prefix ):
            r.append( child )
    return r


def _create_material_passes( mat ):
    mat.use_nodes = True
    tree = mat.node_tree	# valid pointer
    #<tree bpy.data.node_groups['Shader Nodetree']>
    for i in range( 8 ):
        node = tree.nodes.new( type='MATERIAL' )
        node.name = 'GEN.%s' %i
    mat.use_nodes = False

def get_or_create_material_passes( mat ):
    if not mat.node_tree: _create_material_passes( mat )
    r = []
    for node in mat.node_tree.nodes:
        if node.type == 'MATERIAL' and node.name.startswith('GEN.'):
            r.append( node )
    return r

class CreateMaterialPassesOp(bpy.types.Operator):
    '''operator: finds missing textures - checks directories with textures to see if missing are there.'''  
    bl_idname = "ogre.force_setup_material_passes"  
    bl_label = "relocate textures"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.active_material: return True

    def invoke(self, context, event):
        mat = context.active_object.active_material
        mat.use_material_passes = True
        _create_material_passes( mat )
        return {'FINISHED'}


