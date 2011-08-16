# Copyright (C) 2005  Michel Reimpell    [ blender24 version ]
# Copyright (C) 2010 Brett Hartshorn    [ blender25 version ]
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
    "version": (0,5,1),
    "blender": (2,5,8),
    "location": "File > Export...",
    "description": "Export to Ogre xml and binary formats",
    "warning": "Quick Start: '.mesh' output requires OgreCommandLineTools (http://www.ogre3d.org/download/tools) - install to the default path.",
    "wiki_url": "http://code.google.com/p/blender2ogre/w/list",
    "tracker_url": "http://code.google.com/p/blender2ogre/issues/list",
    "category": "Import-Export"}

VERSION = '0.5.1 RDotMesh-test1'


__devnotes__ = '''

## b2rex touches these, so keep the names! ##
ogre_mesh_entity_helper = addon_ogreDotScene.INFO_OT_createOgreExport._node_export
ogre_material_export = addon_ogreDotScene.INFO_OT_createOgreExport.gen_dot_material


Jan 6th 2011 (Hart):
    . updated for blender256
    . fixed Nvidia DDS output
    . add swap axis options

March 18th (SRombauts):
    . issue1: os.getlogin() unreliable; using getpass.getuser() instead
    . issue5: speed optimization O(n^2) into O(n log n)

March 20th (SRombauts):
    . correction to bl_info
    
March 21th (SRombauts):
    . Blender SVN compatibility : using bl_info for printing version when registering
    . Blender SVN compatibility : using prefix "ogre." in bl_idname of any custom bpy.types.Operator (and using this definition instead of a string)
    . Blender SVN compatibility : registering the module is requiered in Blender SVN >2.56 to use operators
    . Blender SVN compatibility : mathutils.Matrix format changed in Blender SVN >2.56

March 25th (SRombauts):
    . issue7: Need for an add-on config file with user preferences
    . issue10: No more tabulation, using the standard 4 spaces recommanded by the Python PEP-8
    
March 31th (SRombauts):
    . Issue 14: DEFAULT_IMAGE_MAGICK_CONVERT uninitialized under Windows
    . 0.3.2 release

April 3rd (SRombauts):
    . Issue 9:  Blender script/addon name must be changed
    . Issue 15: Use an appropriate path for the addon config file
    . 0.3.3 release

May 11th (Hart):
    . small fixes

May 12th (Hart):
    . fixed ogre-export being forced to .txml
    . fixed multi-track animation export, cleaned up doc, added examples.    

May 16th (Hart):
    . tested again in OgreMeshy under linux, fixed works again.
    . really fixed multi-track animation
    . confirmed that shape-animation is badly broken, needs redesign.

June 2nd (Hart):
    . mesh export speedup
    . fixed shape animation export

June 6th (Hart):
    . fixed merge groups
    . added OSX patch
    . dot scene more conformant to spec
    . closed several issues on the tracker
    . fixed multiple materials on single mesh
    . fixed uv textures

June 7th (Hart):
    . really fixed uvs
    . fixed ubuntu (different naming for OgreXMLConverter when using apt-get ogre-tools)
    . fixed Texture Panel and rotation animation option changed to use_from_dupli

June 12th (Hart):
    . fixed collision panel - if not ob.show_bounds: ob.show_bounds = True
    . fixed sharp face normals
    . fixed badverts
    . supports library linking with name collisions

June 18th (Hart):
    . fixed usealpha line: 1959
    . fixed floating bones
    . changed default axis to x z -y
    . fixed ogre_user_report not found if toolbar not enabled

June 30th (Hart):
    . Fixed Lamp export "color" to British "colour" - reported by Mohdakra
    . New spotLightRange inner and outer options
    . Fixed sharedGeometry vertexcount, compatible with jMonkeyEngine
    . New Lamp option powerScale taken from Lamp energy
    . OgreMeshy preview disabled when in mesh-edit mode.

July 2nd (Hart):
    . Fixed fog settings - reported by junode
July 3rd (Hart):
    . Fixed lamp direction - reported by Mohdakra
July 22nd (Hart):
    . Fixed (untested) 32bit indices - should be on submesh not sharedgeo
July 25th (Hart):
    . Improved memory and performance - replaced xml.dom.minidom with custom microdom

July 26th (f00bar):
    . mesh.xml is directly written to file [class SimpleSaxWriter() at end of script]
    . material file name is derived from .scene file name (bpy.context.scene.name always returns "Scene" for me)
    . [shape keys] bpy.context.scene.frame_current did not work (so all values were from current time), now using bpy.context.scene.frame_set(frame)
    . [shape keys] poseindex: need to subtract 1, because shape 0 is base and not written to the file
    . not writing an "index" on "pose" and "track", the index is for the case where "target" is "submesh"
    . "use32bitindexes" : str(bool(numverts > 65535)) is used, that means it is set in cases not needed, but that way it needs no postprocessing of file
    . ugly: function replaceInplace, using fileinput module to write number of vertices into file at end (could write into it without processing the whole file)

July 27th (Hart):
    . reviewed F00bar's changes
    . replaced bpy.data.objects with bpy.context.scene.objects - and tested multiple scene export

August 12th (f00bar):
    . using (nx,ny,nz, r,g,b,ra, vert_uvs) to check if vertex must be duplicated.
         - this is overkill, but it can be replaced when bmesh comes out
    . hopefully fixed bug with deleted materials which blender returns as None
    . small fixes (e.g. Report, being sure mesh.xml file is closed,...)

August 13th (Hart):
    . went back to axis swap "-x z y" - this is the Ogre default
    . fixed swap axis for .txml output
    . removed swap axis option - from now on its always Ogre default
    . merged with f00bar's updates
    . export armature and shape animation now respects FPS
    . shape animation now respects bpy.context.scene.frame_step
    . shadeless material sets emissive to 1.0


'''

# to compare floats (e.g. to decide if vertex in two faces has similar normal, uvs, ... or if vertex must be duplicated)
# tested by looking at normals of subdivided cube, errors in that example were up to 0.000000581
EPSILON=0.000001

# Hardcoded to Ogre Default #
def swap( vec ):
    if len(vec) == 3: return mathutils.Vector( [-vec[0], vec[2], vec[1]] )
    elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, -vec.x, vec.z, vec.y] )
    else: assert 0

## Deprecated
def swap_old(vec):
    if OPTIONS['SWAP_AXIS'] == 'x y z': return vec
    elif OPTIONS['SWAP_AXIS'] == 'x z y':
        if len(vec) == 3: return mathutils.Vector( [vec.x, vec.z, vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, vec.x, vec.z, vec.y] )
    elif OPTIONS['SWAP_AXIS'] == '-x z y':
        if len(vec) == 3: return mathutils.Vector( [-vec.x, vec.z, vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, -vec.x, vec.z, vec.y] )
    elif OPTIONS['SWAP_AXIS'] == 'x z -y':
        if len(vec) == 3: return mathutils.Vector( [vec.x, vec.z, -vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, vec.x, vec.z, -vec.y] )
    else:
        print( 'unknown swap axis mode', OPTIONS['SWAP_AXIS'] )

_faq_ = '''

Q: i have hundres of objects, is there a way i can merge them on export only?
A: yes, just add them to a group named starting with "merge"

Q: can i use subsurf or multi-res on a mesh with an armature?
A: yes.

Q: can i use subsurf or multi-res on a mesh with shape animation?
A: no.

Q: i don't see any objects when i export?
A: you must select the objects you wish to export.

Q: how can i change the name of my .material file, it is always named Scene.material?
A: rename your scene in blender.  The .material script will follow the name of the scene.

Q: i don't see my animations when exported?
A: make sure you created an NLA strip on the armature, and if you keyed bones in pose mode then only those will be exported.

Q: do i need to bake my IK and other constraints into FK on my armature before export?
A: no.

Q: how do i export extra information to my game engine via OgreDotScene?
A: You can assign 'Custom Properties' to objects in blender, and these will be saved to the .scene file.

Q: i want to use a low-resolution mesh as a collision proxy for my high-resolution mesh, how?
A: make the lowres mesh the child of the hires mesh, and name the low res mesh starting with "collision"

Q: i do not want to use triangle mesh collision, can i use simple collision primitives?
A: yes, go to View3D->Tools->Ogre Physics.  This gets save to the OgreDotScene file.

'''


_doc_installing_ = '''
Installing:
    Installing the Addon:
        You can simply copy io_export_ogreDotScene.py to your blender installation under blender/2.57/scripts/addons/
        and enable it in the user-prefs interface (CTRL+ALT+U)
        Or you can use blenders interface, under user-prefs, click addons, and click 'install-addon'
        (its a good idea to delete the old version first)

    Required:
        1. blender2.58

        2. Install Ogre Command Line tools to the default path ( C:\\OgreCommandLineTools )
            http://www.ogre3d.org/download/tools
            (Linux users may use above and Wine, or install from source, or install via apt-get install ogre-tools)

    Optional:
        3. Install NVIDIA DDS Legacy Utilities    ( install to default path )
            http://developer.nvidia.com/object/dds_utilities_legacy.html
            (Linux users will need to use Wine)

        4. Install Image Magick
            http://www.imagemagick.org

        5. Copy folder 'myshaders' to C:\\myshaders
            (Linux copy to your home folder)

        6. Copy OgreMeshy to C:\\OgreMeshy
            If your using 64bit Windows, you may need to download a 64bit OgreMeshy
            (Linux copy to your home folder)

'''


######
# imports
######
import os, sys, time, hashlib, getpass, tempfile , configparser
import math, subprocess
#sax xml:
from xml.sax.saxutils import XMLGenerator


try:
    import bpy, mathutils
    from bpy.props import *
except ImportError:
    sys.exit("This script is an addon for blender, you must install it from blender.")


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
    global     CONFIG_TEMP_DIR, CONFIG_OGRETOOLS_XML_CONVERTER, CONFIG_OGRETOOLS_MESH_MAGICK, CONFIG_OGRE_MESHY, CONFIG_IMAGE_MAGICK_CONVERT, CONFIG_NVIDIATOOLS_EXE, CONFIG_MYSHADERS_DIR
    
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
        DEFAULT_MYSHADERS_DIR = 'C:\\myshaders'
        
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):        # OSX patch by FreqMod June6th 2011
        # DEFAULT_TEMP_PATH = '/tmp' 
        DEFAULT_OGRETOOLS_XML_CONVERTER = '/usr/bin/OgreXmlConverter'
        DEFAULT_OGRETOOLS_MESH_MAGICK = '/usr/bin/MeshMagick'

        if not os.path.isfile( DEFAULT_OGRETOOLS_XML_CONVERTER ):
            if os.path.isfile( '/usr/local/bin/OgreXMLConverter'):
                DEFAULT_OGRETOOLS_XML_CONVERTER = '/usr/local/bin/OgreXMLConverter'
            if os.path.isfile( '%s/.wine/drive_c/OgreCommandLineTools/OgreXmlConverter.exe' %os.environ['HOME'] ):
                DEFAULT_OGRETOOLS_XML_CONVERTER = '%s/.wine/drive_c/OgreCommandLineTools/OgreXmlConverter.exe' %os.environ['HOME']
                DEFAULT_OGRETOOLS_MESH_MAGICK = '%s/.wine/drive_c/OgreCommandLineTools/MeshMagick.exe' %os.environ['HOME']
            elif os.path.isfile( '/usr/bin/OgreXMLConverter'):   # ubuntu ogre-tools package changes name of OgreXmlConverter to OgreXMLConverter
                DEFAULT_OGRETOOLS_XML_CONVERTER = '/usr/bin/OgreXMLConverter'


        DEFAULT_OGRE_MESHY = '%s/OgreMeshy/Ogre Meshy.exe' %os.environ['HOME']

        DEFAULT_IMAGE_MAGICK_CONVERT = '/usr/bin/convert/convert'
        if not os.path.isfile( DEFAULT_IMAGE_MAGICK_CONVERT ): DEFAULT_IMAGE_MAGICK_CONVERT = '/usr/local/bin/convert/convert'

        DEFAULT_NVIDIATOOLS_EXE = '%s/.wine/drive_c/Program Files/NVIDIA Corporation/DDS Utilities' %os.environ['HOME']
        DEFAULT_MYSHADERS_DIR = '%s/myshaders' %os.environ['HOME']
        
    # Compose the path to the config file, in the config/scripts subfolder
    config_path = bpy.utils.user_resource('CONFIG', path='scripts', create=True)
    config_filepath = os.path.join(config_path, CONFIG_FILENAME)

    # Read the blender2ogre.cfg config file for addon options (or create a 'paths' section if not present)
    print('Opening config file %s ...' % config_filepath)
    config = configparser.ConfigParser()
    config.read(config_filepath)
    if not config.has_section('paths'):
        config.add_section('paths')

    # Read (or create default) config values
    CONFIG_TEMP_DIR                = readOrCreateConfigValue(config, 'paths', 'TEMP_DIR',                DEFAULT_TEMP_DIR)
    CONFIG_OGRETOOLS_XML_CONVERTER = readOrCreateConfigValue(config, 'paths', 'OGRETOOLS_XML_CONVERTER', DEFAULT_OGRETOOLS_XML_CONVERTER)
    CONFIG_OGRETOOLS_MESH_MAGICK   = readOrCreateConfigValue(config, 'paths', 'OGRETOOLS_MESH_MAGICK',   DEFAULT_OGRETOOLS_MESH_MAGICK)
    CONFIG_OGRE_MESHY              = readOrCreateConfigValue(config, 'paths', 'OGRE_MESHY',              DEFAULT_OGRE_MESHY)
    CONFIG_IMAGE_MAGICK_CONVERT    = readOrCreateConfigValue(config, 'paths', 'IMAGE_MAGICK_CONVERT',    DEFAULT_IMAGE_MAGICK_CONVERT)
    CONFIG_NVIDIATOOLS_EXE         = readOrCreateConfigValue(config, 'paths', 'NVIDIATOOLS_EXE',         DEFAULT_NVIDIATOOLS_EXE)
    CONFIG_MYSHADERS_DIR           = readOrCreateConfigValue(config, 'paths', 'MYSHADERS_DIR',           DEFAULT_MYSHADERS_DIR)

    # Write the blender2ogre.cfg config file 
    with open(config_filepath, 'w') as configfile:
        config.write(configfile)
        print('config file %s written.' % config_filepath)

    # Print config values
    print('CONFIG_TEMP_DIR=%s'                % CONFIG_TEMP_DIR)
    print('CONFIG_OGRETOOLS_XML_CONVERTER=%s' % CONFIG_OGRETOOLS_XML_CONVERTER)
    print('CONFIG_OGRETOOLS_MESH_MAGICK=%s'   % CONFIG_OGRETOOLS_MESH_MAGICK)
    print('CONFIG_OGRE_MESHY=%s'              % CONFIG_OGRE_MESHY)
    print('CONFIG_IMAGE_MAGICK_CONVERT=%s'    % CONFIG_IMAGE_MAGICK_CONVERT)
    print('CONFIG_NVIDIATOOLS_EXE=%s'         % CONFIG_NVIDIATOOLS_EXE)
    print('CONFIG_MYSHADERS_DIR=%s'           % CONFIG_MYSHADERS_DIR)


# 





# options yet to be added to the config file
OPTIONS = {
    'FORCE_IMAGE_FORMAT' : None,
    'TEXTURES_SUBDIR' : False,
    'PATH' : '/tmp',    # TODO SRombauts: use the CONFIG_TEMP_DIR variable
    'TOUCH_TEXTURES' : False,
    #'SWAP_AXIS' : '-x z y',        # this was not correct when viewed in OgreMeshy
    #'SWAP_AXIS' : 'x z -y',         # this is ogre standard?
    'SWAP_AXIS' : '-x z y',         # ogre standard
}


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

############## Lite Version Control ###############
VersionControl = '_version_  _modified_  _created_'.split()
VersionControlUser = '_category_  _title_  _notes_  _owner_'.split()
VersionControlMesh = '_update_mesh_  _update_material_'.split()

def UUID( ob ):
    #s = ''
    keys = ob.keys()
    #for tag in VersionControl + VersionControlUser
    if '_UUID_' in keys: return ob[ '_UUID_' ]
    else:
        s = str(time.time()) + ob.name
        uid = hashlib.md5(bytes(s, 'utf-8')).hexdigest()
        ob[ '_UUID_' ] = uid
        return uid

class Ogre_setup_version_control_op(bpy.types.Operator):
    '''operator: setup version control helper'''  
    bl_idname = "ogre.setup_version_control"  
    bl_label = "setup version control"
    bl_options = {'REGISTER'}
    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        ob = context.active_object
        if ob:
            keys = ob.keys()
            now = time.time()
            if '_created_' not in keys: ob['_created_'] = now
            if '_modified_' not in keys: ob['_modified_'] = now
            if '_version_' not in keys: ob['_version_'] = 0
            if '_category_' not in keys: ob['_category_'] = 'my category'
            if '_title_' not in keys: ob['_title_'] = 'my title'
            if '_notes_' not in keys: ob['_notes_'] = 'my notes'
            if '_owner_' not in keys: ob['_owner_'] = getpass.getuser()

            if ob.type == 'MESH':
                mesh = ob.data
                mkeys = mesh.keys()
                for tag in VersionControlMesh:
                    if tag not in mkeys: mesh[tag] = True    # converted to 1

        return {'FINISHED'}

