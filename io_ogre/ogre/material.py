from datetime import datetime
import os
from os.path import join
from ..util import *
from .. import util
from .. import config
from .. import shader
from ..report import Report
import tempfile
import shutil

def dot_materials(self, materials, path=None, separate_files=True):
    """
    generate material files, or copy them into a single file

    path: string - or None if one must use a temp file
    separate_files: bool - each material gets it's own filename

    """
    if not materials:
        print('WARNING: no materials, not writting .material script')
        return []

    if not path:
        path = tempfile.mkdtemp(prefix='ogre_io')

    M = MISSING_MATERIAL + '\n'
    for mat in materials:
        if mat is None:
            continue
        Report.materials.append( material_name(mat) )
        data = generate_material( mat, path=path,
                copy_programs=config.get('COPY_SHADER_PROGRAMS'),
                touch_textures=config.get('TOUCH_TEXTURES') )

        M += data
        # Write own .material file per material
        if separate_files:
            url = self.dot_material_write_separate( mat, data, path )
            material_files.append(url)

    # Write one .material file for everything
    if not separate_files:
        try:
            url = os.path.join(path, '%s.material' % mat_file_name)
            with open(url, 'wb') as fd: 
                fd.write(bytes(M,'utf-8'))
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



def dot_material(obj, path, **kwargs):
    """
    write the material file of a
    obj: a blender object that has a mesh
    path: target directory to save the file to

    kwargs: 
      * prefix - string. The prefix name of the file. default ''
      * copy_programs - bool. default False
      * touch_textures - bool. Copy the images along to the material files.
    """
    prefix = kwargs.get('prefix', '')
    for material in obj.data.materials:
        material_text = generate_material(material, path, **kwargs)
        mat_name = material_name(material, prefix=prefix) + '.material'
        with open(join(path, mat_name), 'wb') as fd:
            fd.write(bytes(material_text,'utf-8'))
        yield mat_name

    if kwargs.get('copy_materials', False):
        _copy_materials(obj.data.materials, path)

def _copy_materials(materials, path):
    pass
# Make default material for missing materials:
# * Red flags for users so they can quickly see what they forgot to assign a material to.
# * Do not crash if no material on object - thats annoying for the user.
TEXTURE_COLOUR_OP = {
    'MIX'       :   'modulate',        # Ogre Default - was "replace" but that kills lighting
    'ADD'     :   'add',
    'MULTIPLY' : 'modulate',
    #'alpha_blend' : '',
}
TEXTURE_COLOUR_OP_EX = {
    'MIX'       :    'blend_manual',
    'SCREEN': 'modulate_x2',
    'LIGHTEN': 'modulate_x4',
    'SUBTRACT': 'subtract',
    'OVERLAY':    'add_signed',
    'DIFFERENCE': 'dotproduct',        # best match?
    'VALUE': 'blend_diffuse_colour',
}

