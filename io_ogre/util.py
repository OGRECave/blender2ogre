
# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    # ...so we need to reload our submodule(s) using importlib
    import importlib
    if "config" in locals():
        importlib.reload(config)

# This is only relevant on first run, on later reloads those modules
# are already in locals() and those statements do not do anything.
from . import config
from . report import Report
from os.path import split, splitext
import bpy, logging, logging, mathutils, os, re, subprocess, sys, time

logger = logging.getLogger('util')

def xml_converter_parameters():
    """
    Return the name of the ogre converter
    """
    if sys.platform.startswith("win"):
        # Don't display the Windows GPF dialog if the invoked program dies.
        # See comp.os.ms-windows.programmer.win32
        # How to suppress crash notification dialog?, Jan 14,2004 -
        # Raymond Chen's response [1]

        import ctypes
        SEM_NOGPFAULTERRORBOX = 0x0002 # From MSDN
        ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX);

    exe = config.get('OGRETOOLS_XML_CONVERTER')
    proc = subprocess.Popen([exe,'-v'],stdout=subprocess.PIPE)
    output, _ = proc.communicate()

    pattern = re.compile("OgreXMLConverter ([^ ]+) \((\d+)\.(\d+).(\d+)\) ([^ ]+)")

    match = pattern.match(output.decode('utf-8'))

    if match:
        version = (int(match.group(2)),int(match.group(3)),int(match.group(4)))
        return (match.group(1), version, match.group(5))

    return ("unknown", (1,9,0),"unknown") # means pre 1.10

def xml_converter_version():
    return xml_converter_parameters()[1]

def mesh_tool_parameters():
    """
    Extract OgreMeshTool version info and stuff
    """
    exe = config.get('OGRETOOLS_XML_CONVERTER')
    exe_path, name = os.path.split(exe)
    proc = subprocess.Popen([exe], stdout=subprocess.PIPE, cwd=exe_path)
    output, _ = proc.communicate()

    pattern = re.compile("OgreMeshTool ([^ ]+) \((\d+)\.(\d+).(\d+)\) ([^ ]+)")
    match = pattern.match(output.decode('utf-8'))

    if match:
        version = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
        return (match.group(1), version, match.group(5))

    return ("unknown", (0,0,0), "unknown") # should not happen

def mesh_tool_version():
    return mesh_tool_parameters()[1]

# Calls OgreMeshUpgrader to generate the LOD levels
def lod_create(infile):
    exe = config.get('OGRETOOLS_MESH_UPGRADER')

    # OgreMeshUpgrader only works in tandem with OgreXMLConverter, which are both Ogre v1.x tools.
    # For Ogre v2.x we will use OgreMeshTool to generate the LODs
    if detect_converter_type() != "OgreXMLConverter":
        return
    
    output_path, filename = os.path.split(infile)
    
    if not os.path.exists(infile):
        logger.warn("Cannot find file mesh file: %s, unable to generate LOD" % filename)
        Report.warnings.append("OgreMeshUpgrader failed, LODs will not be generated for this mesh: %s" % filename)
        return
    
    # Extract converter type from its output
    try:
        exe_path, exe_name = os.path.split(exe)
        proc = subprocess.Popen([exe], stdout=subprocess.PIPE, cwd=exe_path)
        output, _ = proc.communicate()
        output = output.decode('utf-8')
    except:
        output = ""
    
    # Check to see if the executable is actually OgreMeshUpgrader
    if output.find("OgreMeshUpgrader") == -1:
        logger.warn("Cannot find suitable OgreMeshUpgrader executable, unable to generate LOD")
        return

    cmd = [exe]

    cmd.append('-l')
    cmd.append(str(config.get('LOD_LEVELS')))
    
    cmd.append('-d')
    cmd.append(str(config.get('LOD_DISTANCE')))

    cmd.append('-p')
    cmd.append(str(config.get('LOD_PERCENT')))

    # Edge lists should be generated (or not) by mesh.py, not OgreMeshUpgrader
    cmd.append('-e')

    # Put logfile into output directory
    use_logger = False
    logfile = os.path.join(output_path, 'OgreMeshUpgrader.log')

    # Check to see if the -log option is available in this OgreMeshUpgrader version
    if output.find("-log") != -1:
        use_logger = True
        cmd.append('-log')
        cmd.append(logfile)

    # Finally, specify input file
    cmd.append(infile)

    logger.info("* Generating %s LOD levels for mesh: %s" % (config.get('LOD_LEVELS'), filename))

    # First try to execute with the -log option
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    output, error = proc.communicate()

    if use_logger == False:
        # If this OgreMeshUpgrader does not have -log then use python to write the output of stdout to a log file
        with open(logfile, 'w') as log:
            log.write(output)
    
    if proc.returncode != 0:
        logger.warn("OgreMeshUpgrader failed, LODs will not be generated for this mesh: %s" % filename)
        Report.warnings.append("OgreMeshUpgrader failed, LODs will not be generated for this mesh: %s" % filename)
        if error != None:
            logger.error(error)
        logger.warn(output)
    else:
        logger.info("- Generated %s LOD levels for mesh: %s" % (config.get('LOD_LEVELS'), filename))