class Ogre_VC_Panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    #bl_context = "object"
    bl_label = "Ogre Version Control"
    @classmethod
    def poll(cls, context):
        if context.active_object: return True
        else: return False
    def draw(self, context):
        layout = self.layout
        ob = context.active_object

        if ob.type == 'MESH':
            mesh = ob.data
            mkeys = mesh.keys()
            box = layout.box()
            box.label(text='mesh: %s' %mesh.name)
            row = box.row()
            for tag in VersionControlMesh:
                #if tag not in mkeys: mesh[tag] = True    # converted to 1
                if tag in mkeys: v = mesh[tag]
                else: v = True
                if v: icon = 'CHECKBOX_HLT'
                else: icon = 'CHECKBOX_DEHLT'
                op = row.operator( 'ogre.toggle_prop', text=tag.replace('_',' '), icon=icon )
                op.propname = tag

        keys = ob.keys()
        box = layout.box()
        issetup = True
        for tag in VersionControl:
            if tag not in keys: issetup=False; continue
            a = tag.replace('_','')
            row = box.row()
            if tag == '_version_':
                row.label( text='version: %s'%ob[tag] )
                op = row.operator( 'ogre.update_modify_time', text='', icon='TIME' )
            else:
                v = ob[ tag ]
                if not v: row.label( text='%s: <undefined>'%a )
                else: row.label( text='%s: %s' %(a, time.asctime(time.localtime(v))) )
        if not issetup:
            op = box.operator('ogre.setup_version_control')
        else:
            box = layout.box()
        for tag in VersionControlUser:
            if tag not in keys: continue
            a = tag.replace('_','')
            row = box.row()
            row.prop( ob, '["%s"]' %tag, text=a )
            op = row.operator( 'ogre.select_by_prop_value', text='', icon='GROUP' )
            op.propname = tag
            op.propvalue = str( ob[tag] )



class Ogre_toggle_prop_op(bpy.types.Operator):
    '''operator: prop toggle helper'''  
    bl_idname = "ogre.toggle_prop"  
    bl_label = "toggle"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type
    propname = StringProperty(name="property name", description="...", maxlen=32, default="")
    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        ob = context.active_object
        if self.propname not in ob.keys(): a = ob.data
        else: a = ob
        if self.propname not in a.keys(): a[ self.propname ] = True
        a[ self.propname ] = not a[ self.propname ]
        return {'FINISHED'}

class Ogre_select_by_prop_value(bpy.types.Operator):
    '''select other objects with the same property value'''  
    bl_idname = "ogre.select_by_prop_value"  
    bl_label = "select by prop"
    bl_options = {'REGISTER', 'UNDO'}
    propname = StringProperty(name="property name", description="...", maxlen=32, default="")
    propvalue = StringProperty(name="property value", maxlen=128, default="")

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        #ob = context.active_object
        for ob in bpy.context.scene.objects:
            if self.propname in ob.keys():
                if str(ob[self.propname]) == self.propvalue: ob.select = True
        return {'FINISHED'}

class Ogre_update_mod_time(bpy.types.Operator):
    '''set modified time and bump the version number up'''  
    bl_idname = "ogre.update_modify_time"  
    bl_label = "update mod time"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        ob = context.active_object
        ob['_modified_'] = time.time()
        ob['_version_'] += 1
        return {'FINISHED'}

class Ogre_toggle_collision(bpy.types.Operator):
    '''enables collision'''  
    bl_idname = "ogre.toggle_collision"  
    bl_label = "modify collision"
    bl_options = {'REGISTER'}

    MODE = StringProperty(name="toggle mode", description="...", maxlen=32, default="disable")

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        ob = context.active_object
        game = ob.game

        colchild = None
        for child in ob.children:
            if child.name.startswith('collision'): colchild = child; break

        if self.MODE != 'disable' and not colchild:
            parent = context.active_object
            child = parent.copy()
            bpy.context.scene.objects.link( child )
            child.name = 'collision'
            child.matrix_local = mathutils.Matrix()
            child.parent = parent
            child.hide_select = True
            child.draw_type = 'WIRE'
            #child.select = False
            child.lock_location = [True]*3
            child.lock_rotation = [True]*3
            child.lock_scale = [True]*3
            colchild = child

        decmod = None
        if colchild:
            for mod in colchild.modifiers:
                if mod.type == 'DECIMATE': decmod = mod; break
            if not decmod:
                decmod = colchild.modifiers.new('LOD', type='DECIMATE')
                decmod.ratio = 0.5


        if self.MODE == 'disable':
            game.use_ghost = True
            if ob.show_bounds: ob.show_bounds = False
            if ob.show_wire: ob.show_wire = False
            if colchild and not colchild.hide: colchild.hide = True

        elif self.MODE.startswith('primitive'):
            game.use_ghost = False
            game.use_collision_bounds = True
            colchild.hide = False
            if colchild and not colchild.hide: colchild.hide = True
            btype = self.MODE.split(':')[-1]
            game.collision_bounds_type = btype
            if btype in 'BOX SPHERE CYLINDER CONE CAPSULE'.split():
                if not ob.show_bounds: ob.show_bounds = True
                if ob.draw_bounds_type != btype: ob.draw_bounds_type = btype
                if ob.show_wire: ob.show_wire = False
            elif btype == 'TRIANGLE_MESH':
                if ob.show_bounds: ob.show_bounds = False
                if not ob.show_wire: ob.show_wire = True
                ob.draw_bounds_type = 'POLYHEDRON'    #whats this?
            else: game.collision_bounds_type = 'BOX'

        elif self.MODE == 'proxy':
            decmod.show_viewport = True
            game.use_ghost = False
            game.use_collision_bounds = False

            if ob.show_bounds: ob.show_bounds = False
            if ob.show_wire: ob.show_wire = False

            if colchild.hide: colchild.hide = False
            if not colchild.select:
                colchild.hide_select = False
                colchild.select = True
                colchild.hide_select = True



        return {'FINISHED'}



