# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    import importlib
    #print("Reloading modules: shader")
    importlib.reload(shader)

import os, shutil, tempfile, math, logging
from .. import config
from .. import shader
from .. import util
from .. import bl_info
from ..report import Report
from ..util import *
from .program import OgreProgram
from bpy.props import EnumProperty
from bpy_extras import io_utils
from bpy_extras import node_shader_utils
from datetime import datetime
from itertools import chain
from mathutils import Vector
from os.path import join, split, splitext

logger = logging.getLogger('material')

def _write_b2o_ver(fd):
    b2o_ver = ".".join(str(i) for i in bl_info["version"])
    fd.write(bytes('// generated by blender2ogre %s on %s\n' % (b2o_ver, datetime.now().replace(microsecond=0)), 'utf-8'))

def dot_materials(materials, path=None, separate_files=True, prefix='mats', **kwargs):
    """
    generate material files, or copy them into a single file

    path: string - or None if one must use a temp file
    separate_files: bool - each material gets it's own filename
    """
    if not materials:
        logger.warn('No materials, not writting .material script')
        return []

    if not path:
        path = tempfile.mkdtemp(prefix='ogre_io')

    if separate_files:
        for mat in materials:
            dot_material(mat, path)
    else:
        mat_file_name = prefix
        target_file = os.path.join(path, '%s.material' % mat_file_name)
        with open(target_file, 'wb') as fd:
            _write_b2o_ver(fd)
            include_missing = False
            for mat in materials:
                if mat is None:
                    include_missing = True
                    continue
                Report.materials.append( material_name(mat) )
                generator = OgreMaterialGenerator(mat, path)
                # Generate before copying textures to collect images first
                material_text = generator.generate()
                if kwargs.get('copy_programs', config.get('COPY_SHADER_PROGRAMS')):
                    generator.copy_programs()
                if kwargs.get('touch_textures', config.get('TOUCH_TEXTURES')):
                    generator.copy_textures()
                fd.write(bytes(material_text + "\n", 'utf-8'))

            if include_missing:
                fd.write(bytes(MISSING_MATERIAL + "\n", 'utf-8'))

def dot_material(mat, path, **kwargs):
    """
    write the material file of a 
    mat: a blender material
    path: target directory to save the file to

    kwargs: 
      * prefix - string. The prefix name of the file. default ''
      * copy_programs - bool. default False
      * touch_textures - bool. Copy the images along to the material files.
    """
    prefix = kwargs.get('prefix', '')
    generator = OgreMaterialGenerator(mat, path, prefix=prefix)
    # Generate before copying textures to collect images first
    material_text = generator.generate()
    if kwargs.get('copy_programs', config.get('COPY_SHADER_PROGRAMS')):
        generator.copy_programs()
    if kwargs.get('touch_textures', config.get('TOUCH_TEXTURES')):
        generator.copy_textures()
    try:
        mat_file_name = join(path, clean_object_name(generator.material_name) + ".material")
        with open(mat_file_name, 'wb') as fd:
            _write_b2o_ver(fd)
            fd.write(bytes(material_text, 'utf-8'))
    except Exception as e:
        logger.error("Unable to create material file: %s" % mat_file_name)
        logger.error(e)
        Report.errors.append("Unable to create material file: %s" % mat_file_name)

    return generator.material_name

class OgreMaterialGenerator(object):
    # Texture wrapper attribute names
    TEXTURE_KEYS = [
        "base_color_texture",
        "specular_texture",
        "roughness_texture",
        "alpha_texture",
        "normalmap_texture",
        "metallic_texture",
        "emission_color_texture"
    ]

    def __init__(self, material, target_path, prefix=''):
        self.material = material
        self.target_path = target_path
        self.w = util.IndentedWriter()
        self.passes = []
        if self.material is None:
            self.material_name = "_missing_material_"
        else:
            self.material_name = material_name(self.material, prefix=prefix)
        self.images = set()

        if (self.material is not None and 
            material.node_tree is not None):
            nodes = shader.get_subnodes( self.material.node_tree, type='MATERIAL_EXT' )
            for node in nodes:
                if node.material:
                    self.passes.append( node.material )

    def generate(self):
        if self.material is None:
            return MISSING_MATERIAL

        self.generate_header()
        with self.w.iword('material').word(self.material_name).embed():
            if self.material.shadow_method != "NONE":
                self.w.iline('receive_shadows on')
            else:
                self.w.iline('receive_shadows off')
            with self.w.iword('technique').embed():
                self.generate_passes()

        text = self.w.text
        self.w.text = ''
        return text

    def generate_header(self):
        for mat in self.passes:
            if mat.use_ogre_parent_material and mat.ogre_parent_material:
                usermat = get_ogre_user_material( mat.ogre_parent_material )
                self.w.iline( '// user material: %s' %usermat.name )
                # TODO: fix what is r