def detect_converter_type():
    # todo: executing the same exe twice might not be efficient but will do for now
    # (twice because version will be extracted later in xml_converter_parameters)
    exe = config.get('OGRETOOLS_XML_CONVERTER')

    # extract converter type from its output
    try:
        proc = subprocess.Popen([exe], stdout=subprocess.PIPE)
        output, _ = proc.communicate()
        output = output.decode('utf-8')
    except:
        output = ""

    if output.find("OgreXMLConverter") != -1:
        return "OgreXMLConverter"
    if output.find("OgreMeshTool") != -1:
        return "OgreMeshTool"
    return "unknown"

def xml_convert(infile, has_uvs=False):
    # todo: Show a UI dialog to show this error. It's pretty fatal for normal usage.
    # We should show how to configure the converter location in config panel or tell the default path.
    exe = config.get('OGRETOOLS_XML_CONVERTER')

    converter_type = detect_converter_type()
    if converter_type == "OgreXMLConverter":
        version = xml_converter_version()
    elif converter_type == "OgreMeshTool":
        version = mesh_tool_version()
    elif converter_type == "unknown":
        logger.warn("Cannot find suitable OgreXMLConverter or OgreMeshTool executable")
        Report.warnings.append("Cannot find suitable OgreXMLConverter or OgreMeshTool executable, binary mesh files won't be generated")
        return

    cmd = [exe]

    if config.get('EXTREMITY_POINTS') > 0 and version < (2,1,0):
        cmd.append('-x')
        cmd.append(config.get('EXTREMITY_POINTS'))

    if version < (1,10,0) or version >= (2,1,0):
        if not config.get('GENERATE_EDGE_LISTS'):
            cmd.append('-e')

    if config.get('OPTIMISE_VERTEX_BUFFERS') and version >= (2,1,0):
        cmd.append('-O')
        cmd.append(config.get('OPTIMISE_VERTEX_BUFFERS_OPTIONS'))

    if not config.get('OPTIMISE_ANIMATIONS'):
        cmd.append('-o')

    if version < (2,1,0):
        # Use quiet mode by default (comment this if you want more debug info out)
        cmd.append('-q')

        # use ubyte4_norm colour type
        if version >= (1, 12, 7):
            cmd.append('-byte')

        # Put logfile into output directory
        logfile_path, name = os.path.split(infile)
        cmd.append('-log')
        cmd.append(os.path.join(logfile_path, 'OgreXMLConverter.log'))

        # Finally, specify input file
        cmd.append(infile)

        ret = subprocess.call(cmd)

        # Instead of asserting, report an error
        if ret != 0:
            logger.error("OgreXMLConverter returned with non-zero status, check OgreXMLConverter.log")
            logger.info(" ".join(cmd))
            Report.errors.append("OgreXMLConverter finished with non-zero status converting mesh: (%s), it might not have been properly generated" % name)
        
        # Clean up .xml file after successful conversion
        if ret == 0 and config.get('XML_DELETE') == True:
            logger.info("Removing generated xml file after conversion: %s" % infile)
            os.remove(infile)
        
    else:
        # Convert to v2 format if required
        cmd.append('-%s' %config.get('MESH_TOOL_EXPORT_VERSION'))

        # If requested by the user, generate LOD levels through OgreMeshUpgrader/OgreMeshTool
        if config.get('LOD_LEVELS') > 0 and config.get('LOD_MESH_TOOLS') == True:
            cmd.append('-l')
            cmd.append(str(config.get('LOD_LEVELS')))
            
            cmd.append('-d')
            cmd.append(str(config.get('LOD_DISTANCE')))

            cmd.append('-p')
            cmd.append(str(config.get('LOD_PERCENT')))

        # Finally, specify input file
        cmd.append(infile)
        
        # OgreMeshTool must be run from its own directory (so setting cwd accordingly)
        # otherwise it will complain about missing render system (missing plugins_tools.cfg)
        exe_path, name = os.path.split(exe)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=exe_path)
        output, error = proc.communicate()

        # Open log file to replace old logging feature that the new tool dropped
        # The log file will be created alongside the exported mesh
        if config.get('EXPORT_ENABLE_LOGGING'):
            logfile_path, name = os.path.split(infile)
            logfile = os.path.join(logfile_path, 'OgreMeshTool.log')
        
            with open(logfile, 'w') as log:
                log.write(output)

        # Check converter status
        if proc.returncode != 0:
            logger.error("OgreMeshTool finished with non-zero status, check OgreMeshTool.log")
            logger.info(" ".join(cmd))
            Report.errors.append("OgreMeshTool finished with non-zero status converting mesh: (%s), it might not have been properly generated" % name)

        # Clean up .xml file after successful conversion
        if proc.returncode == 0 and config.get('XML_DELETE') == True:
            logger.info("Removing generated xml file after conversion: %s" % infile)
            os.remove(infile)