############## mesh LOD physics #############
class Ogre_Physics_LOD(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    #bl_context = "data"
    bl_label = "Ogre Collision"
    @classmethod
    def poll(cls, context):
        if context.active_object: return True
        else: return False
    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        if ob.type != 'MESH': return
        game = ob.game

        if ob.name.startswith('collision'):
            box = layout.box()
            if ob.parent:
                box.label(text='object is a collision proxy for: %s' %ob.parent.name)
            else:
                box.label(text='WARNING: collision proxy missing parent')

        else:   # valid parent
            box = layout.box()
            if not game.use_ghost:  # HAS collision
                op = box.operator( 'ogre.toggle_collision', text='Disable' )
                op.MODE = 'disable'

                if not game.use_collision_bounds:
                    box = layout.box()
                    colchild = None
                    for child in ob.children:
                        if child.name.startswith('collision'): colchild = child; break
                    if colchild:
                        decmod = None
                        for mod in colchild.modifiers:
                            if mod.type == 'DECIMATE': decmod = mod; break
                        if decmod:
                            box.prop( decmod, 'ratio', 'vertex reduction ratio' )
                            box.label(text='faces: %s' %decmod.face_count )
                    else:
                        op = box.operator( 'ogre.toggle_collision', text='Enable Proxy' )
                        op.MODE = 'proxy'
                        op = box.operator( 'ogre.toggle_collision', text='Enable Primitive' )
                        op.MODE = 'primitive:%s' %game.collision_bounds_type

                elif game.use_collision_bounds:
                    box = layout.box()
                    box.prop(game, "collision_margin", text="Collision Margin", slider=True)
                    for btype in 'BOX SPHERE CYLINDER CONE CAPSULE'.split():
                        if game.collision_bounds_type == btype:
                            box.label(text='<%s>' %btype )
                        else:
                            op = box.operator( 'ogre.toggle_collision', text=btype )
                            op.MODE = 'primitive:%s' %btype


            else:   # NO collision

                op = box.operator( 'ogre.toggle_collision', text='Enable Proxy' )
                op.MODE = 'proxy'
                op = box.operator( 'ogre.toggle_collision', text='Enable Primitive' )
                op.MODE = 'primitive:%s' %game.collision_bounds_type






class Ogre_create_collision_op(bpy.types.Operator):
    '''operator: creates new collision'''  
    bl_idname = "ogre.create_collision"  
    bl_label = "create collision mesh"
    bl_options = {'REGISTER', 'UNDO'}                              # Options for this panel type

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        parent = context.active_object
        child = parent.copy()
        bpy.context.scene.objects.link( child )
        child.name = 'collision'
        child.matrix_local = mathutils.Matrix()
        child.parent = parent
        child.hide_select = True
        child.draw_type = 'WIRE'
        #child.select = False
        child.lock_location = [True]*3
        child.lock_rotation = [True]*3
        child.lock_scale = [True]*3
        return {'FINISHED'}


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


class Ogre_Physics(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    #bl_context = "physics"
    bl_label = "Ogre Physics"

    @classmethod
    def poll(cls, context):
        if context.active_object: return True
        else: return False

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        game = ob.game
        #nothing useful here?#soft = ob.game.soft_body

        box = layout.box()
        box.prop(game, "physics_type", text='Type')
        box.prop(game, "use_actor")

        box.separator()

        box.label(text="Attributes:")
        box.prop(game, "mass")
        box.prop(game, "radius")
        box.prop(game, "form_factor")


        box.prop(game, "use_anisotropic_friction")
        subsub = box.column()
        subsub.active = game.use_anisotropic_friction
        subsub.prop(game, "friction_coefficients", text="", slider=True)


        box.label(text="Velocity:")
        box.prop(game, "velocity_min", text="Minimum")
        box.prop(game, "velocity_max", text="Maximum")

        box.label(text="Damping:")
        box.prop(game, "damping", text="Translation", slider=True)
        box.prop(game, "rotation_damping", text="Rotation", slider=True)

        box.separator()

        box.prop(game, "lock_location_x", text="Lock Translation: X")
        box.prop(game, "lock_location_y", text="Lock Translation: Y")
        box.prop(game, "lock_location_z", text="Lock Translation: Z")

        box.prop(game, "lock_rotation_x", text="Lock Rotation: X")
        box.prop(game, "lock_rotation_y", text="Lock Rotation: Y")
        box.prop(game, "lock_rotation_z", text="Lock Rotation: Z")



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

##################################################################

_shader_intro_doc_ = '''
Custom Shader Support | Hijacking Blender's Shader Nodes
    You can use custom attributes and a restricted subset of shader nodes to generate custom Ogre shaders that supports all the 'pass' and 'texture' options of the OgreDotMaterial format.  This is presented to the user as a 'flat-wrapper' around the OgreDotMaterial format, so a good understanding of how shaders work is required - although once a shader is setup anyone could experiment changing its options.
'''

_shader_using_doc_ = '''
Hijacking The Shader Nodes Interface:
    In an effort to streamline the artist workflow (and keep this code clean and bugfree) a different approach is taken to determine the rendering pass order and texturing pass order.  Instead of using mixer nodes and their connections, rendering order is simply determined by height of a material or texture node relative to other nodes of the same type.  The blending options for a rendering pass are stored as custom attributes at the material or texture level, not in mixer nodes.  (Mixer nodes DO NOT map well to OgreDotMaterial blending options, so they are completely ignored)
    This sort of hijacking leads to a shader that will not render in blender as it will in Ogre, as a workaround for this problem multiple rendering branches can be used within the same node tree.  You may have multiple 'Output' nodes, blender will only use the first one, the Ogre exporter will look for a second 'Output' node and consider only nodes connect to it.  This enables you to reuse the same texture nodes with the mapping options kept intact and connecting them to another branch of nodes that connect to the blender 'Output' node.  Using this double-branching the artist can preview their work in the blender software renderer, although it may not appear excatly the same - at a minimum texture mapping and animations can be previsualized.

Example - Colored Ambient Setup:
    1. check 'use_nodes' to initialize shader nodes for the given material
    2. add an 'Extended Material'
        (A). optionally add a 'RGB' input, and plug it into the material ambient input.
        (B). optionally add a 'Geometry' input, select the first vertex color channel, and plug the vertex color output into the material ambient input.
'''

_shader_tips_doc_ = '''
Hijacked Shader Nodes Advantages:
    1. Faster reordering of passes and texture blending order.
        (by hijacking the height of a shader node to determine its rendering order)

    2. Improved workflow between the 'Shader-Programmer' and blender artist.  The experienced shader-programmer can setup node trees in blender with placeholder textures.  Later the blender artist can use blender library linking to link the shader into their scene, and update the textures.  The integrated OgreDotMaterial documentation can help the artist understand how they might modify the node tree.

    3. Users can minimize the number of materials they must manage within blender because some shader options get 'moved-up' to the shader-node-level; and by exploting the nodes this way, we are ineffect instancing a base material and extending it with extra options like the ambient color.  In the example above a single base material can be referened by two separate node-enabled-materials.  The first node-enabled-material could use a RGB input shader node for the ambient color; while the second node-enabled-material could use a Geometry node (selecting the vertexcolor output).
        [this will be improved in the future when blender supports custom properties on shader nodes]


'''


_shader_tex_doc_ = '''
Ogre Shader Doc - Textures
All 'Texture Unit' options of OgreDotMaterial are supported by 'Custom Properties' and the following material nodes:
    Add>Input>Texture
        . texture
    Add>Input>Geometry
        . vertex color    [only the first layer is supported]
        . uv layer
    Add>Vector>Mapping
        . x and y location
        . x rotation
        . x and y scaling

'''

_shader_linking_intro_doc_ = '''
Hijacked Shaders and Blender Library Linking:
    Ogre offers some very advanced and complex ways to implement shaders.  This must be carefully considered by an experienced programmer who is dealing with the high-level shading code.  One particular issue is shadows and deforming mesh requires a shader that can easily be broken by an artist who changes the wrong options, or adds options that invalidate the shader.  These issues can mostly be solved by using Blender's library linking, because linked data beomes read-only - it in effect provides a layer of control by the shader-programmer over the artist.  Done in the right way, these restrictions will not hinder the artist either from experimenting and extending the shader's usefullness.  In addition, library linking allows automatic-push of updates downstream to artists; so whenever the shader-programmer updates their shader code and updates his own master .blend with new shader options, the change is propagated to all .blends linking to it.
'''
_shader_linking_steps_doc_ = '''
Shader Linking Steps:
    1. Communication: if the shader-programmer and artists do not stay in good communication, things are likely to break.  To help make this task simpler.  The shader-programmer can put comments in the .program file that will appear as 'notes' within the artists shader interface.  Comments declared in the 'shader-program-body' are considered comments the artist will see.  Comments in nested structures like 'default_params' are hidden from the artist.

    2a. Material Library: the shader-programer first places their .program file in 'myshaders', then when enabling the addon in Blender any .program files found in myshaders will be parsed and each vertex/fragment shader is added to a menu within Blender's shader nodes interface.  Next, from the shader nodes interface the vertex/fragment shaders can be assigned to 'Sub-Materials' they create and name accordingly, note that references to a given vertex/fragment program are stored as custom-attributes' on the material.

    2b. A Sub-Material is one that does not contain any sub nodes ('use_nodes' is disabled), it however can be used as a sub-material within a shader node tree (to serve as examples and for testing), but its a good idea that these are named '_do_not_link_me_' so that artists do not get confused when linking which materials are 'node-tree-containers' and which are sub-materials that they should link to.  Default textures can also be defined, the artist will have the option later to over-ride these in their scene.  Finally the shader-programmer will save the file as their material library master .blend, and inform the artists it is ready to link in.

    3. Linking: the artist can then link in Sub-Materials from the material library master .blend published by the shader-programmer.  The nice thing with linked materials is that their settings and custom-attributes become read-only.  The addon will detect when a material is linked, and this hides many options from the users view.  The artist can then create their own shader tree and integrate the linked material as the first or any pass they choose.  Another option is to link the entire 'node-tree-container' material, but then the artist can not alter the node tree, but still this is useful in some cases.



'''

_ogre_doc_classic_textures_ = '''
Ogre texture blending is far more limited than Blender's texture slots.  While many of the blending options are the same or similar, only the blend mode "Mix" is allowed to have a variable setting.  All other texture blend modes are either on or off, for example you can not use the "Add" blend mode and set the amount to anything other than fully on (1.0).  The user also has to take into consideration the hardware multi-texturing limitations of their target platform - for example the GeForce3 can only do four texture blend operations in a single pass.  Note that Ogre will fallback to multipass rendering when the hardware won't accelerate it.

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

TextureUnitAnimOps = {    ## DEPRECATED
    'scroll_anim' : '_xspeed _yspeed'.split(),
    'rotate_anim' : ['_revs_per_second'],
    'wave_xform' : '_xform_type _wave_type _base _freq _phase _amp'.split(),
}

#    exmodes = 'one zero dest_colour src_colour one_minus_dest_colour dest_alpha src_alpha one_minus_dest_alpha one_minus_src_alpha'.split()
ogre_scene_blend_types =  [
    ('one zero', 'one zero', 'solid default'),
    ('alpha_blend', 'alpha_blend', 'basic alpha'),
    ('add', 'add', 'additive'),
    ('modulate', 'modulate', 'multiply'),
    ('colour_blend', 'colour_blend', 'blend colors'),
]
for mode in 'dest_colour src_colour one_minus_dest_colour dest_alpha src_alpha one_minus_dest_alpha one_minus_src_alpha'.split():
    ogre_scene_blend_types.append( ('one %s'%mode, 'one %s'%mode, '') )
del mode

bpy.types.Material.scene_blend = EnumProperty(
    items=ogre_scene_blend_types, 
    name='scene blend', 
    description='blending operation of material to scene', 
    default='one zero'
)

class Ogre_Material_Panel( bpy.types.Panel ):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_label = "Ogre Material"

    def draw(self, context):
        if not hasattr(context, "material"): return
        if not context.active_object: return
        if not context.active_object.active_material: return

        mat = context.material
        ob = context.object
        slot = context.material_slot
        layout = self.layout

        box = layout.box()
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

        row = box.row()
        row.prop(mat, "use_shadows")
        row.prop(mat, "use_vertex_color_paint", text="Vertex Colors")


        box = layout.box()
        row = box.row()
        row.prop(mat, "use_transparency", text="Transparent")
        if mat.use_transparency: row.prop(mat, "alpha")
        box.prop(mat, 'scene_blend')


def has_property( a, name ):
    for prop in a.items():
        n,val = prop
        if n == name: return True


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


        #box = layout.box()
        #for param in TextureUnitAnimOps[ 'scroll_anim' ]:
        #    box.prop( node.texture, '["%s"]' % param, text='' )


def guess_uv_layer( layer ):
    ## small issue: in blender layer is a string, multiple objects may have the same material assigned, 
    ## but having different named UVTex slots, most often the user will never rename these so they get
    ## named UVTex.000 etc...   assume this to always be true.
    idx = 0
    if '.' in layer:
        a = layer.split('.')[-1]
        if a.isdigit(): idx = int(a)+1
        else: print('warning: it is not allowed to give custom names to UVTexture channels ->', layer)
    return idx

class ShaderTree(object):
    '''
    Sometimes high resolution renderings may be required.  The user has the option of using multiple Output nodes, blender will only consider the first one, the second if named starting with 'ogre' will be used by the exporter.  This allows the user to have two branches in their node setup, one for blender software rendering, the other for Ogre output.  Also useful for baking procedurals, which then can be used by the ogre branch.
    '''
    @staticmethod
    def valid_node_material( mat ):        # just incase the user enabled nodes but didn't do anything, then disabled nodes
        if mat.node_tree and len(mat.node_tree.nodes):
            for node in mat.node_tree.nodes:
                if node.type == 'MATERIAL':
                    if node.material: return True

    Materials = []
    Output = None
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
        if parent_material:
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
        M += indent(3, 'texture_unit', '{' )

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

        if OPTIONS['FORCE_IMAGE_FORMAT']: postname = self._reformat( texname )        #texname.split('.')[0]+'.dds'
        if OPTIONS['TEXTURES_SUBDIR']:
            destpath = os.path.join(path,'textures')
            if not os.path.isdir( destpath ): os.mkdir( destpath )
            M += indent(4, 'texture textures/%s' %postname )    
        else: 
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
                idx = guess_uv_layer( slot.uv_layer )
                M += indent(4, 'tex_coord_set %s' %idx)

            rgba = False
            if texture.image.depth == 32: rgba = True

            btype = slot.blend_type

            if rgba and slot.use_stencil:
                texop =     'blend_current_alpha'        # 'blend_texture_alpha' shadeless
            elif btype == 'MIX':
                texop = 'blend_manual'
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
                texop = 'add_signed'        # add_smooth not very useful?
            elif btype == 'DIFFERENCE':
                texop = 'dotproduct'        # nothing closely matches blender
            else:
                texop = 'blend_diffuse_colour'

            #factor = .0
            #if slot.use_map_color_diffuse:
            factor = 1.0 - slot.diffuse_color_factor

            if texop == 'blend_manual':
                M += indent(4, 'colour_op_ex %s src_current src_texture %s' %(texop, factor) )
            else:
                M += indent(4, 'colour_op_ex %s src_current src_texture' %texop )
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


    def dotmat_pass(self):    # must be a material
        if not self.material:
            print('ERROR: material node with no submaterial block chosen')
            return ''
        mat = self.material
        color = mat.diffuse_color
        alpha = 1.0
        if mat.use_transparency: alpha = mat.alpha

        ## textures ##
        if not self.textures:        ## class style materials
            slots = get_image_textures( mat )        # returns texture_slot object
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
        if self.node:        # ogre combines passes with the same name, be careful!
            passname = '%s__%s' %(self.node.name,material_name(mat))
            passname = passname.replace(' ','_')
            M += indent(2, 'pass %s' %passname, '{' )        # be careful with pass names
        else:
            M += indent(2, 'pass', '{' )

        M += indent(3, 'cull_hardware none' )        # directx and opengl are reversed, how to deal with this? TODO

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
            M += indent(3, 'emissive 1.0 1.0 1.0 1.0' )
        else:
            M += indent(3, 'emissive %s %s %s %s' %(color.r*f, color.g*f, color.b*f, alpha) )

        M += indent( 3, 'scene_blend %s' %mat.scene_blend )
        for prop in mat.items():
            name,val = prop
            if not name.startswith('_'): M += indent( 3, '%s %s' %prop )

        ## textures ##
        if not self.textures:        ## class style materials
            slots = get_image_textures( mat )        # returns texture_slot object
            usealpha = False
            for slot in slots:
                #if slot.use_map_alpha and slot.texture.use_alpha: usealpha = True; break
                if slot.use_map_alpha: usealpha = True; break

            if usealpha:
                if mat.use_transparency: M += indent(3, 'depth_write off' ) # defined only once per pass (global attributes)

            ## write shader programs before textures
            M += self._write_shader_programs( mat )
            for slot in slots: M += self.dotmat_texture( slot.texture, slot=slot )


        elif self.node:        # shader nodes

            M += self._write_shader_programs( mat )
            for wrap in self.textures:
                M += self.dotmat_texture( wrap.node.texture, texwrapper=wrap )

        M += indent(2, '}' )    # end pass
        return M

    def _write_shader_programs( self, mat ):
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



SELECTED_MATERIAL_NODE = None
SELECTED_TEXTURE_NODE = None

## Custom Node Panel ##
class _node_panel_mixin_(object):        # bug in bpy_rna.c line: 5005 (/* rare case. can happen when registering subclasses */)
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'

    def draw(self, context):
        global SELECTED_MATERIAL_NODE, SELECTED_TEXTURE_NODE
        layout = self.layout
        topmat = context.space_data.id                        # always returns the toplevel material that contains the node_tree
        material = topmat.active_node_material        # the currently selected sub-material
        if not material: layout.label(text='please enable use_nodes'); return
        for node in context.space_data.node_tree.nodes:
            if node.type.startswith('MATERIAL') and node.material and node.material.name == material.name:
                snode = node
                break
        else: snode = None

        if self.mytype == 'shader':
            box = layout.box()
            if not material.library:        # if linked, hide
                row = box.row()
                row.menu( 'ogre_dot_mat_preview', icon='TEXT' )
                row = box.row()
                row.menu('INFO_MT_ogre_shader_pass_attributes', icon='RENDERLAYERS')
                row.menu('INFO_MT_ogre_shader_texture_attributes', icon='TEXTURE')
                row = box.row()
                if MyShaders.vertex_progs:
                    row.menu('OgreShader_vertexprogs', icon='MESH_CUBE')
                if MyShaders.fragment_progs:
                    row.menu('OgreShader_fragmentprogs', icon='MATERIAL_DATA')
            else:
                row = box.row()
                row.menu( 'ogre_dot_mat_preview', icon='TEXT' )
                row.menu('INFO_MT_ogre_shader_texture_attributes', icon='TEXTURE')
                box.label( text='linked->'+os.path.split(material.library.filepath)[-1] )

            box = layout.box()
            row = box.row()
            row.prop( topmat, 'use_shadows' )
            row.prop( topmat, 'use_transparency' )
            box.operator("ogre.new_texture_block", text="new texture", icon='ZOOMIN')

        elif self.mytype == 'notes':
            if not material or not snode:
                print('error: no active node material, enable "use_nodes" and assign a material to the material-node'); return

            node = SELECTED_MATERIAL_NODE
            if node:
                for prop in node.items():        # items is hidden function, dir(com) will not list it!        see rna_prop_ui.py
                    tag,progs = prop
                    if tag not in '_vprograms_ _fprograms_'.split(): continue
                    for name in progs:        # expects dict/idproperty
                        if MyShaders.get( name ):
                            prog = MyShaders.get( name )
                            if prog.comments:
                                box = layout.box()
                                for com in prog.comments: box.label(text=com)

        else:
            nodes = []
            if not material or not snode:
                print('error: no active node material, enable "use_nodes" and assign a material to the material-node'); return
            if self.mytype == 'material':
                nodes.append( material )
                SELECTED_MATERIAL_NODE = material

            elif self.mytype == 'texture':
                #node = material.active_texture        # this is not material nodes (classic material texture slots)
                #for socket in snode.inputs: #socket only contains: .default_value and .name        (links are stores in node_tree.links)
                for link in context.space_data.node_tree.links:
                    if link.from_node and link.to_node:        # to_node can be none durring drag
                        if link.to_node.name == snode.name and link.from_node.type == 'TEXTURE':
                            if link.from_node.texture:
                                tex = link.from_node.texture
                                SELECTED_TEXTURE_NODE = tex        # need bpy_rna way to get selected in node editor! TODO
                                nodes.append( tex )
                            else:
                                layout.label(text='<no texture block>'); return

            for node in nodes:
                layout.label(text=node.name)
                for prop in node.items():        # items is hidden function, dir(com) will not list it!        see rna_prop_ui.py
                    key,value = prop
                    if key.startswith('_'): continue
                    box = layout.box()
                    row = box.row()
                    row.label(text=key)
                    row.prop( node, '["%s"]' % key, text='' )        # so the dict exposes the props!
                    if not node.library:
                        op = row.operator("wm.properties_remove", text="", icon='ZOOMOUT')
                    #op.property = key
                    #op.data_path = 'texture'    #'material'
                    #del ob['key'] # works!
            if not nodes:
                if self.mytype == 'texture':
                    layout.label(text='no texture nodes directly connected')
                else:
                    layout.label(text='no material')

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
                m = merge_objects( subs, transform=e.matrix_world )
                obs.append( m )
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
            elif len(context.selected_objects)>1:
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
            subprocess.call(cmd)

        else:
            subprocess.call([CONFIG_OGRE_MESHY, 'C:\\tmp\\preview.mesh'])

        return {'FINISHED'}


class _ogre_new_tex_block(bpy.types.Operator):
    '''helper to create new texture block'''
    bl_idname = "ogre.new_texture_block"
    bl_label = "helper creates a new texture block"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context): return True
    def execute(self, context):
        tex = bpy.data.textures.new('Tex', type='IMAGE')
        if len(bpy.data.images): tex.image = bpy.data.images[0]        # give a default
        return {'FINISHED'}

class NODE_PT_shader_toplevel(bpy.types.Panel, _node_panel_mixin_):
    bl_label = "Ogre Shader"
    mytype = 'shader'


########## panels appear in order defined ? #############
class OgreShader_shaderprogs(bpy.types.Panel):
    bl_label = "Ogre Shader: Programs"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    def draw(self, context):
        layout = self.layout
        node = SELECTED_MATERIAL_NODE

        if node:
            for prop in node.items():        # items is hidden function, dir(com) will not list it!        see rna_prop_ui.py
                tag,progs = prop
                if tag not in '_vprograms_ _fprograms_'.split(): continue

                box = layout.box()
                for name in progs:        # expects dict/idproperty
                    row = box.row()
                    #row.label(text=name)
                    #row.prop( node, '["%s"]["%s"]' % (key,sname), text=sname )        # so the dict exposes the props!
                    #op = row.operator("ogre.add_shader_program_param", text=name, icon='SETTINGS')
                    if MyShaders.get( name ):
                        _prog = MyShaders.get( name )
                        _name = '%s  | %s' %(name, _prog.source)
                        if node.library:
                            row.label(text=_name)
                        elif _prog.type == 'vertex':
                            op = row.operator("ogre.add_shader_program_param", text=_name, icon='MESH_CUBE')
                            op.program_name = name
                        elif _prog.type == 'fragment':
                            op = row.operator("ogre.add_shader_program_param", text=_name, icon='MATERIAL_DATA')
                            op.program_name = name

                        #row.label(text=_prog.source)

                    else:        # can't find the shader
                        op = row.operator("ogre.add_shader_program_param", text=name, icon='QUESTION')
                        op.program_name = name

                    if not node.library:
                        op = row.operator("wm.properties_remove", text="", icon='ZOOMOUT')

                        col = box.column()
                        for param_name in progs[name]:
                            param = progs[name][ param_name ]
                            txt = '    %s  %s' %(param['name'], param['value-code'])
                            if 'args' in param: txt += ' ' + param['args']
                            row = col.row()
                            row.label(text=txt)        # TODO support over-ride value-code and args
                            #row.prop( node, '["%s"]["%s"]["%s"]["value-code"]' %(tag,name,param_name) )
                            #op = row.operator("wm.properties_remove", text="", icon='ZOOMOUT')


###########################
class NODE_PT_material_props(bpy.types.Panel, _node_panel_mixin_):
    bl_label = "Ogre Shader: Pass"; mytype = 'material'
class NODE_PT_texture_props(bpy.types.Panel, _node_panel_mixin_):
    bl_label = "Ogre Shader: Textures"; mytype = 'texture'
class NODE_PT_user_notes_props(bpy.types.Panel, _node_panel_mixin_):
    bl_label = "Ogre Shader: User Notes"; mytype = 'notes'


class _ogre_op_shader_program_param(bpy.types.Operator):
    '''helper to create new texture block'''
    bl_idname = "ogre.add_shader_program_param"
    bl_label = "assign program shader to material"
    bl_options = {'REGISTER'}
    program_name = StringProperty('prog-name')
    @classmethod
    def poll(cls, context): return True
    def execute(self, context):
        print( self.program_name )
        MyShaders.Selected = self.program_name
        bpy.ops.wm.call_menu( name='_ogre_shader_prog_param_menu_' )
        return {'FINISHED'}

class _ogre_shader_prog_param_menu_(bpy.types.Menu):
    bl_label = "Vertex Program Params"
    def draw(self, context):
        layout = self.layout
        pname = MyShaders.Selected
        prog = MyShaders.get( pname )
        for a in 'name file source technique entry_point profiles'.split():
            attr = getattr(prog, a)
            if attr: layout.label(text='%s=%s' %(a,attr.strip()))

        for p in prog.params_auto:
            name = p['name']
            vcode = p['value-code']
            txt = name + '|' + vcode
            if 'args' in p: txt += '  ' + p['args']
            op = layout.operator(_ogre_op_shader_program_subparam.bl_idname, text=txt, icon='ZOOMIN')
            op.program_name = prog.name
            op.param_name = name

class _ogre_op_shader_program_subparam(bpy.types.Operator):
    '''helper to...'''
    bl_idname = "ogre.add_shader_program_subparam"
    bl_label = "assign program shader subparam to material"
    bl_options = {'REGISTER'}
    program_name = StringProperty('prog-name')
    param_name = StringProperty('param-name')

    @classmethod
    def poll(cls, context): return True
    def execute(self, context):
        print( self.program_name )
        prog = MyShaders.get(self.program_name)
        param = prog.get_param( self.param_name )

        node = SELECTED_MATERIAL_NODE
        if node:
            if prog.type == 'vertex': P = node['_vprograms_']
            else: P = node['_fprograms_']
            P[ prog.name ][ self.param_name ] = param.copy()

        context.area.tag_redraw()
        return {'FINISHED'}


#############################
class _ogre_shader_progs_mixin_(object): # TODO chat with jesterking, layout.menu should return menu
    def draw(self, context):
        layout = self.layout
        if self.mytype == 'vertex':
            for prog in MyShaders.vertex_progs:
                op = layout.operator(_ogre_op_shader_programs.bl_idname, text=prog.name, icon='ZOOMIN')
                op.program_name = prog.name
        else:
            for prog in MyShaders.fragment_progs:
                op = layout.operator(_ogre_op_shader_programs.bl_idname, text=prog.name, icon='ZOOMIN')
                op.program_name = prog.name
class OgreShader_vertexprogs(bpy.types.Menu, _ogre_shader_progs_mixin_):
    bl_label = "Vertex Programs"
    mytype = 'vertex'
class OgreShader_fragmentprogs(bpy.types.Menu, _ogre_shader_progs_mixin_):
    bl_label = "Fragment Programs"
    mytype = 'fragment'

class _ogre_op_shader_programs(bpy.types.Operator):
    '''helper to create new texture block'''
    bl_idname = "ogre.add_shader_program"
    bl_label = "assign program shader to material"
    bl_options = {'REGISTER', 'UNDO'}
    program_name = StringProperty('prog-name')
    @classmethod
    def poll(cls, context): return True
    def execute(self, context):
        print( self.program_name )
        prog = MyShaders.get( self.program_name )
        mat = SELECTED_MATERIAL_NODE
        if prog.type == 'vertex':
            if '_vprograms_' not in mat: mat['_vprograms_'] = {}
            d = mat['_vprograms_']
        else:
            if '_fprograms_' not in mat: mat['_fprograms_'] = {}
            d = mat['_fprograms_']
        d[ prog.name ] = {}

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
_OGRE_SHADER_REF_ = []
_OGRE_SHADER_REF_TEX_ = []
def ogredoc( cls ):
    tag = cls.__name__.split('_ogredoc_')[-1]

    if tag.startswith('Shader_Nodes_'):
        cls.bl_label = cls.ogre_shader_op = tag.split('Shader_Nodes_')[-1]
        cls.ogre_shader_params = []
        if cls.ogre_shader_op not in 'ambient diffuse specular emissive'.split():
            for line in cls.mydoc.splitlines():
                if line.strip().startswith('@'):        # custom markup
                    cls.ogre_shader_params.append( line.strip()[1:] )
        _OGRE_SHADER_REF_.append( cls )
    elif tag.startswith('TEX_'):
        cls.bl_label = cls.ogre_shader_tex_op = tag.split('TEX_')[-1]
        cls.ogre_shader_params = []
        if cls.ogre_shader_tex_op not in 'texture tex_coord_set'.split():
            for line in cls.mydoc.splitlines():
                if line.strip().startswith('@'):        # custom markup
                    cls.ogre_shader_params.append( line.strip()[1:] )
        _OGRE_SHADER_REF_TEX_.append( cls )

    else:
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

        if hasattr(self, 'ogre_shader_params') and self.ogre_shader_params:
            for param in self.ogre_shader_params:
                if hasattr(self, 'ogre_shader_tex_op'):
                    txt = '%s    %s' %(self.ogre_shader_tex_op, param)
                    op = layout.operator(INFO_OT_ogre_set_shader_tex_param.bl_idname, text=txt, icon='ZOOMIN')
                    op.shader_tex = self.ogre_shader_tex_op        # bpy op API note: uses slots to prevent an op from having dynamic attributes
                    op.shader_tex_param = param
                else:
                    txt = '%s    %s' %(self.ogre_shader_op, param)
                    op = layout.operator(INFO_OT_ogre_set_shader_param.bl_idname, text=txt, icon='ZOOMIN')
                    op.shader_pass = self.ogre_shader_op        # bpy op API note: uses slots to prevent an op from having dynamic attributes
                    op.shader_pass_param = param



class INFO_OT_ogre_set_shader_param(bpy.types.Operator):
    '''assign ogre shader param'''
    bl_idname = "ogre.set_shader_param"
    bl_label = "Ogre Shader Param"
    bl_options = {'REGISTER', 'UNDO'}
    shader_pass = StringProperty(name="shader operation", description="", maxlen=64, default="")
    shader_pass_param = StringProperty(name="shader param", description="", maxlen=64, default="")
    @classmethod
    def poll(cls, context): return True
    def execute(self, context):
        SELECTED_MATERIAL_NODE[ self.shader_pass ] = self.shader_pass_param
        context.area.tag_redraw()
        return {'FINISHED'}

class INFO_OT_ogre_set_shader_tex_param(bpy.types.Operator):
    '''assign ogre shader texture param'''
    bl_idname = "ogre.set_shader_tex_param"
    bl_label = "Ogre Shader Texture Param"
    bl_options = {'REGISTER', 'UNDO'}
    shader_tex = StringProperty(name="shader operation", description="", maxlen=64, default="")
    shader_tex_param = StringProperty(name="shader param", description="", maxlen=64, default="")
    @classmethod
    def poll(cls, context): return True
    def execute(self, context):
        SELECTED_TEXTURE_NODE[ self.shader_tex ] = self.shader_tex_param
        context.area.tag_redraw()
        return {'FINISHED'}

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

@ogredoc
class _ogredoc_Texture_Options( INFO_MT_ogre_helper ):
    mydoc = _ogre_doc_classic_textures_

#@ogredoc
#class _ogredoc_Game_Logic_Intro( INFO_MT_ogre_helper ):
#    mydoc = _game_logic_intro_doc_

#@ogredoc
#class _ogredoc_Game_Logic_Types( INFO_MT_ogre_helper ):
#    mydoc = _ogre_logic_types_doc_


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

Current Shader Issues:
    1. You can not create a shader that ends up being more than 16 passes (Ogre limitation)
    2. Shader nodes do not support custom attributes, this limits material attribute overloading.
    3. At this time GLSL in Blender can not compile complex node trees, this will prevent
    you from seeing the output of the shader in the viewport, not seeing your textures in
    the viewport is a serious problem.  There are two workarounds:
        (a) disable 'use_nodes' and assign textures to the material in the normal manner.
            [ the shader nodes are still exported to Ogre ]
        (b) use a second branch connected to the first 'Output' and preview with software renderer.

'''


@ogredoc
class _ogredoc_Bugs( INFO_MT_ogre_helper ):
    mydoc = '''
Known Issues:
    . shape animation breaks when using modifiers that change the vertex count

'''

@ogredoc
class _ogredoc_Node_Shaders_Introduction( INFO_MT_ogre_helper ):
    mydoc = _shader_intro_doc_

@ogredoc
class _ogredoc_Node_Shaders_Doc( INFO_MT_ogre_helper ):
    mydoc = _shader_using_doc_

@ogredoc
class _ogredoc_Node_Shaders_Tips_and_Tricks( INFO_MT_ogre_helper ):
    mydoc = _shader_tips_doc_

@ogredoc
class _ogredoc_Node_Shaders_Textures( INFO_MT_ogre_helper ):
    mydoc = _shader_tex_doc_

@ogredoc
class _ogredoc_Node_Shaders_Linking_Intro( INFO_MT_ogre_helper ):
    mydoc = _shader_linking_intro_doc_
@ogredoc
class _ogredoc_Node_Shaders_Linking_Steps( INFO_MT_ogre_helper ):
    mydoc = _shader_linking_steps_doc_


############ Ogre v.17 Doc ######
@ogredoc
class _ogredoc_Shader_Nodes_ambient( INFO_MT_ogre_helper ):
    mydoc = '''
Sets the ambient colour reflectance properties of this pass. This attribute has no effect if a asm, CG, or HLSL shader program is used. With GLSL, the shader can read the OpenGL material state. 

Format: ambient (<red> <green> <blue> [<alpha>]| vertexcolour)
NB valid colour values are between 0.0 and 1.0.

Example: ambient 0.0 0.8 0.0

The base colour of a pass is determined by how much red, green and blue light is reflects at each vertex. This property determines how much ambient light (directionless global light) is reflected. It is also possible to make the ambient reflectance track the vertex colour as defined in the mesh by using the keyword vertexcolour instead of the colour values. The default is full white, meaning objects are completely globally illuminated. Reduce this if you want to see diffuse or specular light effects, or change the blend of colours to make the object have a base colour other than white. This setting has no effect if dynamic lighting is disabled using the 'lighting off' attribute, or if any texture layer has a 'colour_op replace' attribute.

Default: ambient 1.0 1.0 1.0 1.0

'''

@ogredoc
class _ogredoc_Shader_Nodes_diffuse( INFO_MT_ogre_helper ):
    mydoc = '''
Sets the diffuse colour reflectance properties of this pass. This attribute has no effect if a asm, CG, or HLSL shader program is used. With GLSL, the shader can read the OpenGL material state.

Format: diffuse (<red> <green> <blue> [<alpha>]| vertexcolour)
NB valid colour values are between 0.0 and 1.0.

Example: diffuse 1.0 0.5 0.5

The base colour of a pass is determined by how much red, green and blue light is reflects at each vertex. This property determines how much diffuse light (light from instances of the Light class in the scene) is reflected. It is also possible to make the diffuse reflectance track the vertex colour as defined in the mesh by using the keyword vertexcolour instead of the colour values. The default is full white, meaning objects reflect the maximum white light they can from Light objects. This setting has no effect if dynamic lighting is disabled using the 'lighting off' attribute, or if any texture layer has a 'colour_op replace' attribute.

Default: diffuse 1.0 1.0 1.0 1.0
'''

@ogredoc
class _ogredoc_Shader_Nodes_specular( INFO_MT_ogre_helper ):
    mydoc = '''
Sets the specular colour reflectance properties of this pass. This attribute has no effect if a asm, CG, or HLSL shader program is used. With GLSL, the shader can read the OpenGL material state.

Format: specular (<red> <green> <blue> [<alpha>]| vertexcolour) <shininess>
NB valid colour values are between 0.0 and 1.0. Shininess can be any value greater than 0.

Example: specular 1.0 1.0 1.0 12.5

The base colour of a pass is determined by how much red, green and blue light is reflects at each vertex. This property determines how much specular light (highlights from instances of the Light class in the scene) is reflected. It is also possible to make the diffuse reflectance track the vertex colour as defined in the mesh by using the keyword vertexcolour instead of the colour values. The default is to reflect no specular light. The colour of the specular highlights is determined by the colour parameters, and the size of the highlights by the separate shininess parameter.. The higher the value of the shininess parameter, the sharper the highlight ie the radius is smaller. Beware of using shininess values in the range of 0 to 1 since this causes the the specular colour to be applied to the whole surface that has the material applied to it. When the viewing angle to the surface changes, ugly flickering will also occur when shininess is in the range of 0 to 1. Shininess values between 1 and 128 work best in both DirectX and OpenGL renderers. This setting has no effect if dynamic lighting is disabled using the 'lighting off' attribute, or if any texture layer has a 'colour_op replace' attribute.

Default: specular 0.0 0.0 0.0 0.0 0.0
'''

@ogredoc
class _ogredoc_Shader_Nodes_emissive( INFO_MT_ogre_helper ):
    mydoc = '''
emissive

Sets the amount of self-illumination an object has. This attribute has no effect if a asm, CG, or HLSL shader program is used. With GLSL, the shader can read the OpenGL material state.

Format: emissive (<red> <green> <blue> [<alpha>]| vertexcolour)
NB valid colour values are between 0.0 and 1.0.

Example: emissive 1.0 0.0 0.0

If an object is self-illuminating, it does not need external sources to light it, ambient or otherwise. It's like the object has it's own personal ambient light. Unlike the name suggests, this object doesn't act as a light source for other objects in the scene (if you want it to, you have to create a light which is centered on the object). It is also possible to make the emissive colour track the vertex colour as defined in the mesh by using the keyword vertexcolour instead of the colour values. This setting has no effect if dynamic lighting is disabled using the 'lighting off' attribute, or if any texture layer has a 'colour_op replace' attribute.

Default: emissive 0.0 0.0 0.0 0.0
'''

# TODO remove this
if 0:
    @ogredoc
    class _ogredoc_Shader_Nodes_scene_blend( INFO_MT_ogre_helper ):
        mydoc = '''
    scene_blend

    Sets the kind of blending this pass has with the existing contents of the scene. Wheras the texture blending operations seen in the texture_unit entries are concerned with blending between texture layers, this blending is about combining the output of this pass as a whole with the existing contents of the rendering target. This blending therefore allows object transparency and other special effects. There are 2 formats, one using predefined blend types, the other allowing a roll-your-own approach using source and destination factors.

    Format1: scene_blend <add|modulate|alpha_blend|colour_blend>
    Example: scene_blend add

    This is the simpler form, where the most commonly used blending modes are enumerated using a single parameter. Valid <blend_type> parameters are:
        @add
    The colour of the rendering output is added to the scene. Good for explosions, flares, lights, ghosts etc. Equivalent to 'scene_blend one one'.
        @modulate
    The colour of the rendering output is multiplied with the scene contents. Generally colours and darkens the scene, good for smoked glass, semi-transparent objects etc. Equivalent to 'scene_blend dest_colour zero'.
        @colour_blend
    Colour the scene based on the brightness of the input colours, but don't darken. Equivalent to 'scene_blend src_colour one_minus_src_colour'
        @alpha_blend
    The alpha value of the rendering output is used as a mask. Equivalent to 'scene_blend src_alpha one_minus_src_alpha'

    '''

@ogredoc
class _ogredoc_Shader_Nodes_separate_scene_blend( INFO_MT_ogre_helper ):
    mydoc = '''
separate_scene_blend

This option operates in exactly the same way as scene_blend, except that it allows you to specify the operations to perform between the rendered pixel and the frame buffer separately for colour and alpha components. By nature this option is only useful when rendering to targets which have an alpha channel which you'll use for later processing, such as a render texture.

Format1: separate_scene_blend <simple_colour_blend> <simple_alpha_blend>
Example: separate_scene_blend add modulate

This example would add colour components but multiply alpha components. The blend modes available are as in scene_blend. The more advanced form is also available:

Params:
    @add  modulate
    @add  alpha_blend
    @add  color_blend

    @modulate  add
    @modulate  alpha_blend
    @modulate  color_blend

    @alpha_blend    add
    @alpha_blend    modulate
    @alpha_blend    color_blend

    @colour_blend  add
    @colour_blend  modulate
    @colour_blend  alpha_blend

Format2: separate_scene_blend <colour_src_factor> <colour_dest_factor> <alpha_src_factor> <alpha_dest_factor>
Example: separate_scene_blend one one_minus_dest_alpha one one 

Again the options available in the second format are the same as those in the second format of scene_blend.
'''

@ogredoc
class _ogredoc_Shader_Nodes_scene_blend_op( INFO_MT_ogre_helper ):
    mydoc = '''
scene_blend_op

This directive changes the operation which is applied between the two components of the scene blending equation, which by default is 'add' (sourceFactor * source + destFactor * dest). You may change this to 'add', 'subtract', 'reverse_subtract', 'min' or 'max'.

Format: scene_blend_op <add|subtract|reverse_subtract|min|max>
Default: scene_blend_op add

Params:
    @add
    @subtract
    @reverse_subtract
    @min
    @max

----------------------------------------------------
Math shader node can support: add, subtract, min and max
'''

@ogredoc
class _ogredoc_Shader_Nodes_separate_scene_blend_op( INFO_MT_ogre_helper ):
    mydoc = '''

separate_scene_blend_op

This directive is as scene_blend_op, except that you can set the operation for colour and alpha separately. 
Format: separate_scene_blend_op <colourOp> <alphaOp>
Default: separate_scene_blend_op add add

Params:
    @add  subtract
    @add  reverse_subtract
    @add  min
    @add  max

    @subtract  add
    @subtract  reverse_subtract
    @subtract  min
    @subtract  max

    @reverse_subtract  subtract
    @reverse_subtract  add
    @reverse_subtract  min
    @reverse_subtract  max

    @min  add
    @min  subtract
    @min  reverse_subtract
    @min  max

    @max  add
    @max  subtract
    @max  reverse_subtract
    @max  min

'''


@ogredoc
class _ogredoc_Shader_Nodes_depth_check( INFO_MT_ogre_helper ):
    mydoc = '''
depth_check
Params:
    @on
    @off

Sets whether or not this pass renders with depth-buffer checking on or not.

Format: depth_check <on|off>

If depth-buffer checking is on, whenever a pixel is about to be written to the frame buffer the depth buffer is checked to see if the pixel is in front of all other pixels written at that point. If not, the pixel is not written. If depth checking is off, pixels are written no matter what has been rendered before. Also see depth_func for more advanced depth check configuration.

Default: depth_check on
'''

@ogredoc
class _ogredoc_Shader_Nodes_depth_write( INFO_MT_ogre_helper ):
    mydoc = '''
depth_write
Params:
    @on
    @off

Sets whether or not this pass renders with depth-buffer writing on or not.
Format: depth_write <on|off>

If depth-buffer writing is on, whenever a pixel is written to the frame buffer the depth buffer is updated with the depth value of that new pixel, thus affecting future rendering operations if future pixels are behind this one. If depth writing is off, pixels are written without updating the depth buffer. Depth writing should normally be on but can be turned off when rendering static backgrounds or when rendering a collection of transparent objects at the end of a scene so that they overlap each other correctly.

Default: depth_write on
'''

@ogredoc
class _ogredoc_Shader_Nodes_depth_func( INFO_MT_ogre_helper ):
    mydoc = '''
depth_func

Sets the function used to compare depth values when depth checking is on.

Format: depth_func <func>

If depth checking is enabled (see depth_check) a comparison occurs between the depth value of the pixel to be written and the current contents of the buffer. This comparison is normally less_equal, i.e. the pixel is written if it is closer (or at the same distance) than the current contents. The possible functions are:
    @always_fail
        Never writes a pixel to the render target
    @always_pass
        Always writes a pixel to the render target
    @less
        Write if (new_Z < existing_Z)
    @less_equal
        Write if (new_Z <= existing_Z)
    @equal
        Write if (new_Z == existing_Z)
    @not_equal
        Write if (new_Z != existing_Z)
    @greater_equal
        Write if (new_Z >= existing_Z)
    @greater
        Write if (new_Z >existing_Z)

Default: depth_func less_equal
'''

@ogredoc
class _ogredoc_Shader_Nodes_depth_bias( INFO_MT_ogre_helper ):
    mydoc = '''
depth_bias
Params:
    @1
    @2
    @3
    @4

Sets the bias applied to the depth value of this pass. Can be used to make coplanar polygons appear on top of others e.g. for decals. 

Format: depth_bias <constant_bias> [<slopescale_bias>]

The final depth bias value is constant_bias * minObservableDepth + maxSlope * slopescale_bias. Slope scale biasing is relative to the angle of the polygon to the camera, which makes for a more appropriate bias value, but this is ignored on some older hardware. Constant biasing is expressed as a factor of the minimum depth value, so a value of 1 will nudge the depth by one 'notch' if you will. Also see iteration_depth_bias
'''

@ogredoc
class _ogredoc_Shader_Nodes_iteration_depth_bias( INFO_MT_ogre_helper ):
    mydoc = '''
iteration_depth_bias
Params:
    @1
    @2
    @3
    @4

Sets an additional bias derived from the number of times a given pass has been iterated. Operates just like depth_bias except that it applies an additional bias factor to the base depth_bias value, multiplying the provided value by the number of times this pass has been iterated before, through one of the iteration variants. So the first time the pass will get the depth_bias value, the second time it will get depth_bias + iteration_depth_bias, the third time it will get depth_bias + iteration_depth_bias * 2, and so on. The default is zero. 

Format: iteration_depth_bias <bias_per_iteration>
'''

@ogredoc
class _ogredoc_Shader_Nodes_alpha_rejection( INFO_MT_ogre_helper ):
    mydoc = '''
alpha_rejection
Params:
    @always_pass
    @greater_equal 0
    @greater_equal 16
    @greater_equal 32
    @greater_equal 64

Sets the way the pass will have use alpha to totally reject pixels from the pipeline.

Format: alpha_rejection <function> <value>

Example: alpha_rejection greater_equal 128


The function parameter can be any of the options listed in the material depth_function attribute. The value parameter can theoretically be any value between 0 and 255, but is best limited to 0 or 128 for hardware compatibility.

Default: alpha_rejection always_pass
'''

@ogredoc
class _ogredoc_Shader_Nodes_alpha_to_coverage( INFO_MT_ogre_helper ):
    mydoc = '''
alpha_to_coverage
Params:
    @on
    @off

Sets whether this pass will use 'alpha to coverage', a way to multisample alpha texture edges so they blend more seamlessly with the background. This facility is typically only available on cards from around 2006 onwards, but it is safe to enable it anyway - Ogre will just ignore it if the hardware does not support it. The common use for alpha to coverage is foliage rendering and chain-link fence style textures. 

Format: alpha_to_coverage <on|off>
Default: alpha_to_coverage off
'''

@ogredoc
class _ogredoc_Shader_Nodes_light_scissor( INFO_MT_ogre_helper ):
    mydoc = '''
light_scissor
Params:
    @on
    @off

Sets whether when rendering this pass, rendering will be limited to a screen-space scissor rectangle representing the coverage of the light(s) being used in this pass, derived from their attenuation ranges.

Format: light_scissor <on|off>
Default: light_scissor off

This option is usually only useful if this pass is an additive lighting pass, and is at least the second one in the technique. Ie areas which are not affected by the current light(s) will never need to be rendered. If there is more than one light being passed to the pass, then the scissor is defined to be the rectangle which covers all lights in screen-space. Directional lights are ignored since they are infinite.

This option does not need to be specified if you are using a standard additive shadow mode, i.e. SHADOWTYPE_STENCIL_ADDITIVE or SHADOWTYPE_TEXTURE_ADDITIVE, since it is the default behaviour to use a scissor for each additive shadow pass. However, if you're not using shadows, or you're using Integrated Texture Shadows where passes are specified in a custom manner, then this could be of use to you.
'''

@ogredoc
class _ogredoc_Shader_Nodes_light_clip_planes( INFO_MT_ogre_helper ):
    mydoc = '''
light_clip_planes
Params:
    @on
    @off
Sets whether when rendering this pass, triangle setup will be limited to clipping volume covered by the light. Directional lights are ignored, point lights clip to a cube the size of the attenuation range or the light, and spotlights clip to a pyramid bounding the spotlight angle and attenuation range.

Format: light_clip_planes <on|off>
Default: light_clip_planes off

This option will only function if there is a single non-directional light being used in this pass. If there is more than one light, or only directional lights, then no clipping will occur. If there are no lights at all then the objects won't be rendered at all.

When using a standard additive shadow mode, ie SHADOWTYPE_STENCIL_ADDITIVE or SHADOWTYPE_TEXTURE_ADDITIVE, you have the option of enabling clipping for all light passes by calling SceneManager::setShadowUseLightClipPlanes regardless of this pass setting, since rendering is done lightwise anyway. This is off by default since using clip planes is not always faster - it depends on how much of the scene the light volumes cover. Generally the smaller your lights are the more chance you'll see a benefit rather than a penalty from clipping. If you're not using shadows, or you're using Integrated Texture Shadows where passes are specified in a custom manner, then specify the option per-pass using this attribute.

A specific note about OpenGL: user clip planes are completely ignored when you use an ARB vertex program. This means light clip planes won't help much if you use ARB vertex programs on GL, although OGRE will perform some optimisation of its own, in that if it sees that the clip volume is completely off-screen, it won't perform a render at all. When using GLSL, user clipping can be used but you have to use glClipVertex in your shader, see the GLSL documentation for more information. In Direct3D user clip planes are always respected.
'''

@ogredoc
class _ogredoc_Shader_Nodes_illumination_stage( INFO_MT_ogre_helper ):
    mydoc = '''
illumination_stage
Params:
    @ambient
    @per_light
    @decal

When using an additive lighting mode (SHADOWTYPE_STENCIL_ADDITIVE or SHADOWTYPE_TEXTURE_ADDITIVE), the scene is rendered in 3 discrete stages, ambient (or pre-lighting), per-light (once per light, with shadowing) and decal (or post-lighting). Usually OGRE figures out how to categorise your passes automatically, but there are some effects you cannot achieve without manually controlling the illumination. For example specular effects are muted by the typical sequence because all textures are saved until the 'decal' stage which mutes the specular effect. Instead, you could do texturing within the per-light stage if it's possible for your material and thus add the specular on after the decal texturing, and have no post-light rendering. 

If you assign an illumination stage to a pass you have to assign it to all passes in the technique otherwise it will be ignored. Also note that whilst you can have more than one pass in each group, they cannot alternate, ie all ambient passes will be before all per-light passes, which will also be before all decal passes. Within their categories the passes will retain their ordering though. Format: illumination_stage <ambient|per_light|decal>

Default: none (autodetect)
'''


@ogredoc
class _ogredoc_Shader_Nodes_normalise_normals( INFO_MT_ogre_helper ):
    mydoc = '''
normalise_normals
Params:
    @on
    @off

Sets whether or not this pass renders with all vertex normals being automatically re-normalised.
Format: normalise_normals <on|off>

Scaling objects causes normals to also change magnitude, which can throw off your lighting calculations. By default, the SceneManager detects this and will automatically re-normalise normals for any scaled object, but this has a cost. If you'd prefer to control this manually, call SceneManager::setNormaliseNormalsOnScale(false) and then use this option on materials which are sensitive to normals being resized. 

Default: normalise_normals off
'''

@ogredoc
class _ogredoc_Shader_Nodes_transparent_sorting( INFO_MT_ogre_helper ):
    mydoc = '''
transparent_sorting
Params:
    @on
    @off
    @force

Sets if transparent textures should be sorted by depth or not.

Format: transparent_sorting <on|off|force>

By default all transparent materials are sorted such that renderables furthest away from the camera are rendered first. This is usually the desired behaviour but in certain cases this depth sorting may be unnecessary and undesirable. If for example it is necessary to ensure the rendering order does not change from one frame to the next. In this case you could set the value to 'off' to prevent sorting.

You can also use the keyword 'force' to force transparent sorting on, regardless of other circumstances. Usually sorting is only used when the pass is also transparent, and has a depth write or read which indicates it cannot reliably render without sorting. By using 'force', you tell OGRE to sort this pass no matter what other circumstances are present.

Default: transparent_sorting on
'''

@ogredoc
class _ogredoc_Shader_Nodes_cull_hardware( INFO_MT_ogre_helper ):
    mydoc = '''
cull_hardware
Params:
    @clockwise
    @anticlockwise
    @none

Sets the hardware culling mode for this pass.

Format: cull_hardware <clockwise|anticlockwise|none>

A typical way for the hardware rendering engine to cull triangles is based on the 'vertex winding' of triangles. Vertex winding refers to the direction in which the vertices are passed or indexed to in the rendering operation as viewed from the camera, and will wither be clockwise or anticlockwise (that's 'counterclockwise' for you Americans out there ;). If the option 'cull_hardware clockwise' is set, all triangles whose vertices are viewed in clockwise order from the camera will be culled by the hardware. 'anticlockwise' is the reverse (obviously), and 'none' turns off hardware culling so all triagles are rendered (useful for creating 2-sided passes).

Default: cull_hardware clockwise
NB this is the same as OpenGL's default but the opposite of Direct3D's default (because Ogre uses a right-handed coordinate system like OpenGL).
'''

@ogredoc
class _ogredoc_Shader_Nodes_cull_software( INFO_MT_ogre_helper ):
    mydoc = '''
cull_software
Params:
    @back
    @front
    @none

Sets the software culling mode for this pass.

Format: cull_software <back|front|none>

In some situations the engine will also cull geometry in software before sending it to the hardware renderer. This setting only takes effect on SceneManager's that use it (since it is best used on large groups of planar world geometry rather than on movable geometry since this would be expensive), but if used can cull geometry before it is sent to the hardware. In this case the culling is based on whether the 'back' or 'front' of the triangle is facing the camera - this definition is based on the face normal (a vector which sticks out of the front side of the polygon perpendicular to the face). Since Ogre expects face normals to be on anticlockwise side of the face, 'cull_software back' is the software equivalent of 'cull_hardware clockwise' setting, which is why they are both the default. The naming is different to reflect the way the culling is done though, since most of the time face normals are pre-calculated and they don't have to be the way Ogre expects - you could set 'cull_hardware none' and completely cull in software based on your own face normals, if you have the right SceneManager which uses them.

Default: cull_software back

'''

@ogredoc
class _ogredoc_Shader_Nodes_lighting( INFO_MT_ogre_helper ):
    mydoc = '''
lighting
Params:
    @on
    @off

Sets whether or not dynamic lighting is turned on for this pass or not. If lighting is turned off, all objects rendered using the pass will be fully lit. This attribute has no effect if a vertex program is used.

Format: lighting <on|off>

Turning dynamic lighting off makes any ambient, diffuse, specular, emissive and shading properties for this pass redundant. When lighting is turned on, objects are lit according to their vertex normals for diffuse and specular light, and globally for ambient and emissive.

Default: lighting on
'''

@ogredoc
class _ogredoc_Shader_Nodes_shading( INFO_MT_ogre_helper ):
    mydoc = '''
shading
Params:
    @flat
    @gouraud
    @phong

Sets the kind of shading which should be used for representing dynamic lighting for this pass.

Format: shading <flat|gouraud|phong>

When dynamic lighting is turned on, the effect is to generate colour values at each vertex. Whether these values are interpolated across the face (and how) depends on this setting.

flat
    No interpolation takes place. Each face is shaded with a single colour determined from the first vertex in the face.
gouraud
    Colour at each vertex is linearly interpolated across the face.
phong
    Vertex normals are interpolated across the face, and these are used to determine colour at each pixel. Gives a more natural lighting effect but is more expensive and works better at high levels of tessellation. Not supported on all hardware.

Default: shading gouraud
'''

@ogredoc
class _ogredoc_Shader_Nodes_polygon_mode( INFO_MT_ogre_helper ):
    mydoc = '''
polygon_mode
Params:
    @solid
    @wireframe
    @points

Sets how polygons should be rasterised, i.e. whether they should be filled in, or just drawn as lines or points.

Format: polygon_mode <solid|wireframe|points>

solid
The normal situation - polygons are filled in.
wireframe
Polygons are drawn in outline only.
points
Only the points of each polygon are rendered.
Default: polygon_mode solid
'''

@ogredoc
class _ogredoc_Shader_Nodes_polygon_mode_overrideable( INFO_MT_ogre_helper ):
    mydoc = '''
polygon_mode_overrideable
Params:
    @true
    @false

Sets whether or not the polygon_mode set on this pass can be downgraded by the camera, if the camera itself is set to a lower polygon mode. If set to false, this pass will always be rendered at its own chosen polygon mode no matter what the camera says. The default is true.

Format: polygon_mode_overrideable <true|false>
'''


@ogredoc
class _ogredoc_Shader_Nodes_fog_override( INFO_MT_ogre_helper ):
    mydoc = '''
fog_override
Params:
    @true
    @false
    @true exp 1 1 1 0.002 100 10000

Tells the pass whether it should override the scene fog settings, and enforce it's own. Very useful for things that you don't want to be affected by fog when the rest of the scene is fogged, or vice versa. Note that this only affects fixed-function fog - the original scene fog parameters are still sent to shaders which use the fog_params parameter binding (this allows you to turn off fixed function fog and calculate it in the shader instead; if you want to disable shader fog you can do that through shader parameters anyway). 

Format: fog_override <override?> [<type> <colour> <density> <start> <end>]

Default: fog_override false

If you specify 'true' for the first parameter and you supply the rest of the parameters, you are telling the pass to use these fog settings in preference to the scene settings, whatever they might be. If you specify 'true' but provide no further parameters, you are telling this pass to never use fogging no matter what the scene says. Here is an explanation of the parameters:
type
    none = No fog, equivalent of just using 'fog_override true'
    linear = Linear fog from the <start> and <end> distances
    exp = Fog increases exponentially from the camera (fog = 1/e^(distance * density)), use <density> param to control it
    exp2 = Fog increases at the square of FOG_EXP, i.e. even quicker (fog = 1/e^(distance * density)^2), use <density> param to control it
colour
    Sequence of 3 floating point values from 0 to 1 indicating the red, green and blue intensities
density
    The density parameter used in the 'exp' or 'exp2' fog types. Not used in linear mode but param must still be there as a placeholder 
start
    The start distance from the camera of linear fog. Must still be present in other modes, even though it is not used.
end
    The end distance from the camera of linear fog. Must still be present in other modes, even though it is not used.

Example: fog_override true exp 1 1 1 0.002 100 10000
'''

@ogredoc
class _ogredoc_Shader_Nodes_colour_write( INFO_MT_ogre_helper ):
    mydoc = '''
colour_write
Params:
    @on
    @off

Sets whether or not this pass renders with colour writing on or not.
Format: colour_write <on|off>

If colour writing is off no visible pixels are written to the screen during this pass. You might think this is useless, but if you render with colour writing off, and with very minimal other settings, you can use this pass to initialise the depth buffer before subsequently rendering other passes which fill in the colour data. This can give you significant performance boosts on some newer cards, especially when using complex fragment programs, because if the depth check fails then the fragment program is never run. 

Default: colour_write on
'''

@ogredoc
class _ogredoc_Shader_Nodes_start_light( INFO_MT_ogre_helper ):
    mydoc = '''
start_light
Params:
    @0
    @1
    @2
    @3
    @4
    @5
    @6

Sets the first light which will be considered for use with this pass.

Format: start_light <number>

You can use this attribute to offset the starting point of the lights for this pass. In other words, if you set start_light to 2 then the first light to be processed in that pass will be the third actual light in the applicable list. You could use this option to use different passes to process the first couple of lights versus the second couple of lights for example, or use it in conjunction with the iteration option to start the iteration from a given point in the list (e.g. doing the first 2 lights in the first pass, and then iterating every 2 lights from then on perhaps). 

Default: start_light 0
'''

@ogredoc
class _ogredoc_Shader_Nodes_max_lights( INFO_MT_ogre_helper ):
    mydoc = '''
max_lights
Params:
    @1
    @2
    @3
    @4
    @5
    @6

Sets the maximum number of lights which will be considered for use with this pass.

Format: max_lights <number>

The maximum number of lights which can be used when rendering fixed-function materials is set by the rendering system, and is typically set at 8. When you are using the programmable pipeline (See section 3.1.9 Using Vertex/Geometry/Fragment Programs in a Pass) this limit is dependent on the program you are running, or, if you use 'iteration once_per_light' or a variant (See section iteration), it effectively only bounded by the number of passes you are willing to use. If you are not using pass iteration, the light limit applies once for this pass. If you are using pass iteration, the light limit applies across all iterations of this pass - for example if you have 12 lights in range with an 'iteration once_per_light' setup but your max_lights is set to 4 for that pass, the pass will only iterate 4 times. 

Default: max_lights 8
'''

@ogredoc
class _ogredoc_Shader_Nodes_iteration( INFO_MT_ogre_helper ):
    mydoc = '''
iteration
Params:
    @once
    @once_per_light
    @1 once
    @1 once_per_light
    @2 once
    @2 once_per_light

Sets whether or not this pass is iterated, i.e. issued more than once.

Format 1: iteration <once | once_per_light> [lightType]

Format 2: iteration <number> [<per_light> [lightType]]

Format 3: iteration <number> [<per_n_lights> <num_lights> [lightType]]

Examples:
    iteration once
        The pass is only executed once which is the default behaviour.
    iteration once_per_light point
        The pass is executed once for each point light.
    iteration 5
        The render state for the pass will be setup and then the draw call will execute 5 times.
    iteration 5 per_light point
        The render state for the pass will be setup and then the draw call will execute 5 times. This will be done for each point light.
    iteration 1 per_n_lights 2 point
        The render state for the pass will be setup and the draw call executed once for every 2 lights.

By default, passes are only issued once. However, if you use the programmable pipeline, or you wish to exceed the normal limits on the number of lights which are supported, you might want to use the once_per_light option. In this case, only light index 0 is ever used, and the pass is issued multiple times, each time with a different light in light index 0. Clearly this will make the pass more expensive, but it may be the only way to achieve certain effects such as per-pixel lighting effects which take into account 1..n lights.

Using a number instead of "once" instructs the pass to iterate more than once after the render state is setup. The render state is not changed after the initial setup so repeated draw calls are very fast and ideal for passes using programmable shaders that must iterate more than once with the same render state i.e. shaders that do fur, motion blur, special filtering.

If you use once_per_light, you should also add an ambient pass to the technique before this pass, otherwise when no lights are in range of this object it will not get rendered at all; this is important even when you have no ambient light in the scene, because you would still want the objects silhouette to appear.

The lightType parameter to the attribute only applies if you use once_per_light, per_light, or per_n_lights and restricts the pass to being run for lights of a single type (either 'point', 'directional' or 'spot'). In the example, the pass will be run once per point light. This can be useful because when you're writing a vertex / fragment program it is a lot easier if you can assume the kind of lights you'll be dealing with. However at least point and directional lights can be dealt with in one way. 

Default: iteration once

'''

@ogredoc
class _ogredoc_Shader_Nodes_point_size( INFO_MT_ogre_helper ):
    mydoc = '''
point_size
Params:
    @4
    @16
    @32

This setting allows you to change the size of points when rendering a point list, or a list of point sprites. The interpretation of this command depends on the point_size_attenuation option - if it is off (the default), the point size is in screen pixels, if it is on, it expressed as normalised screen coordinates (1.0 is the height of the screen) when the point is at the origin. 

NOTE: Some drivers have an upper limit on the size of points they support - this can even vary between APIs on the same card! Don't rely on point sizes that cause the points to get very large on screen, since they may get clamped on some cards. Upper sizes can range from 64 to 256 pixels.

Format: point_size <size>

Default: point_size 1.0
'''

@ogredoc
class _ogredoc_Shader_Nodes_point_sprites( INFO_MT_ogre_helper ):
    mydoc = '''
point_sprites
Params:
    @on
    @off

This setting specifies whether or not hardware point sprite rendering is enabled for this pass. Enabling it means that a point list is rendered as a list of quads rather than a list of dots. It is very useful to use this option if you're using a BillboardSet and only need to use point oriented billboards which are all of the same size. You can also use it for any other point list render. 

Format: point_sprites <on|off>

Default: point_sprites off
'''

@ogredoc
class _ogredoc_Shader_Nodes_point_size_attenuation( INFO_MT_ogre_helper ):
    mydoc = '''
point_size_attenuation
Params:
    @on
    @off
    @on constant
    @on linear
    @on quadratic

Defines whether point size is attenuated with view space distance, and in what fashion. This option is especially useful when you're using point sprites (See section point_sprites) since it defines how they reduce in size as they get further away from the camera. You can also disable this option to make point sprites a constant screen size (like points), or enable it for points so they change size with distance.

You only have to provide the final 3 parameters if you turn attenuation on. The formula for attenuation is that the size of the point is multiplied by 1 / (constant + linear * dist + quadratic * d^2); therefore turning it off is equivalent to (constant = 1, linear = 0, quadratic = 0) and standard perspective attenuation is (constant = 0, linear = 1, quadratic = 0). The latter is assumed if you leave out the final 3 parameters when you specify 'on'.

Note that the resulting attenuated size is clamped to the minimum and maximum point size, see the next section.

Format: point_size_attenuation <on|off> [constant linear quadratic] Default: point_size_attenuation off
'''

@ogredoc
class _ogredoc_Shader_Nodes_point_size_min( INFO_MT_ogre_helper ):
    mydoc = '''
point_size_min
Params:
    @1
    @4
    @8

Sets the minimum point size after attenuation (point_size_attenuation). For details on the size metrics, See section point_size.

Format: point_size_min <size> Default: point_size_min 0
'''

@ogredoc
class _ogredoc_Shader_Nodes_point_size_max( INFO_MT_ogre_helper ):
    mydoc = '''
point_size_max
Params:
    @32
    @64
    @128

Sets the maximum point size after attenuation (point_size_attenuation). For details on the size metrics, See section point_size. A value of 0 means the maximum is set to the same as the max size reported by the current card. 

Format: point_size_max <size> Default: point_size_max 0
'''

## Ogre 1.7 doc - 3.1.3 Texture Units ##
@ogredoc
class _ogredoc_TEX_texture_alias( INFO_MT_ogre_helper ):
    mydoc = '''
texture_alias
Params:
    @myname
Sets the alias name for this texture unit.
Format: texture_alias <name>
Example: texture_alias NormalMap
Setting the texture alias name is useful if this material is to be inherited by other other materials and only the textures will be changed in the new material.(See section 3.1.12 Texture Aliases)

Default: If a texture_unit has a name then the texture_alias defaults to the texture_unit name.
'''

@ogredoc
class _ogredoc_TEX_texture( INFO_MT_ogre_helper ):
    mydoc = '''
texture

Sets the name of the static texture image this layer will use.

Format: texture <texturename> [<type>] [unlimited | numMipMaps] [alpha] [<PixelFormat>] [gamma]

Example: texture funkywall.jpg

This setting is mutually exclusive with the anim_texture attribute. Note that the texture file cannot include spaces. Those of you Windows users who like spaces in filenames, please get over it and use underscores instead.

The 'type' parameter allows you to specify a the type of texture to create - the default is '2d', but you can override this; here's the full list:
1d
    A 1-dimensional texture; that is, a texture which is only 1 pixel high. These kinds of textures can be useful when you need to encode a function in a texture and use it as a simple lookup, perhaps in a fragment program. It is important that you use this setting when you use a fragment program which uses 1-dimensional texture coordinates, since GL requires you to use a texture type that matches (D3D will let you get away with it, but you ought to plan for cross-compatibility). Your texture widths should still be a power of 2 for best compatibility and performance.
2d
    The default type which is assumed if you omit it, your texture has a width and a height, both of which should preferably be powers of 2, and if you can, make them square because this will look best on the most hardware. These can be addressed with 2D texture coordinates.
3d
    A 3 dimensional texture i.e. volume texture. Your texture has a width, a height, both of which should be powers of 2, and has depth. These can be addressed with 3d texture coordinates i.e. through a pixel shader.
cubic
    This texture is made up of 6 2D textures which are pasted around the inside of a cube. Can be addressed with 3D texture coordinates and are useful for cubic reflection maps and normal maps.
The 'numMipMaps' option allows you to specify the number of mipmaps to generate for this texture. The default is 'unlimited' which means mips down to 1x1 size are generated. You can specify a fixed number (even 0) if you like instead. Note that if you use the same texture in many material scripts, the number of mipmaps generated will conform to the number specified in the first texture_unit used to load the texture - so be consistent with your usage.

The 'alpha' option allows you to specify that a single channel (luminance) texture should be loaded as alpha, rather than the default which is to load it into the red channel. This can be helpful if you want to use alpha-only textures in the fixed function pipeline. Default: none
'''

@ogredoc
class _ogredoc_TEX_anim_texture( INFO_MT_ogre_helper ):
    mydoc = '''
anim_texture

Sets the images to be used in an animated texture layer. In this case an animated texture layer means one which has multiple frames, each of which is a separate image file. There are 2 formats, one for implicitly determined image names, one for explicitly named images.

Format1 (short): anim_texture <base_name> <num_frames> <duration>
Example: anim_texture flame.jpg 5 2.5

This sets up an animated texture layer made up of 5 frames named flame_0.jpg, flame_1.jpg, flame_2.jpg etc, with an animation length of 2.5 seconds (2fps). If duration is set to 0, then no automatic transition takes place and frames must be changed manually in code.

Format2 (long): anim_texture <frame1> <frame2> ... <duration>
Example: anim_texture flamestart.jpg flamemore.png flameagain.jpg moreflame.jpg lastflame.tga 2.5

This sets up the same duration animation but from 5 separately named image files. The first format is more concise, but the second is provided if you cannot make your images conform to the naming standard required for it. 

Default: none
'''

@ogredoc
class _ogredoc_TEX_cubic_texture( INFO_MT_ogre_helper ):
    mydoc = '''
cubic_texture
    @mybasename separateUV
    @mybasename combinedUVW
    @front.jpg front.jpg back.jpg left.jpg right.jpg up.jpg down.jpg separateUV

Sets the images used in a cubic texture, i.e. one made up of 6 individual images making up the faces of a cube. These kinds of textures are used for reflection maps (if hardware supports cubic reflection maps) or skyboxes. There are 2 formats, a brief format expecting image names of a particular format and a more flexible but longer format for arbitrarily named textures.

Format1 (short): cubic_texture <base_name> <combinedUVW|separateUV>

The base_name in this format is something like 'skybox.jpg', and the system will expect you to provide skybox_fr.jpg, skybox_bk.jpg, skybox_up.jpg, skybox_dn.jpg, skybox_lf.jpg, and skybox_rt.jpg for the individual faces.

Format2 (long): cubic_texture <front> <back> <left> <right> <up> <down> separateUV

In this case each face is specified explicitly, incase you don't want to conform to the image naming standards above. You can only use this for the separateUV version since the combinedUVW version requires a single texture name to be assigned to the combined 3D texture (see below).

In both cases the final parameter means the following:
combinedUVW
The 6 textures are combined into a single 'cubic' texture map which is then addressed using 3D texture coordinates with U, V and W components. Necessary for reflection maps since you never know which face of the box you are going to need. Note that not all cards support cubic environment mapping.
separateUV
The 6 textures are kept separate but are all referenced by this single texture layer. One texture at a time is active (they are actually stored as 6 frames), and they are addressed using standard 2D UV coordinates. This type is good for skyboxes since only one face is rendered at one time and this has more guaranteed hardware support on older cards.

Default: none
'''

@ogredoc
class _ogredoc_TEX_binding_type( INFO_MT_ogre_helper ):
    mydoc = '''
binding_type
Params:
    @vertex
    @fragment
Tells this texture unit to bind to either the fragment processing unit or the vertex processing unit (for 3.1.10 Vertex Texture Fetch). 

Format: binding_type <vertex|fragment> Default: binding_type fragment
'''

@ogredoc
class _ogredoc_TEX_content_type( INFO_MT_ogre_helper ):
    mydoc = '''
content_type
    @compositor DepthCompositor OutputTexture

Tells this texture unit where it should get its content from. The default is to get texture content from a named texture, as defined with the texture, cubic_texture, anim_texture attributes. However you can also pull texture information from other automated sources. The options are:
@named
    The default option, this derives texture content from a texture name, loaded by ordinary means from a file or having been manually created with a given name.
@shadow
    This option allows you to pull in a shadow texture, and is only valid when you use texture shadows and one of the 'custom sequence' shadowing types (See section 7. Shadows). The shadow texture in question will be from the 'n'th closest light that casts shadows, unless you use light-based pass iteration or the light_start option which may start the light index higher. When you use this option in multiple texture units within the same pass, each one references the next shadow texture. The shadow texture index is reset in the next pass, in case you want to take into account the same shadow textures again in another pass (e.g. a separate specular / gloss pass). By using this option, the correct light frustum projection is set up for you for use in fixed-function, if you use shaders just reference the texture_viewproj_matrix auto parameter in your shader.
@compositor
    This option allows you to reference a texture from a compositor, and is only valid when the pass is rendered within a compositor sequence. This can be either in a render_scene directive inside a compositor script, or in a general pass in a viewport that has a compositor attached. Note that this is a reference only, meaning that it does not change the render order. You must make sure that the order is reasonable for what you are trying to achieve (for example, texture pooling might cause the referenced texture to be overwritten by something else by the time it is referenced). 

The extra parameters for the content_type are only required for this type: 
The first is the name of the compositor being referenced. (Required) 
The second is the name of the texture to reference in the compositor. (Required) 

The third is the index of the texture to take, in case of an MRT. (Optional)
Format: content_type <named|shadow|compositor> [<Referenced Compositor Name>] [<Referenced Texture Name>] [<Referenced MRT Index>] 

Default: content_type named 

Example: content_type compositor DepthCompositor OutputTexture 
'''

@ogredoc
class _ogredoc_TEX_tex_coord_set( INFO_MT_ogre_helper ):
    mydoc = '''
tex_coord_set

Sets which texture coordinate set is to be used for this texture layer. A mesh can define multiple sets of texture coordinates, this sets which one this material uses.

Format: tex_coord_set <set_num>
Example: tex_coord_set 2
Default: tex_coord_set 0
'''

@ogredoc
class _ogredoc_TEX_tex_address_mode( INFO_MT_ogre_helper ):
    mydoc = '''
tex_address_mode

Defines what happens when texture coordinates exceed 1.0 for this texture layer.You can use the simple format to specify the addressing mode for all 3 potential texture coordinates at once, or you can use the 2/3 parameter extended format to specify a different mode per texture coordinate. 

Simple Format: tex_address_mode <uvw_mode> 
Extended Format: tex_address_mode <u_mode> <v_mode> [<w_mode>]

@wrap
    Any value beyond 1.0 wraps back to 0.0. Texture is repeated.
@clamp
    Values beyond 1.0 are clamped to 1.0. Texture 'streaks' beyond 1.0 since last line of pixels is used across the rest of the address space. Useful for textures which need exact coverage from 0.0 to 1.0 without the 'fuzzy edge' wrap gives when combined with filtering.
@mirror
    Texture flips every boundary, meaning texture is mirrored every 1.0 u or v
@border
    Values outside the range [0.0, 1.0] are set to the border colour, you might also set the tex_border_colour attribute too.

Default: tex_address_mode wrap
'''

@ogredoc
class _ogredoc_TEX_tex_border_colour( INFO_MT_ogre_helper ):
    mydoc = '''
tex_border_colour
    @0.0 0.5 0.0 0.25
Sets the border colour of border texture address mode (see tex_address_mode). 
Format: tex_border_colour <red> <green> <blue> [<alpha>]
NB valid colour values are between 0.0 and 1.0.
Example: tex_border_colour 0.0 1.0 0.3
Default: tex_border_colour 0.0 0.0 0.0 1.0
'''

@ogredoc
class _ogredoc_TEX_filtering( INFO_MT_ogre_helper ):
    mydoc = '''
filtering

Sets the type of texture filtering used when magnifying or minifying a texture. There are 2 formats to this attribute, the simple format where you simply specify the name of a predefined set of filtering options, and the complex format, where you individually set the minification, magnification, and mip filters yourself.

Simple Format
Format: filtering <none|bilinear|trilinear|anisotropic>
Default: filtering bilinear

With this format, you only need to provide a single parameter which is one of the following:
@none
    No filtering or mipmapping is used. This is equivalent to the complex format 'filtering point point none'.
@bilinear
    2x2 box filtering is performed when magnifying or reducing a texture, and a mipmap is picked from the list but no filtering is done between the levels of the mipmaps. This is equivalent to the complex format 'filtering linear linear point'.

@trilinear
    2x2 box filtering is performed when magnifying and reducing a texture, and the closest 2 mipmaps are filtered together. This is equivalent to the complex format 'filtering linear linear linear'.
@anisotropic
    This is the same as 'trilinear', except the filtering algorithm takes account of the slope of the triangle in relation to the camera rather than simply doing a 2x2 pixel filter in all cases. This makes triangles at acute angles look less fuzzy. Equivalent to the complex format 'filtering anisotropic anisotropic linear'. Note that in order for this to make any difference, you must also set the max_anisotropy attribute too.
'''

@ogredoc
class _ogredoc_TEX_max_anisotropy( INFO_MT_ogre_helper ):
    mydoc = '''
max_anisotropy
    @2
    @4
    @8
    @16
Sets the maximum degree of anisotropy that the renderer will try to compensate for when filtering textures. The degree of anisotropy is the ratio between the height of the texture segment visible in a screen space region versus the width - so for example a floor plane, which stretches on into the distance and thus the vertical texture coordinates change much faster than the horizontal ones, has a higher anisotropy than a wall which is facing you head on (which has an anisotropy of 1 if your line of sight is perfectly perpendicular to it). You should set the max_anisotropy value to something greater than 1 to begin compensating; higher values can compensate for more acute angles. The maximum value is determined by the hardware, but it is usually 8 or 16. 

In order for this to be used, you have to set the minification and/or the magnification filtering option on this texture to anisotropic. Format: max_anisotropy <value>
Default: max_anisotropy 1
'''

@ogredoc
class _ogredoc_TEX_mipmap_bias( INFO_MT_ogre_helper ):
    mydoc = '''
mipmap_bias
    @1
    @4
    @8

Sets the bias value applied to the mipmapping calculation, thus allowing you to alter the decision of which level of detail of the texture to use at any distance. The bias value is applied after the regular distance calculation, and adjusts the mipmap level by 1 level for each unit of bias. Negative bias values force larger mip levels to be used, positive bias values force smaller mip levels to be used. The bias is a floating point value so you can use values in between whole numbers for fine tuning.

In order for this option to be used, your hardware has to support mipmap biasing (exposed through the render system capabilities), and your minification filtering has to be set to point or linear. Format: mipmap_bias <value>
Default: mipmap_bias 0
'''

@ogredoc
class _ogredoc_TEX_colour_op( INFO_MT_ogre_helper ):
    mydoc = '''
colour_op

Determines how the colour of this texture layer is combined with the one below it (or the lighting effect on the geometry if this is the first layer).
Format: colour_op <replace|add|modulate|alpha_blend>

This method is the simplest way to blend texture layers, because it requires only one parameter, gives you the most common blending types, and automatically sets up 2 blending methods: one for if single-pass multitexturing hardware is available, and another for if it is not and the blending must be achieved through multiple rendering passes. It is, however, quite limited and does not expose the more flexible multitexturing operations, simply because these can't be automatically supported in multipass fallback mode. If want to use the fancier options, use colour_op_ex, but you'll either have to be sure that enough multitexturing units will be available, or you should explicitly set a fallback using colour_op_multipass_fallback.
@replace
    Replace all colour with texture with no adjustment.
@add
    Add colour components together.
@modulate
    Multiply colour components together.
@alpha_blend
    Blend based on texture alpha.

Default: colour_op modulate
'''

@ogredoc
class _ogredoc_TEX_colour_op_ex( INFO_MT_ogre_helper ):
    mydoc = '''
colour_op_ex
    @add_signed src_manual src_current 0.5

This is an extended version of the colour_op attribute which allows extremely detailed control over the blending applied between this and earlier layers. Multitexturing hardware can apply more complex blending operations that multipass blending, but you are limited to the number of texture units which are available in hardware.

Format: colour_op_ex <operation> <source1> <source2> [<manual_factor>] [<manual_colour1>] [<manual_colour2>]
Example colour_op_ex add_signed src_manual src_current 0.5

See the IMPORTANT note below about the issues between multipass and multitexturing that using this method can create. Texture colour operations determine how the final colour of the surface appears when rendered. Texture units are used to combine colour values from various sources (e.g. the diffuse colour of the surface from lighting calculations, combined with the colour of the texture). This method allows you to specify the 'operation' to be used, i.e. the calculation such as adds or multiplies, and which values to use as arguments, such as a fixed value or a value from a previous calculation.

Operation options:
    source1
        Use source1 without modification
    source2
        Use source2 without modification
    modulate
        Multiply source1 and source2 together.
    modulate_x2
        Multiply source1 and source2 together, then by 2 (brightening).
    modulate_x4
        Multiply source1 and source2 together, then by 4 (brightening).
    add
        Add source1 and source2 together.
    add_signed
        Add source1 and source2 then subtract 0.5.
    add_smooth
        Add source1 and source2, subtract the product
    subtract
        Subtract source2 from source1
    blend_diffuse_alpha
        Use interpolated alpha value from vertices to scale source1, then add source2 scaled by (1-alpha).
    blend_texture_alpha
        As blend_diffuse_alpha but use alpha from texture
    blend_current_alpha
        As blend_diffuse_alpha but use current alpha from previous stages (same as blend_diffuse_alpha for first layer)
    blend_manual
        As blend_diffuse_alpha but use a constant manual alpha value specified in <manual>
    dotproduct
        The dot product of source1 and source2
    blend_diffuse_colour

        Use interpolated colour value from vertices to scale source1, then add source2 scaled by (1-colour).

Source1 and source2 options:
    src_current
        The colour as built up from previous stages.
    src_texture
        The colour derived from the texture assigned to this layer.
    src_diffuse
        The interpolated diffuse colour from the vertices (same as 'src_current' for first layer).
    src_specular
        The interpolated specular colour from the vertices.
    src_manual
        The manual colour specified at the end of the command.

For example 'modulate' takes the colour results of the previous layer, and multiplies them with the new texture being applied. Bear in mind that colours are RGB values from 0.0-1.0 so multiplying them together will result in values in the same range, 'tinted' by the multiply. Note however that a straight multiply normally has the effect of darkening the textures - for this reason there are brightening operations like modulate_x2. Note that because of the limitations on some underlying APIs (Direct3D included) the 'texture' argument can only be used as the first argument, not the second. 

Note that the last parameter is only required if you decide to pass a value manually into the operation. Hence you only need to fill these in if you use the 'blend_manual' operation.

'''

@ogredoc
class _ogredoc_TEX_colour_op_multipass_fallback( INFO_MT_ogre_helper ):
    mydoc = '''
colour_op_multipass_fallback
    @one one_minus_dest_alpha

Sets the multipass fallback operation for this layer, if you used colour_op_ex and not enough multitexturing hardware is available.

Format: colour_op_multipass_fallback <src_factor> <dest_factor>
Example: colour_op_multipass_fallback one one_minus_dest_alpha

Because some of the effects you can create using colour_op_ex are only supported under multitexturing hardware, if the hardware is lacking the system must fallback on multipass rendering, which unfortunately doesn't support as many effects. This attribute is for you to specify the fallback operation which most suits you.

The parameters are the same as in the scene_blend attribute; this is because multipass rendering IS effectively scene blending, since each layer is rendered on top of the last using the same mechanism as making an object transparent, it's just being rendered in the same place repeatedly to get the multitexture effect. If you use the simpler (and less flexible) colour_op attribute you don't need to call this as the system sets up the fallback for you.

'''

@ogredoc
class _ogredoc_TEX_alpha_op_ex( INFO_MT_ogre_helper ):
    mydoc = '''
alpha_op_ex

Behaves in exactly the same away as colour_op_ex except that it determines how alpha values are combined between texture layers rather than colour values.The only difference is that the 2 manual colours at the end of colour_op_ex are just single floating-point values in alpha_op_ex.
'''

@ogredoc
class _ogredoc_TEX_env_map( INFO_MT_ogre_helper ):
    mydoc = '''
env_map

Turns on/off texture coordinate effect that makes this layer an environment map.

Format: env_map <off|spherical|planar|cubic_reflection|cubic_normal>

Environment maps make an object look reflective by using automatic texture coordinate generation depending on the relationship between the objects vertices or normals and the eye.

@spherical
    A spherical environment map. Requires a single texture which is either a fish-eye lens view of the reflected scene, or some other texture which looks good as a spherical map (a texture of glossy highlights is popular especially in car sims). This effect is based on the relationship between the eye direction and the vertex normals of the object, so works best when there are a lot of gradually changing normals, i.e. curved objects.
@planar
    Similar to the spherical environment map, but the effect is based on the position of the vertices in the viewport rather than vertex normals. This effect is therefore useful for planar geometry (where a spherical env_map would not look good because the normals are all the same) or objects without normals.
@cubic_reflection
    A more advanced form of reflection mapping which uses a group of 6 textures making up the inside of a cube, each of which is a view if the scene down each axis. Works extremely well in all cases but has a higher technical requirement from the card than spherical mapping. Requires that you bind a cubic_texture to this texture unit and use the 'combinedUVW' option.
@cubic_normal
    Generates 3D texture coordinates containing the camera space normal vector from the normal information held in the vertex data. Again, full use of this feature requires a cubic_texture with the 'combinedUVW' option.

Default: env_map off
'''

@ogredoc
class _ogredoc_TEX_scroll( INFO_MT_ogre_helper ):
    mydoc = '''
scroll

Sets a fixed scroll offset for the texture.
Format: scroll <x> <y>

This method offsets the texture in this layer by a fixed amount. Useful for small adjustments without altering texture coordinates in models. However if you wish to have an animated scroll effect, see the scroll_anim attribute.

[use mapping node location x and y]
'''

@ogredoc
class _ogredoc_TEX_scroll_anim( INFO_MT_ogre_helper ):
    mydoc = '''
scroll_anim
    @0.1 0.1
    @0.5 0.5
    @2.0 3.0

Sets up an animated scroll for the texture layer. Useful for creating fixed-speed scrolling effects on a texture layer (for varying scroll speeds, see wave_xform).

Format: scroll_anim <xspeed> <yspeed>
'''

@ogredoc
class _ogredoc_TEX_rotate( INFO_MT_ogre_helper ):
    mydoc = '''
rotate
Rotates a texture to a fixed angle. This attribute changes the rotational orientation of a texture to a fixed angle, useful for fixed adjustments. If you wish to animate the rotation, see rotate_anim.
Format: rotate <angle>
The parameter is a anti-clockwise angle in degrees.
[ use mapping node rotation x ]
'''

@ogredoc
class _ogredoc_TEX_rotate_anim( INFO_MT_ogre_helper ):
    mydoc = '''
rotate_anim
    @0.1
    @0.2
    @0.4
Sets up an animated rotation effect of this layer. Useful for creating fixed-speed rotation animations (for varying speeds, see wave_xform).
Format: rotate_anim <revs_per_second>
The parameter is a number of anti-clockwise revolutions per second.
'''

@ogredoc
class _ogredoc_TEX_scale( INFO_MT_ogre_helper ):
    mydoc = '''
scale
Adjusts the scaling factor applied to this texture layer. Useful for adjusting the size of textures without making changes to geometry. This is a fixed scaling factor, if you wish to animate this see wave_xform.
Format: scale <x_scale> <y_scale>
Valid scale values are greater than 0, with a scale factor of 2 making the texture twice as big in that dimension etc.
[ use mapping node scale x and y ]
'''

@ogredoc
class _ogredoc_TEX_wave_xform( INFO_MT_ogre_helper ):
    mydoc = '''
wave_xform
    @scale_x sine 1.0 0.2 0.0 5.0

Sets up a transformation animation based on a wave function. Useful for more advanced texture layer transform effects. You can add multiple instances of this attribute to a single texture layer if you wish.

Format: wave_xform <xform_type> <wave_type> <base> <frequency> <phase> <amplitude>

Example: wave_xform scale_x sine 1.0 0.2 0.0 5.0

xform_type:
    scroll_x
        Animate the x scroll value
    scroll_y
        Animate the y scroll value
    rotate
        Animate the rotate value
    scale_x
        Animate the x scale value
    scale_y
        Animate the y scale value

wave_type
    sine
        A typical sine wave which smoothly loops between min and max values
    triangle
        An angled wave which increases & decreases at constant speed, changing instantly at the extremes
    square
        Max for half the wavelength, min for the rest with instant transition between
    sawtooth
        Gradual steady increase from min to max over the period with an instant return to min at the end.
    inverse_sawtooth
        Gradual steady decrease from max to min over the period, with an instant return to max at the end.

base
    The base value, the minimum if amplitude > 0, the maximum if amplitude < 0
frequency
    The number of wave iterations per second, i.e. speed
phase
    Offset of the wave start
amplitude
    The size of the wave

The range of the output of the wave will be {base, base+amplitude}. So the example above scales the texture in the x direction between 1 (normal size) and 5 along a sine wave at one cycle every 5 second (0.2 waves per second).
'''

@ogredoc
class _ogredoc_TEX_transform( INFO_MT_ogre_helper ):
    mydoc = '''
transform
    @m00 m01 m02 m03 m10 m11 m12 m13 m20 m21 m22 m23 m30 m31 m32 m33
This attribute allows you to specify a static 4x4 transformation matrix for the texture unit, thus replacing the individual scroll, rotate and scale attributes mentioned above. 
Format: transform m00 m01 m02 m03 m10 m11 m12 m13 m20 m21 m22 m23 m30 m31 m32 m33
The indexes of the 4x4 matrix value above are expressed as m<row><col>.
'''

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
        elif propname in VersionControlMesh:
            user = doc.createElement('version_control')
            o.appendChild( user )
            user.setAttribute( 'name', propname )
            user.setAttribute( 'value', str(propvalue) )
            user.setAttribute( 'type', type(propvalue).__name__ )


class Ogre_import_op(bpy.types.Operator):
    '''Import Ogre Scene'''
    bl_idname = "ogre.import"
    bl_label = "Import Ogre"
    bl_options = {'REGISTER'}
    filepath= StringProperty(name="File Path", description="Filepath used for importing Ogre .scene file", maxlen=1024, default="")
    COPY_ATTRIBUTES = BoolProperty(name="Copy Attributes", description="copy version control attributes: category, title, owner, etc.", default=True)

    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        wm= context.window_manager; wm.fileselect_add(self)        # writes to filepath
        return {'RUNNING_MODAL'}
    def execute(self, context):
        Report.reset()
        doc = dom.parse( self.filepath )
        nodes = doc.getElementsByTagName('node')
        for node in nodes:
            print( node )
            name = node.getAttribute('name')
            if node.hasAttribute('uuid') and name in bpy.data.objects.keys():
                ob = bpy.data.objects[ name ]
                uuid = node.getAttribute('uuid')
                print(name, uuid)
                if '_UUID_' in ob.keys():
                    if ob['_UUID_'] == uuid:
                        Report.messages.append( '%s: already has matching UUID' %name )
                    else:
                        Report.messages.append( '%s: syncing UUID' %name )
                else:
                    Report.messages.append( '%s: updating UUID' %name )

                ob[ '_UUID_' ] = uuid
                if self.COPY_ATTRIBUTES:
                    vcs = node.getElementsByTagName('version_control')
                    d = {}
                    for vc in vcs:
                        n = vc.getAttribute('name')
                        v = vc.getAttribute('value')
                        t = vc.getAttribute('type')
                        if t == 'int': v = int( v )
                        elif t == 'float': v = float( v )
                        d[ n ] = v

        Report.show()
        return {'FINISHED'}


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


class _OgreCommonExport_(object):
    @classmethod
    def poll(cls, context): return True
    def invoke(self, context, event):
        wm = context.window_manager
        fs = wm.fileselect_add(self)        # writes to filepath
        print( 'fs', fs )
        return {'RUNNING_MODAL'}
    def execute(self, context): self.ogre_export(  self.filepath, context ); return {'FINISHED'}


    #EXPORT_TYPE = StringProperty(default="OGRE")
    ## Options ##
    _axis_modes =  [
        ('x z -y', 'x z -y', 'ogre standard'),
        ('x y z', 'x y z', 'no swapping'),
        ('-x z y', '-x z y', 'old default'),
        ('x z y', 'x z y', 'swap y and z'),
    ]


    _image_formats =  [
        ('','do not convert', 'default'),
        ('jpg', 'jpg', 'jpeg format'),
        ('png', 'png', 'png format'),
        ('dds', 'dds', 'nvidia dds format'),
    ]



    def dot_material( self, meshes, path='/tmp', mat_file_name='SceneMaterial'):
        print('updating .material')
        mats = []
        for ob in meshes:
            if len(ob.data.materials):
                for mat in ob.data.materials:
                    if mat not in mats: mats.append( mat )
        if not mats: print('WARNING: no materials, not writting .material script'); return
        M = MISSING_MATERIAL + '\n'
        for mat in mats:
            if mat is None:
                continue
            Report.materials.append( material_name(mat) )
            data = self.gen_dot_material( mat, path, convert_textures=True )
            M += data
            if self.EXPORT_TYPE == 'REX': self.dot_material_write_separate( mat, data, path )

        #always sets "Scene.material", not so good if exporting all stuff to same directory
        #url = os.path.join(path, '%s.material' %bpy.context.scene.name)
        url = os.path.join(path, '%s.material' % mat_file_name)
        f = open( url, 'wb' ); f.write( bytes(M,'utf-8') ); f.close()
        print('saved', url)

    def dot_material_write_separate( self, mat, data, path = '/tmp' ):      # thanks Pforce
        url = os.path.join(path, '%s.material' % material_name(mat))
        f = open(url, 'wb'); f.write( bytes(data,'utf-8') ); f.close()
        print('saved', url)

    ## python note: classmethods prefer attributes defined at the classlevel, kinda makes sense, (even if called by an instance)
    @classmethod
    def gen_dot_material( self, mat, path='/tmp', convert_textures=False ):        # TODO deprecated context_textures...
        M = ''
        M += 'material %s \n{\n'        %material_name(mat)     # supports blender library linking
        if mat.use_shadows: M += indent(1, 'receive_shadows on')
        else: M += indent(1, 'receive_shadows off')

        M += indent(1, 'technique', '{' )    # technique GLSL
        #if mat.use_vertex_color_paint:
        M += self.gen_dot_material_pass( mat, path, convert_textures )

        M += indent(1, '}' )    # end technique
        M += '}\n'    # end material
        return M

    @classmethod
    def gen_dot_material_pass( self, mat, path, convert_textures ):
        print('GEN DOT MATERIAL...', mat)
        OPTIONS['PATH'] = path
        M = ''
        #if mat.node_tree and len(mat.node_tree.nodes):
        if ShaderTree.valid_node_material( mat ):
            print('        NODES MATERIAL')
            tree = ShaderTree.parse( mat )
            passes = tree.get_passes()
            for P in passes:
                print('        SHADER PASS:', P)
                M += P.dotmat_pass()
        else:
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
        #OPTIONS['SWAP_AXIS'] = self.EX_SWAP_MODE
        Report.reset()

        ShaderTree.EX_DDS_MIPS = self.EX_DDS_MIPS

        if self.EX_FORCE_IMAGE:
            fmt = self.EX_FORCE_IMAGE.lower()
            if not fmt.startswith('.'): fmt = '.'+fmt
            OPTIONS['FORCE_IMAGE_FORMAT'] = fmt

        meshes = []
        mesh_collision_prims = {}
        mesh_collision_files = {}

        print('ogre export->', url)
        prefix = url.split('.')[0]

        #rex = dom.Document()        # realxtend .rex
        rex = RDocument()

        rex.appendChild( rex.createElement('scene') )

        now = time.time()
        #doc = dom.Document()
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
        extern = doc.createElement('externals')
        environ = doc.createElement('environment')
        for n in (nodes,extern,environ): scn.appendChild( n )
        ############################

        ## extern files ##
        item = doc.createElement('item'); extern.appendChild( item )
        item.setAttribute('type','material')
        a = doc.createElement('file'); item.appendChild( a )
        #does return "Scene" always
        #material_file_name_base=context.scene.name
        material_file_name_base=os.path.split(url)[1].replace('.scene', '').replace('.txml', '')
        a.setAttribute('name', '%s.material' % material_file_name_base)    # .material file (scene mats)


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


        ## nodes (objects) ##
        objects = []        # gather because macros will change selection state
        linkedgroups = []
        for ob in bpy.context.scene.objects:
            if ob.name.startswith('collision'): continue
            if self.EX_SELONLY and not ob.select:
                if ob.type == 'CAMERA' and self.EX_FORCE_CAMERA: pass
                elif ob.type == 'LAMP' and self.EX_FORCE_LAMPS: pass
                else: continue
            if ob.type == 'EMPTY' and ob.dupli_group and ob.dupli_type == 'GROUP': linkedgroups.append( ob )
            else: objects.append( ob )

        temps = []

        for e in linkedgroups:
            grp = e.dupli_group
            subs = []
            for o in grp.objects:
                if o.type=='MESH': subs.append( o )
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
        for ob in objects:
            flat = []
            _flatten( ob, flat )
            root = flat[-1]
            if root not in roots: roots.append( root )

        exported_meshes = []        # don't export same data multiple times
        for root in roots:
            print('--------------- exporting root ->', root )
            self._node_export( root, 
                url=url, doc = doc, rex = rex, 
                exported_meshes = exported_meshes, 
                meshes = meshes,
                mesh_collision_prims = mesh_collision_prims,
                mesh_collision_files = mesh_collision_files,
                prefix = prefix,
                objects=objects, 
                xmlparent=nodes 
            )

        if self.EX_SCENE:
            if self.EXPORT_TYPE == 'REX':
                if not url.endswith('.txml'): url += '.txml'
                data = rex.toprettyxml()
                f = open( url, 'wb' ); f.write( bytes(data,'utf-8') ); f.close()
                print('realxtend scene dumped', url)
            else:
                if not url.endswith('.scene'): url += '.scene'
                data = doc.toprettyxml()
                f = open( url, 'wb' ); f.write( bytes(data,'utf-8') ); f.close()
                print('ogre scene dumped', url)


        if self.EX_MATERIALS: self.dot_material( meshes, os.path.split(url)[0], material_file_name_base)

        for ob in temps:context.scene.objects.unlink( ob )
        bpy.ops.wm.call_menu( name='Ogre_User_Report' )


    ############# node export - recursive ###############
    def _node_export( self, ob, url='', doc=None, rex=None, exported_meshes=[], meshes=[], mesh_collision_prims={}, mesh_collision_files={}, prefix='', objects=[], xmlparent=None ):

        o = _ogre_node_helper( doc, ob, objects )
        xmlparent.appendChild(o)

        ## UUID ##
        o.setAttribute('uuid', UUID(ob))

        ## custom user props ##
        for prop in ob.items():
            propname, propvalue = prop
            if not propname.startswith('_'):
                user = doc.createElement('user_data')
                o.appendChild( user )
                user.setAttribute( 'name', propname )
                user.setAttribute( 'value', str(propvalue) )
                user.setAttribute( 'type', type(propvalue).__name__ )
            elif propname in VersionControl+VersionControlUser:
                user = doc.createElement('version_control')
                o.appendChild( user )
                user.setAttribute( 'name', propname )
                user.setAttribute( 'value', str(propvalue) )
                user.setAttribute( 'type', type(propvalue).__name__ )

        # no need to store _exported_ time per object?? #
        #if '_modified_' in ob.keys():
        #    #if ob['_modified_'] >= ob['_exported_']:
        #    ob['_exported_'] = time.time()        # Ogre engine can test if _modified_ is newer than _exported_, and decide if to reload


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
            self.rex_entity( rex, ob )        # is dotREX flat?

            collisionFile = None
            collisionPrim = None
            if ob.data.name in mesh_collision_prims: collisionPrim = mesh_collision_prims[ ob.data.name ]
            if ob.data.name in mesh_collision_files: collisionFile = mesh_collision_files[ ob.data.name ]

            meshes.append( ob )
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
                        if child.name.startswith('collision'):        # double check, instances with decimate modifier are ok?
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


    ########################################
    def rex_entity( self, doc, ob ):        # does rex flatten the hierarchy? or keep it like ogredotscene?
        proto = 'local://'      # antont says file:// is also valid
        e = doc.createElement( 'entity' )
        doc.documentElement.appendChild( e )
        e.setAttribute('id', str(len(doc.documentElement.childNodes)) )

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

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Name")
        c.setAttribute('sync', '1')

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "name" )
        a.setAttribute('value', ob.data.name )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "description" )
        a.setAttribute('value', "" )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "user-defined" )
        a.setAttribute('value', "false" )

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Placeable")
        c.setAttribute('sync', '1')

        ############ Tundra TRANSFORM ####################
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Transform" )
        x,z,y = ob.matrix_world.to_translation()
        loc = '%6f,%6f,%6f' %(-x,y,z)
        x,z,y = ob.matrix_world.to_euler()
        x = math.degrees( x ); y = math.degrees( y ); z = math.degrees( z )
        rot = '%6f,%6f,%6f' %(-x,y,z)
        x,z,y = ob.matrix_world.to_scale()
        scl = '%6f,%6f,%6f' %(abs(x),abs(y),abs(z))		# Tundra2 clamps any negative to zero
        a.setAttribute('value', "%s,%s,%s" %(loc,rot,scl) )
        #############################################


        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Show bounding box" )
        if ob.show_bounds: a.setAttribute('value', "true" )
        else: a.setAttribute('value', "false" )

        ## realXtend internal Naali format ##
        if ob.game.physics_type == 'RIGID_BODY':
            com = doc.createElement('component'); e.appendChild( com )
            com.setAttribute('type', 'EC_RigidBody')
            com.setAttribute('sync', '1')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Mass')
            a.setAttribute('value', str(ob.game.mass))

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Friction')
            avg = sum( ob.game.friction_coefficients ) / 3.0
            a.setAttribute('value', str(avg))

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Linear damping')
            a.setAttribute('value', str(ob.game.damping))

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Angular damping')
            a.setAttribute('value', str(ob.game.rotation_damping))

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Phantom')        # this must mean no-collide
            a.setAttribute('value', str(ob.game.use_ghost).lower() )