#                 for prog in usermat.get_programs():
#                     r.append( prog.data )
                self.w.iline( '// abstract passes //' )
                for line in usermat.as_abstract_passes():
                    self.w.iline(line)

    def generate_passes(self):
        self.generate_pass(self.material)
        for mat in self.passes:
            if mat.use_in_ogre_material_pass: # submaterials
                self.generate_pass(mat)

    def generate_pass( self, mat, pass_name="" ):
        usermat = texnodes = None
        if mat.use_ogre_parent_material:
            usermat = get_ogre_user_material( mat.ogre_parent_material )
            texnodes = shader.get_texture_subnodes( self.material, mat )

        if usermat:
            self.w.iword('pass %s : %s/PASS0' %(pass_name,usermat.name))
        else:
            self.w.iword('pass')
            if pass_name: self.w.word(pass_name)

        with self.w.embed():
            # Texture wrappers
            textures = {}
            mat_wrapper = node_shader_utils.PrincipledBSDFWrapper(mat)
            for tex_key in self.TEXTURE_KEYS:
                texture = getattr(mat_wrapper, tex_key, None)
                # In the case of the Metallic and Roughness textures, they cannot be obtained using "node_shader_utils"
                # https://docs.blender.org/manual/en/2.80/addons/io_scene_gltf2.html#metallic-and-roughness
                if tex_key == 'roughness_texture':
                    texture = gather_metallic_roughness_texture(mat_wrapper)
                if texture and texture.image:
                    textures[tex_key] = texture
                    # adds image to the list for later copy
                    self.images.add(texture.image)

            color = mat_wrapper.base_color
            alpha = 1.0
            if mat.blend_method == "CLIP":
                alpha = mat_wrapper.alpha
                self.w.iword('alpha_rejection greater_equal').round(255*mat.alpha_threshold).nl()
            elif mat.blend_method != "OPAQUE":
                alpha = mat_wrapper.alpha
                self.w.iword('scene_blend alpha_blend').nl()
                if mat.show_transparent_back:
                    self.w.iword('cull_hardware none').nl()
                    self.w.iword('depth_write off').nl()

            if config.get('USE_FFP_PARAMETERS') is True:
                # arbitrary bad translation from PBR to Blinn Phong
                # derive proportions from metallic
                bf = 1.0 - mat_wrapper.metallic
                mf = max(0.04, mat_wrapper.metallic)
                # derive specular color
                sc = mathutils.Color(color[:3]) * mf + (1.0 - mf) * mathutils.Color((1, 1, 1)) * (1.0 - mat_wrapper.roughness)
                si = (1.0 - mat_wrapper.roughness) * 128

                self.w.iword('diffuse').round(color[0]*bf).round(color[1]*bf).round(color[2]*bf).round(alpha).nl()
                self.w.iword('specular').round(sc[0]).round(sc[1]).round(sc[2]).round(alpha).round(si, 3).nl()
            else:
                self.w.iword('diffuse').round(color[0]).round(color[1]).round(color[2]).round(alpha).nl()
                self.w.iword('specular').round(mat_wrapper.roughness).round(mat_wrapper.metallic).real(0).real(0).real(0).nl()
                self.generate_rtshader_system(textures)

            for name in dir(mat):   #mat.items() - items returns custom props not pyRNA:
                if name.startswith('ogre_') and name != 'ogre_parent_material':
                    var = getattr(mat,name)
                    op = name.replace('ogre_', '')
                    val = var
                    if type(var) == bool:
                        if var: val = 'on'
                        else: val = 'off'
                    self.w.iword(op).word(val).nl()

            if texnodes and usermat.texture_units:
                for i,name in enumerate(usermat.texture_units_order):
                    if i<len(texnodes):
                        node = texnodes[i]
                        if node.texture:
                            geo = shader.get_connected_input_nodes( self.material, node )[0]
                            # self.generate_texture_unit( node.texture, name=name, uv_layer=geo.uv_layer )
                            raise NotImplementedError("TODO: slots dont exist anymore - use image")
            elif textures:
                for key, texture in textures.items():
                    self.generate_texture_unit(key, texture)

    def generate_rtshader_system(self, textures):
        """
        Generates the rtshader_system section of a pass.

        textures: dictionary with all the textures
        """
        self.w.nl()
        self.w.iword('// additional maps - requires RTSS').nl()

        with self.w.iword('rtshader_system').embed():
            for key, texture in textures.items():
                image = texture.image
                target_filepath = split(image.filepath or image.name)[1]
                filename = self.change_ext(target_filepath, image)

                if key == "normalmap_texture":
                    self.w.iword('lighting_stage normal_map').word(filename).nl()
                elif key == "roughness_texture":
                    self.w.iword('lighting_stage metal_roughness texture').word(filename).nl()

            # If there was no 'roughness_texture', this switches the lighting equations from Blinn-Phong to the Cook-Torrance PBR model
            if 'roughness_texture' not in textures:
                self.w.iline('lighting_stage metal_roughness')

            if 'emission_color_texture' in textures:
                self.w.iword('texturing_stage late_add_blend // needed for emissive to work').nl()

    def generate_texture_unit(self, key, texture):
        """
        Generates a texture_unit of a pass.

        key: key of the texture in the material shader (not used, for normal if needed)
        texture: the material texture
        """
        #src_dir = os.path.dirname(bpy.data.filepath)
        # For target path relative
        # dst_dir = os.path.dirname(self.target_path)
        #dst_dir = src_dir
        #filename = io_utils.path_reference(texture.image.filepath, src_dir, dst_dir, mode='RELATIVE', library=texture.image.library)
        # Do not use if target path relative
        # filename = repr(filepath)[1:-1]
        #_, filename = split(filename)
        #filename = self.change_ext(filename, texture.image)

        # Use same filename as: copy_texture()
        image = texture.image
        target_filepath = split(image.filepath or image.name)[1]
        filename = self.change_ext(target_filepath, image)

        # These textures are processed in generate_rtshader_system()
        if key in ("normalmap_texture", "roughness_texture"):
            return

        self.w.nl()

        if not key in ("base_color_texture", "emission_color_texture"):
            self.w.iword('// Don\'t know how to export:').word(key).word(filename).nl()
            return
        else:
            self.w.iword('// -').word(key).nl()

        with self.w.iword('texture_unit').embed():
            self.w.iword('texture').word(filename).nl()

            exmode = texture.extension
            if exmode in TEXTURE_ADDRESS_MODE:
                self.w.iword('tex_address_mode').word(TEXTURE_ADDRESS_MODE[exmode]).nl()

            if exmode == 'CLIP':
                r,g,b = texture.node_image.color_mapping.blend_color
                self.w.iword('tex_border_colour').round(r).round(g).round(b).nl()
            x,y = texture.scale[0:2]
            if x != 1 or y != 1:
                self.w.iword('scale').round(1.0 / x).round(1.0 / y).nl()

            if texture.texcoords == 'Reflection':
                if texture.projection == 'SPHERE':
                    self.w.iline('env_map spherical')
                elif texture.projection == 'FLAT':
                    self.w.iline('env_map planar')
                else: 
                    logger.warn('Texture: <%s> has a non-UV mapping type (%s) and not picked a proper projection type of: Sphere or Flat' % (texture.name, slot.mapping))

            x,y = texture.translation[0:2]
            if x or y:
                self.w.iword('scroll').round(x).round(y).nl()
            if texture.rotation.z:
                # Radians to degrees
                self.w.iword('rotate').round(math.degrees(texture.rotation.z), 2).nl()
 
            btype = 'modulate'
            if key == "emission_color_texture":
                btype = "add"

            self.w.iword('colour_op').word(btype).nl()

    def copy_textures(self):
        for image in self.images:
            self.copy_texture(image)

    def copy_texture(self, image):
        origin_filepath = image.filepath
        target_filepath = split(origin_filepath or image.name)[1]
        target_filepath = self.change_ext(target_filepath, image)
        target_filepath = join(self.target_path, target_filepath)

        if image.packed_file:
            # packed in .blend file, save image as target file
            image.filepath = target_filepath
            image.save()
            image.filepath = origin_filepath
            logger.info("Writing texture: (%s)", target_filepath)
        else:
            image_filepath = bpy.path.abspath(image.filepath, library=image.library)
            image_filepath = os.path.normpath(image_filepath)
            
            # Should we update the file
            update = False
            if os.path.isfile(target_filepath):
                src_stat = os.stat(target_filepath)
                dst_stat = os.stat(image_filepath)
                update = src_stat.st_size != dst_stat.st_size \
                    or src_stat.st_mtime != dst_stat.st_mtime
            else:
                update = True

            if update:
                if is_image_postprocessed(image):
                    logger.info("ImageMagick: (%s) -> (%s)", image_filepath, target_filepath)
                    util.image_magick(image, image_filepath, target_filepath)
                else:
                    # copy2 tries to copy all metadata (modification date included), to keep update decision consistent
                    shutil.copy2(image_filepath, target_filepath)
                    logger.info("Copying image: (%s)", origin_filepath)
            else:
                logger.info("Skip copying (%s). Texture is already up to date.", origin_filepath)

    def get_active_programs(self):
        r = []
        for mat in self.passes:
            if mat.use_ogre_parent_material and mat.ogre_parent_material:
                usermat = get_ogre_user_material( mat.ogre_parent_material )
                for prog in usermat.get_programs(): r.append( prog )
        return r

    def copy_programs(self):
        for prog in self.get_active_programs():
            if prog.source:
                prog.save(self.target_path)
            else:
                logger.warn('Uses program %s which has no source' % prog.name)

    def change_ext( self, name, image ):
        name_no_ext, _ = splitext(name)
        if image.file_format != 'NONE':
            name = name_no_ext + "." + image.file_format.lower()
        if config.get('FORCE_IMAGE_FORMAT') != 'NONE':
            name = name_no_ext + "." + config.get('FORCE_IMAGE_FORMAT')
        return name