def image_magick( texture, origin_filepath, target_filepath ):
    exe = config.get('IMAGE_MAGICK_CONVERT')
    cmd = [ exe, origin_filepath ]

    x,y = texture.image.size
    ax = texture.image.resize_x
    ay = texture.image.resize_y

    if texture.image.use_convert_format and texture.image.convert_format == 'jpg':
        cmd.append( '-quality' )
        cmd.append( '%s' %texture.image.jpeg_quality )

    if texture.image.use_resize_half:
        cmd.append( '-resize' )
        cmd.append( '%sx%s' %(x/2, y/2) )
    elif texture.image.use_resize_absolute and (x>ax or y>ay):
        cmd.append( '-resize' )
        cmd.append( '%sx%s' %(ax,ay) )

    elif x > config.get('MAX_TEXTURE_SIZE') or y > config.get('MAX_TEXTURE_SIZE'):
        cmd.append( '-resize' )
        cmd.append( str(config.get('MAX_TEXTURE_SIZE')) )

    if texture.image.use_color_quantize:
        if texture.image.use_color_quantize_dither:
            cmd.append( '+dither' )
        cmd.append('-colors')
        cmd.append(str(texture.image.color_quantize))

    if target_filepath.endswith('.dds'):
        cmd.append('-define')
        cmd.append('dds:mipmaps={}'.format(config.get('DDS_MIPS') if texture.use_mipmap else 0))

    cmd.append(target_filepath)
    logging.debug('image magick: "%s"', ' '.join(cmd))
    subprocess.call(cmd)

def swap(vec):
    if config.get('SWAP_AXIS') == 'xyz': return vec
    elif config.get('SWAP_AXIS') == 'xzy':
        if len(vec) == 3: return mathutils.Vector( [vec.x, vec.z, vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, vec.x, vec.z, vec.y] )
    elif config.get('SWAP_AXIS') == '-xzy':
        if len(vec) == 3: return mathutils.Vector( [-vec.x, vec.z, vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, -vec.x, vec.z, vec.y] )
    elif config.get('SWAP_AXIS') == 'xz-y':
        if len(vec) == 3: return mathutils.Vector( [vec.x, vec.z, -vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, vec.x, vec.z, -vec.y] )
    else:
        logging.warn( 'unknown swap axis mode %s', config.get('SWAP_AXIS') )
        assert 0

def uid(ob):
    if ob.uid == 0:
        high = 0
        multires = 0
        for o in bpy.data.objects:
            if o.uid > high: high = o.uid
            if o.use_multires_lod: multires += 1
        high += 1 + (multires*10)
        if high < 100: high = 100   # start at 100
        ob.uid = high
    return ob.uid

def timer_diff_str(start):
    return "%0.2f" % (time.time()-start)

def find_bone_index( ob, arm, groupidx): # sometimes the groups are out of order, this finds the right index.
    if groupidx < len(ob.vertex_groups): # reported by Slacker
        vg = ob.vertex_groups[ groupidx ]
        j = 0
        for i,bone in enumerate(arm.pose.bones):
            if not bone.bone.use_deform and config.get('ONLY_DEFORMABLE_BONES'):
                j+=1 # if we skip bones we need to adjust the id
            if bone.name == vg.name:
                return i-j
    else:
        logger.warn('<%s> Object vertex groups (%s) not in sync with armature: %s', ob.name, groupidx, arm.name)

def mesh_is_smooth( mesh ):
    for face in mesh.tessfaces:
        if face.use_smooth: return True