class INFO_OT_createOgreExport(bpy.types.Operator, _OgreCommonExport_):
    '''Export Ogre Scene'''
    bl_idname = "ogre.export"
    bl_label = "Export Ogre"
    bl_options = {'REGISTER', 'UNDO'}
    filepath= StringProperty(name="File Path", description="Filepath used for exporting Ogre .scene file", maxlen=1024, default="", subtype='FILE_PATH')
    EXPORT_TYPE = 'OGRE'

    #EX_SWAP_MODE = EnumProperty( items=_OgreCommonExport_._axis_modes, name='swap axis',  description='axis swapping mode', default='x z -y' )
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

    #EX_SWAP_MODE = EnumProperty( items=_OgreCommonExport_._axis_modes, name='swap axis',  description='axis swapping mode', default='x z -y' )
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
    mat = get_parent_matrix(ob, objects).inverted() * ob.matrix_world

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
        self.flipMat = mathutils.Matrix(((-1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)))
        self.skeleton = skeleton
        self.name = pbone.name
        #self.matrix = self.flipMat * matrix
        self.matrix = matrix
        self.bone = pbone        # safe to hold pointer to pose bone, not edit bone!
        if not pbone.bone.use_deform: print('warning: bone <%s> is non-deformabled, this is inefficient!' %self.name)
        #TODO test#if pbone.bone.use_inherit_scale: print('warning: bone <%s> is using inherit scaling, Ogre has no support for this' %self.name)
        self.parent = pbone.parent
        self.children = []
        self.fixUpAxis = True

    def update(self):        # called on frame update
        pose = self.bone.matrix.copy()
        #pose = self.bone.matrix * self.skeleton.object_space_transformation
        #pose =  self.skeleton.object_space_transformation * self.bone.matrix
        self._inverse_total_trans_pose = pose.inverted()

        # calculate difference to parent bone
        if self.parent:
            pose = self.parent._inverse_total_trans_pose * pose
        elif self.fixUpAxis:
            #pose = mathutils.Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1))) * pose   # Requiered for Blender SVN > 2.56
            pose = self.flipMat * pose

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
        elif (self.fixUpAxis):
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
        arm.layers = [True]*20      # can not have anything hidden - just to be sure
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
                    for group in strip.action.groups:        # check if the user has keyed only some of the bones (for anim blending)
                        if group.name in arm.pose.bones: stripbones.append( group.name )
                    if not stripbones:                                    # otherwise we use all bones
                        for bone in arm.pose.bones: stripbones.append( bone.name )
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

