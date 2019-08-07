
## Ogre Command Line Tools Documentation
## Pop up dialog for various info/error messages

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