def find_uv_layer_index( uvname, material=None ):
    # This breaks if users have uv layers with same name with different indices over different objects
    idx = 0
    for mesh in bpy.data.meshes:
        if material is None or material.name in mesh.materials:
            if mesh.uv_textures:
                names = [ uv.name for uv in mesh.uv_textures ]
                if uvname in names:
                    idx = names.index( uvname )
                    break # should we check all objects using material and enforce the same index?
    return idx

def has_custom_property( a, name ):
    for prop in a.items():
        n,val = prop
        if n == name:
            return True

def is_strictly_simple_terrain( ob ):
    # A default plane, with simple-subsurf and displace modifier on Z
    if len(ob.data.vertices) != 4 and len(ob.data.tessfaces) != 1:
        return False
    elif len(ob.modifiers) < 2:
        return False
    elif ob.modifiers[0].type != 'SUBSURF' or ob.modifiers[1].type != 'DISPLACE':
        return False
    elif ob.modifiers[0].subdivision_type != 'SIMPLE':
        return False
    elif ob.modifiers[1].direction != 'Z':
        return False # disallow NORMAL and other modes
    else:
        return True

def get_image_textures( mat ):
    r = []
    for s in mat.texture_slots:
        if s and s.texture != None and s.texture.type == 'IMAGE':
            r.append( s )
    return r

def texture_image_path(tex):

    if not tex.image:
        return None

    if tex.library: # support library linked textures
        libpath = split(bpy.path.abspath(tex.library.filepath))[0]
        image_filepath = bpy.path.abspath(tex.image.filepath, libpath)
    else:
        if tex.image.packed_file:
            return tex.image.name + ".png"

        return bpy.path.abspath( tex.image.filepath )

def objects_merge_materials(objs):
    """
    return a list that contains unique material objects
    """
    materials = set()
    for obj in objs:
        for mat in obj.data.materials:
            materials.add(mat)
    return materials

def indent( level, *args ):
    if not args:
        return '    ' * level
    else:
        a = ''
        for line in args:
            a += '    ' * level
            a += line
            a += '\n'
        return a

def gather_instances():
    instances = {}
    for ob in bpy.context.scene.objects:
        if ob.data and ob.data.users > 1:
            if ob.data not in instances:
                instances[ ob.data ] = []
            instances[ ob.data ].append( ob )
    return instances

def select_instances( context, name ):
    for ob in bpy.context.scene.objects:
        ob.select = False
    ob = bpy.context.scene.objects[ name ]
    if ob.data:
        inst = gather_instances()
        for ob in inst[ ob.data ]: ob.select = True
        bpy.context.scene.objects.active = ob

def select_group( context, name, options={} ):
    for ob in bpy.context.scene.objects:
        ob.select = False
    for grp in bpy.data.groups:
        if grp.name == name:
            # context.scene.objects.active = grp.objects
            # Note that the context is read-only. These values cannot be modified directly,
            # though they may be changed by running API functions or by using the data API.
            # So bpy.context.object = obj will raise an error. But bpy.context.scene.objects.active = obj
            # will work as expected. - http://wiki.blender.org/index.php?title=Dev:2.5/Py/API/Intro&useskin=monobook
            bpy.context.scene.objects.active = grp.objects[0]
            for ob in grp.objects:
                ob.select = True
        else:
            pass

def get_objects_using_materials( mats ):
    obs = []
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            for mat in ob.data.materials:
                if mat in mats:
                    if ob not in obs:
                        obs.append( ob )
                    break
    return obs

def get_materials_using_image( img ):
    mats = []
    for mat in bpy.data.materials:
        for slot in get_image_textures( mat ):
            if slot.texture.image == img:
                if mat not in mats:
                    mats.append( mat )
    return mats

def get_parent_matrix( ob, objects ):
    if not ob.parent:
        return mathutils.Matrix(((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)))   # Requiered for Blender SVN > 2.56
    else:
        if ob.parent in objects:
            return ob.parent.matrix_world.copy()
        else:
            return get_parent_matrix(ob.parent, objects)