############ extra tools ##############


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





import array, time, ctypes
class CtypesMesh(object):

    def get_vertex_position(self, idx ):
        v = self.vertex_positions; d = idx*3
        return v[ d ], v[ d+1 ], v[ d+2 ]

    def get_vertex_normal(self, idx ):
        v = self.vertex_normals; d = idx*3
        return v[ d ], v[ d+1 ], v[ d+2 ]

    def __init__(self, data):
        self.numVerts = N = len( data.vertices )
        self.numFaces = Nfaces = len(data.faces)

        #self.vertex_positions = array.array( 'f', [.0]*3 ) * N
        self.vertex_positions = (ctypes.c_float * (N * 3))()
        data.vertices.foreach_get( 'co', self.vertex_positions )
        v = self.vertex_positions

        #start = time.time()     # 5x slower than doing the same thing with array.array
        #for i in range(N):
        #    x,y,z=data.vertices[i].co
        #print('end slow', time.time()-start )

        self.vertex_normals = (ctypes.c_float * (N * 3))()
        data.vertices.foreach_get( 'normal', self.vertex_normals )
        print('vert normals ok')

        self.faces = (ctypes.c_uint * (Nfaces * 4))()
        data.faces.foreach_get( 'vertices_raw', self.faces )
        print('faces ok')

        self.faces_normals = (ctypes.c_float * (Nfaces * 3))()
        data.faces.foreach_get( 'normal', self.faces_normals )
        print('face normals ok')


        self.faces_smooth = (ctypes.c_bool * Nfaces)() 
        data.faces.foreach_get( 'use_smooth', self.faces_smooth )
        print('faces smooth ok')
        #for i in range(self.numFaces): print(' smooth:', self.faces_smooth[i], i )

        self.faces_material_index = (ctypes.c_ushort * Nfaces)() 
        data.faces.foreach_get( 'material_index', self.faces_material_index )
        print('faces mat idx ok')

        self.vertex_colors = []
        if len( data.vertex_colors ):
            vc = data.vertex_colors[0]
            n = len(vc.data)
            # no colors_raw !!?
            self.vcolors1 = (ctypes.c_float * (n * 3))()  # face1
            vc.data.foreach_get( 'color1', self.vcolors1 )
            self.vertex_colors.append( self.vcolors1 )

            self.vcolors2 = (ctypes.c_float * (n * 3))()  # face2
            vc.data.foreach_get( 'color2', self.vcolors2 )
            self.vertex_colors.append( self.vcolors2 )

            self.vcolors3 = (ctypes.c_float * (n * 3))()  # face3
            vc.data.foreach_get( 'color3', self.vcolors3 )
            self.vertex_colors.append( self.vcolors3 )

            self.vcolors4 = (ctypes.c_float * (n * 3))()  # face4
            vc.data.foreach_get( 'color4', self.vcolors4 )
            self.vertex_colors.append( self.vcolors4 )

        self.uv_textures = []
        if data.uv_textures.active:
            for layer in data.uv_textures:
                n = len(layer.data) * 8
                a = (ctypes.c_float * n)()
                layer.data.foreach_get( 'uv_raw', a )   # 4 faces
                self.uv_textures.append( a )





