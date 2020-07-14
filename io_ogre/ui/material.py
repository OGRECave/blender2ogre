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