# Make default material for missing materials:
# * Red flags for users so they can quickly see what they forgot to assign a material to.
# * Do not crash if no material on object - thats annoying for the user.
TEXTURE_COLOUR_OP = {
    'MIX'       : 'modulate',   # Ogre Default - was "replace" but that kills lighting
    'ADD'       : 'add',
    'MULTIPLY'  : 'modulate',
    #'alpha_blend' : '',
}
TEXTURE_COLOUR_OP_EX = {
    'MIX'       : 'blend_manual',
    'SCREEN'    : 'modulate_x2',
    'LIGHTEN'   : 'modulate_x4',
    'SUBTRACT'  : 'subtract',
    'OVERLAY'   : 'add_signed',
    'DIFFERENCE': 'dotproduct', # best match?
    'VALUE'     : 'blend_diffuse_colour',
}

TEXTURE_ADDRESS_MODE = {
    'REPEAT'    : 'wrap',
    'EXTEND'    : 'clamp',
    'CLIP'      : 'border',
    'CHECKER'   : 'mirror'
}

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

def load_user_materials():
    # I think this is solely used for realXtend...
    # the config of USER_MATERIAL points to a subdirectory of tundra by default.
    # In this case all parsing can be moved to the tundra subfolder

    # Exit this function if the path is empty. Allows 'USER_MATERIALS' to be blank and not affect anything.
    # If 'USER_MATERIALS' is something too broad like "C:\\" it recursively scans it and might crash if it
    # hits directories it doesn't have access too
    if config.get('USER_MATERIALS') == '':
        return

    try:
        if os.path.isdir( config.get('USER_MATERIALS') ):
            scripts,progs = update_parent_material_path( config.get('USER_MATERIALS') )
            for prog in progs:
                logger.info('Ogre shader program: %s' % prog.name)
    except Exception as e:
        logger.warn("Unable to parse 'USER_MATERIALS' directory: %s" % config.get('USER_MATERIALS'))
        logger.warn(e)