try: import io_export_rogremesh.rogremesh as R
except:
    R = None
    print( 'WARNING: "io_export_rogremesh" is missing' )

if R and R.rpy.load(): _USE_RPYTHON_ = True
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

'''
        return abs(self.nx - o.nx) < EPSILON and abs(self.ny - o.ny) < EPSILON and abs(self.nz - o.nz) < EPSILON and abs(self.r - o.r) < EPSILON \
                and abs(self.g - o.g) < EPSILON and abs(self.b - o.b) < EPSILON and abs(self.ra - o.ra) < EPSILON \
                and ( self.vert_uvs == o.vert_uvs or ( \
                abs(self.vert_uvs[0][0] - o.vert_uvs[0][0]) < EPSILON and abs(self.vert_uvs[0][1] - o.vert_uvs[0][1]) < EPSILON \
                and abs(self.vert_uvs[1][0] - o.vert_uvs[1][0]) < EPSILON and abs(self.vert_uvs[1][1] - o.vert_uvs[1][1]) < EPSILON ) )
'''

#######################################################################################
def dot_mesh( ob, path='/tmp', force_name=None, ignore_shape_animation=False, opts=OptionsEx, normals=True ):
    start = time.time()
    print('mesh to Ogre mesh XML format', ob.name)

    if _USE_RPYTHON_ and False: cmesh = CtypesMesh( ob.data ); R.dump( cmesh )

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

    #replaced by sax parser
    #doc = RDocument()
    #root = doc.createElement('mesh'); doc.appendChild( root )
    name = force_name or ob.data.name
    xmlfile = os.path.join(path, '%s.mesh.xml' %name )
    try:
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

                    x,y,z = swap( v.co )
                    
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
    finally:
        if doc:
            doc.close()
        if f:
            f.close()


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
        op = layout.operator( Ogre_ogremeshy_op.bl_idname, text='', icon='PLUGIN' ); op.mesh = True
        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.menu("INFO_MT_file")
        sub.menu("INFO_MT_add")
        if rd.use_game_engine: sub.menu("INFO_MT_game")
        else: sub.menu("INFO_MT_render")

        row = layout.row(align=True); row.scale_x=1.5
        row.menu("INFO_MT_instances", icon='NODETREE')
        row.menu("INFO_MT_groups", icon='GROUP')
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

            layout.separator()
            row = layout.row(align=True)        # align makes buttons compact together
            row.operator("screen.frame_jump", text="", icon='REW').end = False
            row.operator("screen.keyframe_jump", text="", icon='PREV_KEYFRAME').next = False
            if not screen.is_animation_playing: row.operator("screen.animation_play", text="", icon='PLAY')
            else: sub = row.row(); sub.scale_x = 1.0; sub.operator("screen.animation_play", text="", icon='PAUSE')
            row.operator("screen.keyframe_jump", text="", icon='NEXT_KEYFRAME').next = True
            row.operator("screen.frame_jump", text="", icon='FF').end = True
            row = layout.row(align=True)
            layout.prop(scene, "frame_current", text="")



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

