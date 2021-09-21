
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
        
### Start of old io_ogre/ui/material.py filename
import bpy
from .. import shader
from bpy.props import IntProperty
from ..ogre.material import OgreMaterialGenerator
from ..util import wordwrap

def ogre_register(register):
    yield PANEL_properties_window_ogre_material
    yield MatPass1
    yield MatPass2
    yield MatPass3
    yield MatPass4
    yield MatPass5
    yield MatPass6
    yield MatPass7
    yield MatPass8
    yield MT_preview_material_text
    yield CreateMaterialLayerOperator
    yield SetupMaterialPassesOperator

class MT_preview_material_text(bpy.types.Menu):
    """ Preview the outputted material in a menu in the top header """
    bl_label = 'preview'

    @classmethod
    def poll(self,context):
        if context.active_object and context.active_object.active_material:
            return True

    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material
        if mat:
            preview = OgreMaterialGenerator( mat ).generate()
            for line in preview.splitlines():
                if line.strip():
                    for ww in wordwrap( line ):
                        layout.label(text=ww)


class CreateMaterialLayerOperator(bpy.types.Operator):
    '''helper to create new material layer'''
    bl_idname = "ogre.helper_create_attach_material_layer"
    bl_label = "creates and assigns new material to layer"
    bl_options = {'REGISTER'}
    INDEX = IntProperty(name="material layer index", description="index", default=0, min=0, max=8)

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.active_material\
                and context.active_object.active_material.use_material_passes:
            return True

    def execute(self, context):
        mat = context.active_object.active_material
        nodes = shader.get_or_create_material_passes( mat )
        node = nodes[ self.INDEX ]
        node.material = bpy.data.materials.new( name='%s.LAYER%s'%(mat.name,self.INDEX) )
        node.material.use_fixed_pipeline = False
        node.material.offset_z = (self.INDEX*2) + 2     # nudge each pass by 2
        return {'FINISHED'}

class SetupMaterialPassesOperator(bpy.types.Operator):
    '''operator: enables material nodes (workaround for not having IDPointers in pyRNA)'''
    bl_idname = "ogre.force_setup_material_passes"
    bl_label = "force bpyShaders"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.active_material: return True

    def invoke(self, context, event):
        mat = context.active_object.active_material
        mat.use_material_passes = True
        shader.create_material_passes( mat )
        return {'FINISHED'}

class PANEL_properties_window_ogre_material( bpy.types.Panel ):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_label = "Ogre Material (base pass)"

    @classmethod
    def poll( self, context ):
        if not hasattr(context, "material"): return False
        if not context.active_object: return False
        if not context.active_object.active_material: return False
        return True

    def draw(self, context):
        mat = context.material
        ob = context.object
        slot = context.material_slot
        layout = self.layout
        if not mat.use_material_passes:
            box = layout.box()
            box.operator( 'ogre.force_setup_material_passes', text="Ogre Material Layers", icon='SCENE_DATA' )

        ogre_material_panel( layout, mat )
        ogre_material_panel_extra( layout, mat )

class _OgreMatPass( object ):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.active_material and context.active_object.active_material.use_material_passes:
            return True

    def draw(self, context):
        if not hasattr(context, "material"):
            return
        if not context.active_object:
            return
        if not context.active_object.active_material:
            return

        mat = context.material
        ob = context.object
        slot = context.material_slot
        layout = self.layout
        #layout.label(text=str(self.INDEX))
        if mat.use_material_passes:
            db = layout.box()
            nodes = shader.get_or_create_material_passes( mat )
            node = nodes[ self.INDEX ]
            split = db.row()
            if node.material: split.prop( node.material, 'use_in_ogre_material_pass', text='' )
            split.prop( node, 'material' )
            if not node.material:
                op = split.operator( 'ogre.helper_create_attach_material_layer', icon="PLUS", text='' )
                op.INDEX = self.INDEX
            if node.material and node.material.use_in_ogre_material_pass:
                dbb = db.box()
                ogre_material_panel( dbb, node.material, parent=mat )
                ogre_material_panel_extra( dbb, node.material )

# is there a better way to do this?
class MatPass1( _OgreMatPass, bpy.types.Panel ): INDEX = 0; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass2( _OgreMatPass, bpy.types.Panel ): INDEX = 1; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass3( _OgreMatPass, bpy.types.Panel ): INDEX = 2; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass4( _OgreMatPass, bpy.types.Panel ): INDEX = 3; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass5( _OgreMatPass, bpy.types.Panel ): INDEX = 4; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass6( _OgreMatPass, bpy.types.Panel ): INDEX = 5; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass7( _OgreMatPass, bpy.types.Panel ): INDEX = 6; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
class MatPass8( _OgreMatPass, bpy.types.Panel ): INDEX = 7; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)

def ogre_material_panel_extra( parent, mat ):
    box = parent.box()
    header = box.row()
    header.prop(mat, 'use_ogre_advanced_options', text='---guru options---' )

    if mat.use_ogre_advanced_options:
        box.prop(mat, 'offset_z')
        for tag in 'ogre_colour_write ogre_normalise_normals ogre_light_clip_planes ogre_light_scissor ogre_alpha_to_coverage ogre_depth_check'.split():
            box.prop(mat, tag)
        for tag in 'ogre_polygon_mode ogre_shading ogre_transparent_sorting ogre_illumination_stage ogre_depth_func ogre_scene_blend_op'.split():
            box.prop(mat, tag)

def ogre_material_panel( layout, mat, parent=None, show_programs=True ):
    if not parent:
        return # only allow on pass1 and higher

    box = layout.box()
    header = box.row()

    header.prop(mat, 'use_ogre_parent_material', icon='FILE_SCRIPT', text='')

    if mat.use_ogre_parent_material:
        row = box.row()
        row.prop(mat, 'ogre_parent_material', text='')

        s = get_ogre_user_material( mat.ogre_parent_material )  # gets by name
        if s and (s.vertex_programs or s.fragment_programs):
            progs = s.get_programs()
            split = box.row()
            texnodes = None

            if parent:
                texnodes = shader.get_texture_subnodes( parent, submaterial=mat )
            elif mat.node_tree:
                texnodes = shader.get_texture_subnodes( mat )   # assume toplevel

            if not progs:
                bx = split.box()
                bx.label( text='(missing shader programs)', icon='ERROR' )
            elif s.texture_units and texnodes:
                bx = split.box()
                for i,name in enumerate(s.texture_units_order):
                    if i<len(texnodes):
                        row = bx.row()
                        #row.label( text=name )
                        tex = texnodes[i]
                        row.prop( tex, 'texture', text=name )
                        if parent:
                            inputs = shader.get_connected_input_nodes( parent, tex )
                            if inputs:
                                geo = inputs[0]
                                assert geo.type == 'GEOMETRY'
                                row.prop( geo, 'uv_layer', text='UV' )
                    else:
                        print('WARNING: no slot for texture unit:', name)

            if show_programs and (s.vertex_programs or s.fragment_programs):
                bx = box.box()
                for name in s.vertex_programs:
                    bx.label( text=name )
                for name in s.fragment_programs:
                    bx.label( text=name )
### End of old io_ogre/ui/material.py filename