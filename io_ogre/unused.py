
## Ogre Command Line Tools Documentation
## Pop up dialog for various info/error messages

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


popup_message = ""

class PopUpDialogOperator(bpy.types.Operator):
    bl_idname = "object.popup_dialog_operator"
    bl_label = "blender2ogre"

    def __init__(self):
        print("dialog Start")

    def __del__(self):
        print("dialog End")

    def execute(self, context):
        print ("execute")
        return {'RUNNING_MODAL'}

    def draw(self, context):
        # todo: Make this bigger and center on screen.
        # Blender UI stuff seems quite complex, would
        # think that showing a dialog with a message thath
        # does not hide when mouse is moved would be simpler!
        global popup_message
        layout = self.layout
        col = layout.column()
        col.label(popup_message, 'ERROR')

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_popup(self)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # Close
        if event.type == 'LEFTMOUSE':
            print ("Left mouse")
            return {'FINISHED'}
        # Close
        elif event.type in ('RIGHTMOUSE', 'ESC'):
            print ("right mouse")
            return {'FINISHED'}

        print("running modal")
        return {'RUNNING_MODAL'}

def show_dialog(message):
    global popup_message
    popup_message = message
    bpy.ops.object.popup_dialog_operator('INVOKE_DEFAULT')


_ogre_command_line_tools_doc = '''
Usage: OgreXMLConverter [options] sourcefile [destfile]

Available options:
-i             = interactive mode - prompt for options
(The next 4 options are only applicable when converting XML to Mesh)
-l lodlevels   = number of LOD levels
-v lodvalue     = value increment to reduce LOD
-s lodstrategy = LOD strategy to use for this mesh
-p lodpercent  = Percentage triangle reduction amount per LOD
-f lodnumtris  = Fixed vertex reduction per LOD
-e             = DON'T generate edge lists (for stencil shadows)
-r             = DON'T reorganise vertex buffers to OGRE recommended format.
-t             = Generate tangents (for normal mapping)
-td [uvw|tangent]
           = Tangent vertex semantic destination (default tangent)
-ts [3|4]      = Tangent size (3 or 4 components, 4 includes parity, default 3)
-tm            = Split tangent vertices at UV mirror points
-tr            = Split tangent vertices where basis is rotated > 90 degrees
-o             = DON'T optimise out redundant tracks & keyframes
-d3d           = Prefer D3D packed colour formats (default on Windows)
-gl            = Prefer GL packed colour formats (default on non-Windows)
-E endian      = Set endian mode 'big' 'little' or 'native' (default)
-x num         = Generate no more than num eXtremes for every submesh (default 0)
-q             = Quiet mode, less output
-log filename  = name of the log file (default: 'OgreXMLConverter.log')
sourcefile     = name of file to convert
destfile       = optional name of file to write to. If you don't
                 specify this OGRE works it out through the extension
                 and the XML contents if the source is XML. For example
                 test.mesh becomes test.xml, test.xml becomes test.mesh
                 if the XML document root is <mesh> etc.
'''

class CMesh(object):

    def __init__(self, data):
        self.numVerts = N = len( data.vertices )
        self.numFaces = Nfaces = len(data.tessfaces)

        self.vertex_positions = (ctypes.c_float * (N * 3))()
        data.vertices.foreach_get( 'co', self.vertex_positions )
        v = self.vertex_positions

        self.vertex_normals = (ctypes.c_float * (N * 3))()
        data.vertices.foreach_get( 'normal', self.vertex_normals )

        self.faces = (ctypes.c_uint * (Nfaces * 4))()
        data.tessfaces.foreach_get( 'vertices_raw', self.faces )

        self.faces_normals = (ctypes.c_float * (Nfaces * 3))()
        data.tessfaces.foreach_get( 'normal', self.faces_normals )

        self.faces_smooth = (ctypes.c_bool * Nfaces)()
        data.tessfaces.foreach_get( 'use_smooth', self.faces_smooth )

        self.faces_material_index = (ctypes.c_ushort * Nfaces)()
        data.tessfaces.foreach_get( 'material_index', self.faces_material_index )

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

    def save( blenderobject, path ):
        cmesh = Mesh( blenderobject.data )
        start = time.time()
        dotmesh(
            path,
            ctypes.addressof( cmesh.faces ),
            ctypes.addressof( cmesh.faces_smooth ),
            ctypes.addressof( cmesh.faces_material_index ),
            ctypes.addressof( cmesh.vertex_positions ),
            ctypes.addressof( cmesh.vertex_normals ),
            cmesh.numFaces,
            cmesh.numVerts,
        )
        print('Mesh dumped in %s seconds' % (time.time()-start))



class JmonkeyPreviewOp( _OgreCommonExport_, bpy.types.Operator ):
    '''helper to open jMonkey (JME)'''
    bl_idname = 'jmonkey.preview'
    bl_label = "opens JMonkeyEngine in a non-blocking subprocess"
    bl_options = {'REGISTER'}

    filepath= StringProperty(name="File Path", description="Filepath used for exporting Jmonkey .scene file", maxlen=1024, default="/tmp/preview.txml", subtype='FILE_PATH')
    EXPORT_TYPE = 'OGRE'

    @classmethod
    def poll(cls, context):
        if context.active_object: return True

    def invoke(self, context, event):
        global TundraSingleton
        path = '/tmp/preview.scene'
        self.ogre_export( path, context )
        JmonkeyPipe( path )
        return {'FINISHED'}

def JmonkeyPipe( path ):
    root = CONFIG[ 'JMONKEY_ROOT']
    if sys.platform.startswith('win'):
        cmd = [ os.path.join( os.path.join( root, 'bin' ), 'jmonkeyplatform.exe' ) ]
    else:
        cmd = [ os.path.join( os.path.join( root, 'bin' ), 'jmonkeyplatform' ) ]
    cmd.append( '--nosplash' )
    cmd.append( '--open' )
    cmd.append( path )
    proc = subprocess.Popen(cmd)#, stdin=subprocess.PIPE)
    return proc

## NVIDIA texture tool documentation

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