def import_menu_func(self, context):
    self.layout.operator(Ogre_import_op.bl_idname, text="Ogre3D (.scene) | read version control attributes (UUIDs)")

_header_ = None
class OGRE_toggle_toolbar_op(bpy.types.Operator):
    '''Toggle Ogre UI'''
    bl_idname = "ogre.toggle_interface"
    bl_label = "Ogre"
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
        else:
            bpy.utils.register_module(__name__)
            _header_ = bpy.types.INFO_HT_header
            bpy.utils.unregister_class(_header_)
        return {'FINISHED'}

class INFO_HT_microheader(bpy.types.Header):
    bl_space_type = 'INFO'
    def draw(self, context):
        layout = self.layout
        op = layout.operator( OGRE_toggle_toolbar_op.bl_idname, icon='UI' )

_OGRE_MINIMAL_ = ( INFO_OT_createOgreExport, INFO_OT_createRealxtendExport, OGRE_toggle_toolbar_op, INFO_HT_microheader, Ogre_User_Report)

MyShaders = None
def register():
    print( '-'*80)
    print(VERSION)
    global MyShaders, _header_
    #bpy.utils.register_module(__name__)
    #_header_ = bpy.types.INFO_HT_header
    #bpy.utils.unregister_class(_header_)
    for op in _OGRE_MINIMAL_: bpy.utils.register_class( op )
    readOrCreateConfig()
    MyShaders = MyShadersSingleton()
    bpy.types.INFO_MT_file_export.append(export_menu_func_ogre)
    bpy.types.INFO_MT_file_export.append(export_menu_func_realxtend)
    bpy.types.INFO_MT_file_import.append(import_menu_func)
    print( '-'*80)