def material_name( mat, clean = False, prefix='' ):
    """
    returns the material name.

    materials from a library might be exported several times for multiple objects.
    there is no need to have those textures + material scripts several times. thus
    library materials are prefixed with the material filename. (e.g. test.blend + diffuse
    should result in "test_diffuse". special chars are converted to underscore.

    clean: deprecated. do not use!
    """
    if type(mat) is str:
        return prefix + clean_object_name(mat, invalid_chars=invalid_chars_in_name)
    name = clean_object_name(mat.name, invalid_chars=invalid_chars_in_name)
    if mat.library:
        _, filename = split(mat.library.filepath)
        prefix, _ = splitext(filename)
        return prefix + "_" + name
    else:
        return prefix + name

def get_shader_program( name ):
    if name in OgreProgram.PROGRAMS:
        return OgreProgram.PROGRAMS[ name ]
    else:
        logger.warn('No shader program named: %s' % name)

def get_shader_programs():
    return OgreProgram.PROGRAMS.values()

def parse_material_and_program_scripts( path, scripts, progs, missing ):   # recursive

    for name in os.listdir(path):
        url = os.path.join(path, name)
        if os.path.isdir( url ):
            parse_material_and_program_scripts( url, scripts, progs, missing )

        elif os.path.isfile( url ):
            if name.endswith('.material'):
                logger.debug('<found material> %s' % url )
                scripts.append( MaterialScripts( url ) )

            if name.endswith('.program'):
                logger.debug('<found program> %s' % url )
                data = open( url, 'rb' ).read().decode('utf-8')

                chk = []; chunks = [ chk ]
                for line in data.splitlines():
                    line = line.split('//')[0]
                    if line.startswith('}'):
                        chk.append( line )
                        chk = []; chunks.append( chk )
                    elif line.strip():
                        chk.append( line )

                for chk in chunks:
                    if not chk: continue
                    p = OgreProgram( data='\n'.join(chk) )
                    if p.source:
                        ok = p.reload()
                        if not ok: missing.append( p )
                        else: progs.append( p )

