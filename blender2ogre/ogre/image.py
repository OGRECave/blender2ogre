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
            nodes = bpyShaders.get_subnodes( self.material.node_tree, type='MATERIAL_EXT' )
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
            texnodes = bpyShaders.get_texture_subnodes( self.material, mat )

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
                        geo = bpyShaders.get_connected_input_nodes( self.material, node )[0]
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
        destpath = path

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
        if exmode in TextureUnit.tex_address_mode:
            M += indent(4, 'tex_address_mode %s' %TextureUnit.tex_address_mode[exmode] )


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
            if btype in TextureUnit.colour_op:
                if btype=='MIX' and slot.use_map_alpha and not slot.use_stencil:
                    if slot.diffuse_color_factor >= 1.0: texop = 'alpha_blend'
                    else:
                        texop = TextureUnit.colour_op[ btype ]
                        ex = True
                elif btype=='MIX' and slot.use_map_alpha and slot.use_stencil:
                    texop = 'blend_current_alpha'; ex=True
                elif btype=='MIX' and not slot.use_map_alpha and slot.use_stencil:
                    texop = 'blend_texture_alpha'; ex=True
                else:
                    texop = TextureUnit.colour_op[ btype ]
            elif btype in TextureUnit.colour_op_ex:
                    texop = TextureUnit.colour_op_ex[ btype ]
                    ex = True

            if texop and ex:
                if texop == 'blend_manual':
                    factor = 1.0 - slot.diffuse_color_factor
                    M += indent(4, 'colour_op_ex %s src_texture src_current %s' %(texop, factor) )
                else:
                    M += indent(4, 'colour_op_ex %s src_texture src_current' %texop )
            elif texop:
                    M += indent(4, 'colour_op %s' %texop )

        else:
            if uv_layer:
                idx = find_uv_layer_index( uv_layer )
                M += indent(4, 'tex_coord_set %s' %idx)

        M += indent(3, '}' )

        if self.touch_textures:
            # Copy texture only if newer
            if not os.path.isfile(iurl):
                Report.warnings.append('Missing texture: %s' %iurl )
            else:
                desturl = os.path.join( destpath, texname )
                updated = False
                if not os.path.isfile( desturl ) or os.stat( desturl ).st_mtime < os.stat( iurl ).st_mtime:
                    f = open( desturl, 'wb' )
                    f.write( open(iurl,'rb').read() )
                    f.close()
                    updated = True
                posturl = os.path.join(destpath,postname)
                if is_image_postprocessed( texture.image ):
                    if not os.path.isfile( posturl ) or updated:
                        self.image_magick( texture, desturl )   # calls nvconvert if required

        return M