def merge_group( group ):
    logger.info('+ Merge Group: %s' % group.name )
    copies = []
    copies_meshes = []
    for ob in group.objects:
        if ob.type == 'MESH':
            o2 = ob.copy()
            copies.append( o2 )
            o2.data = o2.to_mesh(bpy.context.scene, True, "PREVIEW") # collaspe modifiers
            copies_meshes.append( o2.data )
            while o2.modifiers:
                o2.modifiers.remove( o2.modifiers[0] )
            bpy.context.scene.objects.link( o2 ) #; o2.select = True

    name = group.name[len("merge."):] if group.name != "merge." else "mergeGroup"

    merged = merge( copies )
    merged.name = name
    merged.data.name = name

    # Clean up orphan meshes
    for copy_mesh in copies_meshes:
        if copy_mesh.name != name:
            logger.debug("Removing temporary mesh: %s" % copy_mesh.name)
            bpy.data.meshes.remove(copy_mesh)

    return merged

def merge_objects( objects, name='_temp_', transform=None ):
    assert objects
    copies = []
    for ob in objects:
        ob.select = False
        if ob.type == 'MESH':
            o2 = ob.copy(); copies.append( o2 )
            o2.data = o2.to_mesh(bpy.context.scene, True, "PREVIEW") # collaspe modifiers
            while o2.modifiers:
                o2.modifiers.remove( o2.modifiers[0] )
            if transform:
                o2.matrix_world = transform * o2.matrix_local
            bpy.context.scene.objects.link( o2 ) #; o2.select = True
    merged = merge( copies )
    merged.name = name
    merged.data.name = name

    return merged

def merge( objects ):
    for ob in bpy.context.selected_objects:
        ob.select = False
    for ob in objects:
        logger.info('  - %s' % ob.name)
        ob.select = True
        assert not ob.library
    bpy.context.scene.objects.active = ob
    bpy.ops.object.join()
    return bpy.context.active_object

def get_merge_group( ob, prefix='merge.' ):
    m = []
    for grp in ob.users_group:
        if grp.name.lower().startswith(prefix): m.append( grp )
    if len(m)==1:
        #if ob.data.users != 1:
        #    logger.warn( 'An instance can not be in a merge group' )
        #    return
        return m[0]
    elif m:
        logger.warn('An object can not be in two merge groups at the same time: %s' % ob.name)
        return

def wordwrap( txt ):
    r = ['']
    for word in txt.split(' '): # do not split on tabs
        word = word.replace('\t', ' '*3)
        r[-1] += word + ' '
        if len(r[-1]) > 90:
            r.append( '' )
    return r

def get_lights_by_type( T ):
    r = []
    for ob in bpy.context.scene.objects:
        if ob.type=='LAMP':
            if ob.data.type==T: r.append( ob )
    return r

invalid_chars_in_name     = '"<>\:' # "<> is xml prohibited, : is Ogre prohibited, \ is standard escape char
invalid_chars_in_filename = '/|?*' + invalid_chars_in_name
invalid_chars_spaces      = ' \t'

def clean_object_name(value, invalid_chars = invalid_chars_in_filename, spaces = True):
    if spaces:
        invalid_chars += invalid_chars_spaces
    
    for invalid_char in invalid_chars:
        value = value.replace(invalid_char, '_')
    return value;

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

class IndentedWriter(object):
    """
    Can be used to write well formed documents.

    w = IndentedWriter()
    with w.word("hello").embed():
        w.indent().word("world").string("!!!").nl()
        with w.word("hello").embed():
            w.iline("schnaps")

    print(w.text)
    > hello {
        world "!!!"
        hello {
          schnaps
        }
      }
    """

    sym_stack = []
    text = ""
    embed_syms = None

    def __init__(self, indent = 0):
        for i in range(indent):
            sym_stack.append(None)

    def __enter__(self, **kwargs):
        begin_sym, end_sym, nl = self.embed_syms
        self.write(begin_sym)
        if nl:
            self.nl()
        self.sym_stack.append(end_sym)

    def __exit__(self, *kwargs):
        sym = self.sym_stack.pop()
        self.indent().write(sym).nl()

    def embed(self, begin_sym="{", end_sym="}", nl=True):
        self.embed_syms = (begin_sym, end_sym, nl)
        return self

    def string(self, text):
        self.write("\"")
        self.write(text)
        self.write("\"")
        return self

    def indent(self, plus=0):
        return self.write("    " * (len(self.sym_stack) + plus))

    def real(self, f):
        return self.word(str(f))

    def integer(self, i):
        return self.word(str(i))

    def nl(self):
        self.write("\n")
        return self

    def write(self, text):
        self.text += text
        return self

    def word(self, text):
        return self.write(str(text)).write(" ")

    def iwrite(self, text):
        return self.indent().write(str(text))

    def iword(self, text):
        return self.indent().word(text)

    def iline(self, text):
        return self.indent().line(text)

    def line(self, text):
        return self.write(text + "\n")