def get_ogre_user_material( name ):
    if name in MaterialScripts.ALL_MATERIALS:
        return MaterialScripts.ALL_MATERIALS[ name ]

class OgreMaterialScript(object):
    def get_programs(self):
        progs = []
        for name in list(self.vertex_programs.keys()) + list(self.fragment_programs.keys()):
            p = get_shader_program( name )  # OgreProgram.PROGRAMS
            if p: progs.append( p )
        return progs

    def __init__(self, txt, url):
        self.url = url
        self.data = txt.strip()
        self.parent = None
        self.vertex_programs = {}
        self.fragment_programs = {}
        self.texture_units = {}
        self.texture_units_order = []
        self.passes = []

        line = self.data.splitlines()[0]
        assert line.startswith('material')
        if ':' in line:
            line, self.parent = line.split(':')
        self.name = line.split()[-1]
        logger.debug('New ogre material: %s' % self.name )

        brace = 0
        self.techniques = techs = []
        prog = None # pick up program params
        tex = None  # pick up texture_unit options, require "texture" ?
        for line in self.data.splitlines():
            #logger.debug( line )
            rawline = line
            line = line.split('//')[0]
            line = line.strip()
            if not line: continue

            if line == '{': brace += 1
            elif line == '}': brace -= 1; prog = None; tex = None

            if line.startswith('technique'):
                tech = {'passes':[]}; techs.append( tech )
                if len(line.split()) > 1: tech['technique-name'] = line.split()[-1]
            elif techs:
                if line.startswith('pass'):
                    P = {'texture_units':[], 'vprogram':None, 'fprogram':None, 'body':[]}
                    tech['passes'].append( P )
                    self.passes.append( P )

                elif tech['passes']:
                    P = tech['passes'][-1]
                    P['body'].append( rawline )

                    if line == '{' or line == '}': continue

                    if line.startswith('vertex_program_ref'):
                        prog = P['vprogram'] = {'name':line.split()[-1], 'params':{}}
                        self.vertex_programs[ prog['name'] ] = prog
                    elif line.startswith('fragment_program_ref'):
                        prog = P['fprogram'] = {'name':line.split()[-1], 'params':{}}
                        self.fragment_programs[ prog['name'] ] = prog

                    elif line.startswith('texture_unit'):
                        prog = None
                        tex = {'name':line.split()[-1], 'params':{}}
                        if tex['name'] == 'texture_unit': # ignore unnamed texture units
                            logger.warn('Material %s contains unnamed texture_units' % self.name)
                            logger.warn('--- Unnamed texture units will be ignored ---')
                        else:
                            P['texture_units'].append( tex )
                            self.texture_units[ tex['name'] ] = tex
                            self.texture_units_order.append( tex['name'] )

                    elif prog:
                        p = line.split()[0]
                        if p=='param_named':
                            items = line.split()
                            if len(items) == 4: p, o, t, v = items
                            elif len(items) == 3:
                                p, o, v = items
                                t = 'class'
                            elif len(items) > 4:
                                o = items[1]; t = items[2]
                                v = items[3:]

                            opt = { 'name': o, 'type':t, 'raw_value':v }
                            prog['params'][ o ] = opt
                            if t=='float': opt['value'] = float(v)
                            elif t in 'float2 float3 float4'.split(): opt['value'] = [ float(a) for a in v ]
                            else: logger.debug('Unknown type: %s' % t)

                    elif tex:   # (not used)
                        tex['params'][ line.split()[0] ] = line.split()[ 1 : ]

        for P in self.passes:
            lines = P['body']
            while lines and ''.join(lines).count('{')!=''.join(lines).count('}'):
                if lines[-1].strip() == '}': lines.pop()
                else: break
            P['body'] = '\n'.join( lines )
            assert P['body'].count('{') == P['body'].count('}')     # if this fails, the parser choked

        #logger.debug( self.techniques )
        self.hidden_texture_units = rem = []
        for tex in self.texture_units.values():
            if 'texture' not in tex['params']:
                rem.append( tex )
        for tex in rem:
            logger.warn('Not using texture_unit <%s> because it lacks a "texture" parameter' % tex['name'])
            self.texture_units.pop( tex['name'] )

        if len(self.techniques)>1:
            logger.warn('User material %s has more than one technique' % self.url)

    def as_abstract_passes( self ):
        r = []
        for i,P in enumerate(self.passes):
            head = 'abstract pass %s/PASS%s' %(self.name,i)
            r.append( head + '\n' + P['body'] )
        return r