TEXTURE_ADDRESS_MODE = {
    'REPEAT': 'wrap',
    'EXTEND': 'clamp',
    'CLIP'  : 'border',
    'CHECKER' : 'mirror'
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
    # I think this is soley used for realxtend... the config of USER_MATERIAL
    # points to a subdirectory of tundra by default. In this case all parsing
    # can be moved to the tundra subfolder
    if os.path.isdir( config.get('USER_MATERIALS') ):
        scripts,progs = update_parent_material_path( config.get('USER_MATERIALS') )
        for prog in progs:
            logging.info('Ogre shader program', prog.name)
    #else:
    #    logging.warn('Invalid my-shaders path %s' % config.get('USER_MATERIALS'))


def material_name( mat, clean = False, prefix='' ):
    if type(mat) is str:
        return prefix + mat
    elif not mat.library:
        return prefix + mat.name
    else:
        if clean:
            return prefix + clean_object_name(mat.name + mat.library.filepath.replace('/','_'))
        else:
            return prefix + clean_object_name(mat.name)

def generate_material(mat, path='/tmp', copy_programs=False, touch_textures=False, **kwargs):
    ''' returns generated material string '''

    prefix = kwargs.get('prefix','')
    safename = material_name(mat,prefix=prefix) # supports blender library linking
    w = util.IndentedWriter()
    w.line('// %s generated by blender2ogre %s' % (mat.name, datetime.now())).nl()

    with w.iword('material').word(safename).embed():
        if mat.use_shadows:
            w.iline('receive_shadows on')
        else:
            w.iline('receive_shadows off')

        with w.iword('technique').embed():
            g = OgreMaterialGenerator(mat, path=path, touch_textures=touch_textures)

            if copy_programs:
                progs = g.get_active_programs()
                for prog in progs:
                    if prog.source:
                        prog.save(path)
                    else:
                        print( '[WARNING}: material %s uses program %s which has no source' % (mat.name, prog.name) )

            header = g.get_header()
            passes = g.get_passes()

            w.write('\n'.join(passes))

    if len(header) > 0:
        return header + '\n' + w.text
    else:
        return w.text

def get_shader_program( name ):
    if name in OgreProgram.PROGRAMS:
        return OgreProgram.PROGRAMS[ name ]
    else:
        print('WARNING: no shader program named: %s' %name)

def get_shader_programs():
    return OgreProgram.PROGRAMS.values()

def parse_material_and_program_scripts( path, scripts, progs, missing ):   # recursive
    for name in os.listdir(path):
        url = os.path.join(path,name)
        if os.path.isdir( url ):
            parse_material_and_program_scripts( url, scripts, progs, missing )

        elif os.path.isfile( url ):
            if name.endswith( '.material' ):
                print( '<found material>', url )
                scripts.append( MaterialScripts( url ) )

            if name.endswith('.program'):
                print( '<found program>', url )
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
        print( 'new ogre material: %s' %self.name )

        brace = 0
        self.techniques = techs = []
        prog = None  # pick up program params
        tex = None  # pick up texture_unit options, require "texture" ?
        for line in self.data.splitlines():
            #print( line )
            rawline = line
            line = line.split('//')[0]
            line = line.strip()
            if not line: continue

            if line == '{': brace += 1
            elif line == '}': brace -= 1; prog = None; tex = None

            if line.startswith( 'technique' ):
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
                            print('WARNING: material %s contains unnamed texture_units' %self.name)
                            print('---unnamed texture units will be ignored---')
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
                            else: print('unknown type:', t)

                    elif tex:   # (not used)
                        tex['params'][ line.split()[0] ] = line.split()[ 1 : ]

        for P in self.passes:
            lines = P['body']
            while lines and ''.join(lines).count('{')!=''.join(lines).count('}'):
                if lines[-1].strip() == '}': lines.pop()
                else: break
            P['body'] = '\n'.join( lines )
            assert P['body'].count('{') == P['body'].count('}')     # if this fails, the parser choked

        #print( self.techniques )
        self.hidden_texture_units = rem = []
        for tex in self.texture_units.values():
            if 'texture' not in tex['params']:
                rem.append( tex )
        for tex in rem:
            print('WARNING: not using texture_unit because it lacks a "texture" parameter', tex['name'])
            self.texture_units.pop( tex['name'] )

        if len(self.techniques)>1:
            print('WARNING: user material %s has more than one technique' %self.url)

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
            omat = OgreMaterialScript( '\n'.join( mat ), url )
            if omat.name in self.ALL_MATERIALS:
                print( 'WARNING: material %s redefined' %omat.name )
                #print( '--OLD MATERIAL--')
                #print( self.ALL_MATERIALS[ omat.name ].data )
                #print( '--NEW MATERIAL--')
                #print( omat.data )
            self.materials[ omat.name ] = omat
            self.ALL_MATERIALS[ omat.name ] = omat
            if omat.vertex_programs or omat.fragment_programs:  # ignore materials without programs
                self.ENUM_ITEMS.append( (omat.name, omat.name, url) )

    @classmethod # only call after parsing all material scripts
    def reset_rna(self, callback=None):
        bpy.types.Material.ogre_parent_material = EnumProperty(
            name="Script Inheritence",
            description='ogre parent material class',
            items=self.ENUM_ITEMS,
            #update=callback
        )

IMAGE_FORMATS =  [
    ('NONE','NONE', 'do not convert image'),
    ('bmp', 'bmp', 'bitmap format'),
    ('jpg', 'jpg', 'jpeg format'),
    ('gif', 'gif', 'gif format'),
    ('png', 'png', 'png format'),
    ('tga', 'tga', 'targa format'),
    ('dds', 'dds', 'nvidia dds format'),
]

def is_image_postprocessed( image ):
    if CONFIG['FORCE_IMAGE_FORMAT'] != 'NONE' or image.use_resize_half or image.use_resize_absolute or image.use_color_quantize or image.use_convert_format:
        return True
    else:
        return False

class _image_processing_( object ):
    def _reformat( self, name, image ):
        if image.convert_format != 'NONE':
            name = '%s.%s' %(name[:name.rindex('.')], image.convert_format)
            if image.convert_format == 'dds': name = '_DDS_.%s' %name
        elif image.use_resize_half or image.use_resize_absolute or image.use_color_quantize or image.use_convert_format:
            name = '_magick_.%s' %name
        if CONFIG['FORCE_IMAGE_FORMAT'] != 'NONE' and not name.endswith('.dds'):
            name = '%s.%s' %(name[:name.rindex('.')], CONFIG['FORCE_IMAGE_FORMAT'])
            if CONFIG['FORCE_IMAGE_FORMAT'] == 'dds':
                name = '_DDS_.%s' %name
        return name

    def image_magick( self, texture, infile ):
        print('IMAGE MAGICK', infile )
        exe = CONFIG['IMAGE_MAGICK_CONVERT']
        if not os.path.isfile( exe ):
            Report.warnings.append( 'ImageMagick not installed!' )
            print( 'ERROR: can not find Image Magick - convert', exe ); return
        cmd = [ exe, infile ]
        ## enforce max size ##
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

        elif x > CONFIG['MAX_TEXTURE_SIZE'] or y > CONFIG['MAX_TEXTURE_SIZE']:
            cmd.append( '-resize' )
            cmd.append( str(CONFIG['MAX_TEXTURE_SIZE']) )

        if texture.image.use_color_quantize:
            if texture.image.use_color_quantize_dither:
                cmd.append( '+dither' )
            cmd.append( '-colors' )
            cmd.append( str(texture.image.color_quantize) )

        path,name = os.path.split( infile )
        #if (texture.image.use_convert_format and texture.image.convert_format == 'dds') or CONFIG['FORCE_IMAGE_FORMAT'] == 'dds':
        outfile = os.path.join( path, self._reformat(name,texture.image) )
        if outfile.endswith('.dds'):
            temp = os.path.join( path, '_temp_.png' )
            cmd.append( temp )
            print( 'IMAGE MAGICK: %s' %cmd )
            subprocess.call( cmd )
            self.nvcompress( texture, temp, outfile=outfile )

        else:
            cmd.append( outfile )
            print( 'IMAGE MAGICK: %s' %cmd )
            subprocess.call( cmd )

    def nvcompress(self, texture, infile, outfile=None, version=1, fast=False, blocking=True):
        print('[NVCompress DDS Wrapper]', infile )
        assert version in (1,2,3,4,5)
        exe = CONFIG['NVCOMPRESS']
        cmd = [ exe ]

        if texture.image.use_alpha and texture.image.depth==32:
            cmd.append( '-alpha' )
        if not texture.use_mipmap:
            cmd.append( '-nomips' )

        if texture.use_normal_map:
            cmd.append( '-normal' )
            if version in (1,3):
                cmd.append( '-bc%sn' %version )
            else:
                cmd.append( '-bc%s' %version )
        else:
            cmd.append( '-bc%s' %version )

        if fast:
            cmd.append( '-fast' )
        cmd.append( infile )

        if outfile: cmd.append( outfile )

        print( cmd )
        if blocking:
            subprocess.call( cmd )
        else:
            subprocess.Popen( cmd )

## NVIDIA texture compress documentation

_nvcompress_doc = '''
usage: nvcompress [options] infile [outfile]

Input options:
  -color       The input image is a color map (default).
  -alpha         The input image has an alpha channel used for transparency.
  -normal      The input image is a normal map.
  -tonormal    Convert input to normal map.
  -clamp       Clamp wrapping mode (default).
  -repeat      Repeat wrapping mode.
  -nomips      Disable mipmap generation.

Compression options:
  -fast        Fast compression.
  -nocuda      Do not use cuda compressor.
  -rgb         RGBA format
  -bc1         BC1 format (DXT1)
  -bc1n        BC1 normal map format (DXT1nm)
  -bc1a        BC1 format with binary alpha (DXT1a)
  -bc2         BC2 format (DXT3)
  -bc3         BC3 format (DXT5)
  -bc3n        BC3 normal map format (DXT5nm)
  -bc4         BC4 format (ATI1)
  -bc5         BC5 format (3Dc/ATI2)
'''
class OgreMaterialGenerator( _image_processing_ ):
    def __init__(self, material, path='/tmp', touch_textures=False ):
        self.material = material # top level material
        self.path = path         # copy textures to path
        self.passes = []
        self.touch_textures = touch_textures
        if material.node_tree:
            nodes = shader.get_subnodes( self.material.node_tree, type='MATERIAL_EXT' )
            for node in nodes:
                if node.material:
                    self.passes.append( node.material )

    def get_active_programs(self):
        r = []
        for mat in self.passes:
            if mat.use_ogre_parent_material and mat.ogre_parent_material:
                usermat = get_ogre_user_material( mat.ogre_parent_material )
                for prog in usermat.get_programs(): r.append( prog )
        return r

    def get_header(self):
        r = []
        for mat in self.passes:
            if mat.use_ogre_parent_material and mat.ogre_parent_material:
                usermat = get_ogre_user_material( mat.ogre_parent_material )
                r.append( '// user material: %s' %usermat.name )
                for prog in usermat.get_programs():
                    r.append( prog.data )
                r.append( '// abstract passes //' )
                r += usermat.as_abstract_passes()
        return '\n'.join( r )

    def get_passes(self):
        r = []
        r.append( self.generate_pass(self.material) )
        for mat in self.passes:
            if mat.use_in_ogre_material_pass: # submaterials
                r.append( self.generate_pass(mat) )
        return r

    def generate_pass( self, mat, pass_name=None ):
        usermat = texnodes = None
        if mat.use_ogre_parent_material and mat.ogre_parent_material:
            usermat = get_ogre_user_material( mat.ogre_parent_material )
            texnodes = shader.get_texture_subnodes( self.material, mat )

        M = ''
        if not pass_name: pass_name = mat.name
        if usermat:
            M += indent(2, 'pass %s : %s/PASS0' %(pass_name,usermat.name), '{' )
        else:
            M += indent(2, 'pass %s'%pass_name, '{' )

        color = mat.diffuse_color
        alpha = 1.0
        if mat.use_transparency:
            alpha = mat.alpha

        slots = get_image_textures( mat )        # returns texture_slot objects (CLASSIC MATERIAL)
        usealpha = False #mat.ogre_depth_write
        for slot in slots:
            #if slot.use_map_alpha and slot.texture.use_alpha: usealpha = True; break
            if (slot.texture.image is not None) and (slot.texture.image.use_alpha): usealpha = True; break

        ## force material alpha to 1.0 if textures use_alpha?
        #if usealpha: alpha = 1.0    # let the alpha of the texture control material alpha?

        if mat.use_fixed_pipeline:
            f = mat.ambient
            if mat.use_vertex_color_paint:
                M += indent(3, 'ambient vertexcolour' )
            else:        # fall back to basic material
                M += indent(3, 'ambient %s %s %s %s' %(color.r*f, color.g*f, color.b*f, alpha) )

            f = mat.diffuse_intensity
            if mat.use_vertex_color_paint:
                M += indent(3, 'diffuse vertexcolour' )
            else:        # fall back to basic material
                M += indent(3, 'diffuse %s %s %s %s' %(color.r*f, color.g*f, color.b*f, alpha) )

            f = mat.specular_intensity
            s = mat.specular_color
            M += indent(3, 'specular %s %s %s %s %s' %(s.r*f, s.g*f, s.b*f, alpha, mat.specular_hardness/4.0) )

            f = mat.emit
            if mat.use_shadeless:     # requested by Borris
                M += indent(3, 'emissive %s %s %s 1.0' %(color.r, color.g, color.b) )
            elif mat.use_vertex_color_light:
                M += indent(3, 'emissive vertexcolour' )
            else:
                M += indent(3, 'emissive %s %s %s %s' %(color.r*f, color.g*f, color.b*f, alpha) )
            M += '\n' # pretty printing

        if mat.offset_z:
            M += indent(3, 'depth_bias %s'%mat.offset_z )

        for name in dir(mat):   #mat.items() - items returns custom props not pyRNA:
            if name.startswith('ogre_') and name != 'ogre_parent_material':
                var = getattr(mat,name)
                op = name.replace('ogre_', '')
                val = var
                if type(var) == bool:
                    if var: val = 'on'
                    else: val = 'off'
                M += indent( 3, '%s %s' %(op,val) )
        M += '\n' # pretty printing

        if texnodes and usermat.texture_units:
            for i,name in enumerate(usermat.texture_units_order):
                if i<len(texnodes):
                    node = texnodes[i]
                    if node.texture:
                        geo = shader.get_connected_input_nodes( self.material, node )[0]
                        M += self.generate_texture_unit( node.texture, name=name, uv_layer=geo.uv_layer )
        elif slots:
            for slot in slots:
                M += self.generate_texture_unit( slot.texture, slot=slot )

        M += indent(2, '}' )    # end pass
        return M

    def generate_texture_unit(self, texture, slot=None, name=None, uv_layer=None):
        if not hasattr(texture, 'image'):
            print('WARNING: texture must be of type IMAGE->', texture)
            return ''
        if not texture.image:
            print('WARNING: texture has no image assigned->', texture)
            return ''
        #if slot: print(dir(slot))
        if slot and not slot.use: return ''

        path = self.path    #CONFIG['PATH']

        M = ''; _alphahack = None
        if not name: name = ''      #texture.name   # (its unsafe to use texture block name)
        M += indent(3, 'texture_unit %s' %name, '{' )

        if texture.library: # support library linked textures
            libpath = os.path.split( bpy.path.abspath(texture.library.filepath) )[0]
            iurl = bpy.path.abspath( texture.image.filepath, libpath )
        else:
            iurl = bpy.path.abspath( texture.image.filepath )

        postname = texname = os.path.split(iurl)[-1]

        if texture.image.packed_file:
            orig = texture.image.filepath
            iurl = os.path.join(path, texname)
            if '.' not in iurl:
                print('WARNING: packed image is of unknown type - assuming PNG format')
                iurl += '.png'
                texname = postname = os.path.split(iurl)[-1]

            if not os.path.isfile( iurl ):
                if self.touch_textures:
                    print('MESSAGE: unpacking image: ', iurl)
                    texture.image.filepath = iurl
                    texture.image.save()
                    texture.image.filepath = orig
            else:
                print('MESSAGE: packed image already in temp, not updating', iurl)

        if is_image_postprocessed( texture.image ):
            postname = self._reformat( texname, texture.image )
            print('MESSAGE: image postproc',postname)

        M += indent(4, 'texture %s' %postname )

        exmode = texture.extension
        if exmode in TEXTURE_ADDRESS_MODE:
            M += indent(4, 'tex_address_mode %s' % TEXTURE_ADDRESS_MODE[exmode] )


        # TODO - hijack nodes for better control?
        if slot:        # classic blender material slot options
            if exmode == 'CLIP': M += indent(4, 'tex_border_colour %s %s %s' %(slot.color.r, slot.color.g, slot.color.b) )
            M += indent(4, 'scale %s %s' %(1.0/slot.scale.x, 1.0/slot.scale.y) )
            if slot.texture_coords == 'REFLECTION':
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

            if slot.uv_layer:
                idx = find_uv_layer_index( slot.uv_layer, self.material )
                M += indent(4, 'tex_coord_set %s' %idx)

            rgba = False
            if texture.image.depth == 32: rgba = True
            btype = slot.blend_type     # TODO - fix this hack if/when slots support pyRNA
            ex = False; texop = None
            if btype in TEXTURE_COLOUR_OP:
                if btype=='MIX' and slot.use_map_alpha and not slot.use_stencil:
                    if slot.diffuse_color_factor >= 1.0: texop = 'alpha_blend'
                    else:
                        texop = TEXTURE_COLOUR_OP[ btype ]
                        ex = True
                elif btype=='MIX' and slot.use_map_alpha and slot.use_stencil:
                    texop = 'blend_current_alpha'; ex=True
                elif btype=='MIX' and not slot.use_map_alpha and slot.use_stencil:
                    texop = 'blend_texture_alpha'; ex=True
                else:
                    texop = TEXTURE_COLOUR_OP[ btype ]
            elif btype in TEXTURE_COLOUR_OP_EXcolour_op_ex:
                    texop = TEXTURE_COLOUR_OP_EX[ btype ]
                    ex = True

            if texop and ex:
                if texop == 'blend_manual':
                    factor = 1.0 - slot.diffuse_color_factor
                    M += indent(4, 'colour_op_ex %s src_texture src_current %s' %(texop, factor) )
                else:
                    M += indent(4, 'colour_op_ex %s src_texture src_current' %texop )
            elif texop:
                    M += indent(4, 'colour_op %s' % texop )

        else:
            if uv_layer:
                idx = find_uv_layer_index( uv_layer )
                M += indent(4, 'tex_coord_set %s' %idx)

        M += indent(3, '}' )

        # copy the texture the the destination path
        if self.touch_textures:
            if not os.path.isfile(iurl):
                Report.warnings.append('Missing texture: %s' %iurl )
            else:
                desturl = os.path.join(path, texname)
                updated = False
                if not os.path.isfile(desturl) or\
                        os.stat(desturl).st_mtime < os.stat( iurl ).st_mtime:
                    shutil.copyfile(iurl, desturl)
                    updated = True
                posturl = os.path.join(path, postname)
                if is_image_postprocessed( texture.image ):
                    if not os.path.isfile( posturl ) or updated:
                        self.image_magick( texture, desturl )   # calls nvconvert if required

        return M

def update_parent_material_path( path ):
    ''' updates RNA '''
    print( '>>SEARCHING FOR OGRE MATERIALS: %s' %path )
    scripts = []
    progs = []
    missing = []
    parse_material_and_program_scripts( path, scripts, progs, missing )

    if missing:
        print('WARNING: missing shader programs:')
        for p in missing: print(p.name)
    if missing and not progs:
        print('WARNING: no shader programs were found - set "SHADER_PROGRAMS" to your path')

    MaterialScripts.reset_rna( callback=shader.on_change_parent_material )
    return scripts, progs