def unregister():
    global _header_
    print('unreg-> ogre exporter')
    bpy.utils.unregister_module(__name__)
    if _header_: bpy.utils.register_class(_header_); _header_ = None
    bpy.types.INFO_MT_file_export.remove(export_menu_func_ogre)
    bpy.types.INFO_MT_file_export.remove(export_menu_func_realxtend)
    bpy.types.INFO_MT_file_import.remove(import_menu_func)


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
	def createElement(self,tag): return RElement(tag)
	def appendChild(self,root): self.documentElement = root
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




################### Raymond Hettinger's Constant Folding ##################
# Decorator for BindingConstants at compile time
# A recipe by Raymond Hettinger, from Python Cookbook:
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/277940
# updated for Python3 and still compatible with Python2 - by Hart, May17th 2011

try: _BUILTINS_DICT_ = vars(__builtins__)
except: _BUILTINS_DICT_ = __builtins__
ISPYTHON2 = sys.version_info[0] == 2
_HETTINGER_FOLDS_ = 0

def _hettinger_make_constants(f, builtin_only=False, stoplist=[], verbose=0):
    from opcode import opmap, HAVE_ARGUMENT, EXTENDED_ARG
    global _HETTINGER_FOLDS_
    try:
        if ISPYTHON2: co = f.func_code; fname = f.func_name
        else: co = f.__code__; fname = f.__name__
    except AttributeError: return f        # Jython doesn't have a func_code attribute.
    if ISPYTHON2: newcode = map(ord, co.co_code)
    else: newcode = list( co.co_code )
    newconsts = list(co.co_consts)
    names = co.co_names
    codelen = len(newcode)
    if ISPYTHON2:
        if verbose >= 2: print( f.func_name )
        func_globals = f.func_globals
    else:
        if verbose >= 2: print( f.__name__ )
        func_globals = f.__globals__

    env = _BUILTINS_DICT_.copy()
    if builtin_only:
        stoplist = dict.fromkeys(stoplist)
        stoplist.update(func_globals)
    else:
        env.update(func_globals)

    # First pass converts global lookups into constants
    i = 0
    while i < codelen:
        opcode = newcode[i]
        if opcode in (EXTENDED_ARG, opmap['STORE_GLOBAL']):
            if verbose >= 1: print('skipping function', fname)
            return f    # for simplicity, only optimize common cases
        if opcode == opmap['LOAD_GLOBAL']:
            oparg = newcode[i+1] + (newcode[i+2] << 8)
            name = co.co_names[oparg]
            if name in env and name not in stoplist:
                value = env[name]
                for pos, v in enumerate(newconsts):
                    if v is value:
                        break
                else:
                    pos = len(newconsts)
                    newconsts.append(value)
                newcode[i] = opmap['LOAD_CONST']
                newcode[i+1] = pos & 0xFF
                newcode[i+2] = pos >> 8
                _HETTINGER_FOLDS_ += 1
                if verbose >= 2:
                    print( "    global constant fold:", name )
        i += 1
        if opcode >= HAVE_ARGUMENT:
            i += 2

    # Second pass folds tuples of constants and constant attribute lookups
    i = 0
    while i < codelen:

        newtuple = []
        while newcode[i] == opmap['LOAD_CONST']:
            oparg = newcode[i+1] + (newcode[i+2] << 8)
            newtuple.append(newconsts[oparg])
            i += 3

        opcode = newcode[i]
        if not newtuple:
            i += 1
            if opcode >= HAVE_ARGUMENT:
                i += 2
            continue

        if opcode == opmap['LOAD_ATTR']:
            obj = newtuple[-1]
            oparg = newcode[i+1] + (newcode[i+2] << 8)
            name = names[oparg]
            try:
                value = getattr(obj, name)
                if verbose >= 2: print( '    folding attribute', name )
            except AttributeError:
                continue
            deletions = 1

        elif opcode == opmap['BUILD_TUPLE']:
            oparg = newcode[i+1] + (newcode[i+2] << 8)
            if oparg != len(newtuple): continue
            deletions = len(newtuple)
            value = tuple(newtuple)

        else: continue

        reljump = deletions * 3
        newcode[i-reljump] = opmap['JUMP_FORWARD']
        newcode[i-reljump+1] = (reljump-3) & 0xFF
        newcode[i-reljump+2] = (reljump-3) >> 8

        n = len(newconsts)
        newconsts.append(value)
        newcode[i] = opmap['LOAD_CONST']
        newcode[i+1] = n & 0xFF
        newcode[i+2] = n >> 8
        i += 3
        _HETTINGER_FOLDS_ += 1
        if verbose >= 2:
            print( "    folded constant:",value )

    if ISPYTHON2:
        codestr = ''.join(map(chr, newcode))
        codeobj = type(co)(co.co_argcount, co.co_nlocals, co.co_stacksize,
                        co.co_flags, codestr, tuple(newconsts), co.co_names,
                        co.co_varnames, co.co_filename, co.co_name,
                        co.co_firstlineno, co.co_lnotab, co.co_freevars,
                        co.co_cellvars)
        return type(f)(codeobj, f.func_globals, f.func_name, f.func_defaults, f.func_closure)
    else:
        codestr = b''
        for s in newcode: codestr += s.to_bytes(1,'little')
        codeobj = type(co)(co.co_argcount, co.co_kwonlyargcount, co.co_nlocals, co.co_stacksize,
                        co.co_flags, codestr, tuple(newconsts), co.co_names,
                        co.co_varnames, co.co_filename, co.co_name,
                        co.co_firstlineno, co.co_lnotab, co.co_freevars,
                        co.co_cellvars)
        return type(f)(codeobj, f.__globals__, f.__name__, f.__defaults__, f.__closure__)


def hettinger_bind_recursive(mc, builtin_only=False, stoplist=[],  verbose=0):
    """Recursively apply constant binding to functions in a module or class.

    Use as the last line of the module (after everything is defined, but
    before test code).  In modules that need modifiable globals, set
    builtin_only to True.

    """
    import types
    try: d = vars(mc)
    except TypeError: return
    if ISPYTHON2: recursivetypes = (type, types.ClassType)
    else: recursivetypes = (type,)
    for k, v in d.items():
        if type(v) is types.FunctionType:
            newv = _hettinger_make_constants(v, builtin_only, stoplist,  verbose)
            setattr(mc, k, newv)
        elif type(v) in recursivetypes:
            hettinger_bind_recursive(v, builtin_only, stoplist, verbose)

def hettinger_transform( module=None ):
    global _HETTINGER_FOLDS_
    _HETTINGER_FOLDS_ = 0
    if not module: module = sys.modules[__name__]
    hettinger_bind_recursive( module, verbose=1 )
    print( 'HETTINGER: constants folded', _HETTINGER_FOLDS_ )


hettinger_transform()