class MaterialScripts(object):
    ALL_MATERIALS = {}
    ENUM_ITEMS = []

    def __init__(self, url):
        self.url = url
        self.data = ''
        data = open( url, 'rb' ).read()
        try:
            self.data = data.decode('utf-8')
        except:
            self.data = data.decode('latin-1')

        self.materials = {}
        ## chop up .material file, find all material defs ####
        mats = []
        mat = []
        skip = False    # for now - programs must be defined in .program files, not in the .material
        for line in self.data.splitlines():
            if not line.strip(): continue
            a = line.split()[0]             #NOTE ".split()" strips white space
            if a == 'material':
                mat = []; mats.append( mat )
                mat.append( line )
            elif a in ('vertex_program', 'fragment_program', 'abstract'):
                skip = True
            elif mat and not skip:
                mat.append( line )
            elif skip and line=='}':
                skip = False

        ##########################
        for mat in mats:
            omat = OgreMaterialScript('\n'.join( mat ), url )
            if omat.name in self.ALL_MATERIALS:
                logger.warn('Material %s redefined' % omat.name )
                #logger.debug('--- OLD MATERIAL ---')
                #logger.debug( self.ALL_MATERIALS[ omat.name ].data )
                #logger.debug('--- NEW MATERIAL ---')
                #logger.debug( omat.data )
            self.materials[ omat.name ] = omat
            self.ALL_MATERIALS[ omat.name ] = omat
            if omat.vertex_programs or omat.fragment_programs:  # ignore materials without programs
                self.ENUM_ITEMS.append( (omat.name, omat.name, url) )

    @classmethod # only call after parsing all material scripts
    def reset_rna(self, callback=None):
        bpy.types.Material.ogre_parent_material = EnumProperty(
            name="Script Inheritence",
            description='OGRE parent material class',
            items=self.ENUM_ITEMS,
            #update=callback
        )

IMAGE_FORMATS =  [
    ('NONE','NONE', 'Do not convert image'),
    ('bmp', 'bmp', 'Bitmap format'),
    ('jpg', 'jpg', 'JPEG format'),
    ('gif', 'gif', 'GIF format'),
    ('png', 'png', 'PNG format'),
    ('tga', 'tga', 'Targa format'),
    ('dds', 'dds', 'DDS format'),
]

def is_image_postprocessed( image ):
    if config.get('FORCE_IMAGE_FORMAT') != 'NONE':
        return True
    else:
        return False


def update_parent_material_path( path ):
    ''' updates RNA '''
    logger.debug('>> SEARCHING FOR OGRE MATERIALS: %s' % path )
    scripts = []
    progs = []
    missing = []
    parse_material_and_program_scripts( path, scripts, progs, missing )

    if missing:
        logger.warn('Missing shader programs:')
        for p in missing: logger.debug(p.name)
    if missing and not progs:
        logger.warn('No shader programs were found - set "SHADER_PROGRAMS" to your path')

    MaterialScripts.reset_rna( callback=shader.on_change_parent_material )
    return scripts, progs

class ShaderImageTextureWrapper():
    """
    This class imitates the namesake Class from the library: node_shader_utils.
    The objective is that the Metallic Roughness Texture follows the same codepath as the other textures
    """

    def __init__(self, node_image):
        self.image = node_image.image
        self.extension = node_image.extension
        self.node_image = node_image
        #self.name = ??
        self.texcoords = 'UV'
        self.projection = node_image.projection
        self.scale = self.get_mapping_input('Scale')
        self.translation = self.get_mapping_input('Location')
        self.rotation = self.get_mapping_input('Rotation')

    # Esta funcion obtiene los datos de un nodo de tipo: Mapping
    def get_mapping_input(self, input):
        if len(self.node_image.inputs['Vector'].links) > 0:
            node_mapping = self.node_image.inputs['Vector'].links[0].from_node

            if node_mapping.type == 'MAPPING':
                return node_mapping.inputs[input].default_value
            else:
                logger.warn("Connected node: %s is not of type 'MAPPING'" % node_mapping.name)
                return None
        else:
            return None

def gather_metallic_roughness_texture(mat_wrapper):
    """
    For a given material, retrieve the corresponding metallic roughness texture according to glTF2 guidelines.
    (https://docs.blender.org/manual/en/2.80/addons/io_scene_gltf2.html#metallic-and-roughness)
    :param blender_material: a blender material for which to get the metallic roughness texture
    :return: a blender Image
    """
    material = mat_wrapper.material

    logger.debug("Getting Metallic roughness texture of material: '%s'" % material.name)

    separate_name = None
    #image_texture = None
    node_image = None

    for input_name in ['Roughness', 'Metallic']:
        logger.debug(" + Processing input: '%s'" % input_name)

        if material.use_nodes == False:
            logger.warn("Material: '%s' does not use nodes" % material.name)
            return None

        if 'Principled BSDF' not in  material.node_tree.nodes:
            logger.warn("Material: '%s' does not have a 'Principled BSDF' node" % material.name)
            return None

        input = material.node_tree.nodes['Principled BSDF'].inputs[input_name]

        # Check that input is connected to a node
        if len(input.links) > 0:
            separate_node = input.links[0].from_node
        else:
            logger.warn("%s input is not connected" % input_name)
            return None

        # Check that connected node is of type 'SEPARATE_COLOR'
        if separate_node.type not in ['SEPARATE_COLOR', 'SEPRGB']:
            logger.warn("Connected node '%s' is not of type 'SEPARATE_COLOR'" % separate_node.name)
            return None

        # Check that both inputs are connected to the same 'SEPARATE_COLOR' node (node names are unique)
        if separate_name == None:
            separate_name = separate_node.name
        elif separate_name != separate_node.name:
            logger.warn("Connected node '%s' is different between 'Roughness' and 'Metallic' inputs" % separate_node.name)
            return None

        # Check that 'Roughness' is connected to 'Green' output and 'Metallic' is connected to 'Blue' output
        if input_name == 'Roughness' and input.links[0].from_socket.name not in ['Green', 'G']:
            logger.warn("'Roughness' input connected to wrong output of node: '%s'" % separate_node.name)
            return None
        elif input_name == 'Metallic' and input.links[0].from_socket.name not in ['Blue', 'B']:
            logger.warn("'Metallic' input connected to wrong output of node: '%s'" % separate_node.name)
            return None

        # Check that input is connected to a node
        if len(separate_node.inputs[0].links) == 0:
            logger.warn("node '%s' has no input texture" % separate_node.name)
            return None

        # Get the image texture
        node_image = separate_node.inputs[0].links[0].from_node
        if node_image.type != 'TEX_IMAGE':
            logger.warn("Node connected to '%s' is not of type: 'TEX_IMAGE'" % separate_node.name)
            return None

    return ShaderImageTextureWrapper(node_image)
