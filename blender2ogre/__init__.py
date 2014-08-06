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

import os, sys, time, array, ctypes, math
import bpy, mathutils
from bpy.props import *
import hashlib, getpass, tempfile, configparser, subprocess, pickle
from . import config
from .util import *
from .xml import *
from .report import *
from .ogre.export import INFO_OT_createOgreExport
from .ogre.material import IMAGE_FORMATS, update_parent_material_path, generate_material
from .report import Report
from .ogre.meshy import OgreMeshyPreviewOp
from . import help
from .tundra.properties import *
from .properties import *

UI_CLASSES = []
def UI(cls):
    ''' Toggles the Ogre interface panels '''
    if cls not in UI_CLASSES:
        UI_CLASSES.append(cls)
    return cls
def hide_user_interface():
    for cls in UI_CLASSES:
        bpy.utils.unregister_class( cls )

''' todo: Update the nonsense C:\Tundra2 paths from defaul config and fix this doc.
    Additionally point to some doc how to build opengl only version on windows if that really is needed and
    remove the old Tundra 7z link. '''

## Options

class MiniReport(bpy.types.Menu):
    bl_label = "Mini-Report | (see console for full report)"
    def draw(self, context):
        layout = self.layout
        txt = Report.report()
        for line in txt.splitlines():
            layout.label(text=line)

# UI panels

@UI
class PANEL_Physics(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Physics"

    @classmethod
    def poll(cls, context):
        if context.active_object:
            return True
        else:
            return False

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        game = ob.game

        if ob.type != 'MESH':
            return
        elif ob.subcollision == True:
            box = layout.box()
            if ob.parent:
                box.label(text='object is a collision proxy for: %s' %ob.parent.name)
            else:
                box.label(text='WARNING: collision proxy missing parent')
            return

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

@UI
class PANEL_Collision(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Collision"

    @classmethod
    def poll(cls, context):
        if context.active_object:
            return True
        else:
            return False

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        game = ob.game

        if ob.type != 'MESH':
            return
        elif ob.subcollision == True:
            box = layout.box()
            if ob.parent:
                box.label(text='object is a collision proxy for: %s' %ob.parent.name)
            else:
                box.label(text='WARNING: collision proxy missing parent')
            return

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
            if mode == 'PRIMITIVE':
                box.label(text='Primitive: %s' %prim)
            else:
                box.label(text='Primitive')

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

@UI
class PANEL_Configure(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_label = "Ogre Configuration File"

    def draw(self, context):
        layout = self.layout
        op = layout.operator( 'ogre.save_config', text='update config file', icon='FILE' )
        for tag in _CONFIG_TAGS_:
            layout.prop( context.window_manager, tag )


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

## Game Logic Documentation

class _WrapLogic(object):
    SwapName = { 'frame_property' : 'animation' } # custom name hacks

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
            nodes = bpyShaders.get_or_create_material_passes( mat )
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

@UI
class MatPass1( _OgreMatPass, bpy.types.Panel ): INDEX = 0; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
@UI
class MatPass2( _OgreMatPass, bpy.types.Panel ): INDEX = 1; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
@UI
class MatPass3( _OgreMatPass, bpy.types.Panel ): INDEX = 2; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
@UI
class MatPass4( _OgreMatPass, bpy.types.Panel ): INDEX = 3; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
@UI
class MatPass5( _OgreMatPass, bpy.types.Panel ): INDEX = 4; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
@UI
class MatPass6( _OgreMatPass, bpy.types.Panel ): INDEX = 5; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
@UI
class MatPass7( _OgreMatPass, bpy.types.Panel ): INDEX = 6; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)
@UI
class MatPass8( _OgreMatPass, bpy.types.Panel ): INDEX = 7; bl_label = "Ogre Material (pass%s)"%str(INDEX+1)

class _create_new_material_layer_helper(bpy.types.Operator):
    '''helper to create new material layer'''
    bl_idname = "ogre.helper_create_attach_material_layer"
    bl_label = "creates and assigns new material to layer"
    bl_options = {'REGISTER'}
    INDEX = IntProperty(name="material layer index", description="index", default=0, min=0, max=8)

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.active_material and context.active_object.active_material.use_material_passes:
            return True

    def execute(self, context):
        mat = context.active_object.active_material
        nodes = bpyShaders.get_or_create_material_passes( mat )
        node = nodes[ self.INDEX ]
        node.material = bpy.data.materials.new( name='%s.LAYER%s'%(mat.name,self.INDEX) )
        node.material.use_fixed_pipeline = False
        node.material.offset_z = (self.INDEX*2) + 2     # nudge each pass by 2
        return {'FINISHED'}

# UI panels continues

@UI
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

@UI
class PANEL_Textures(bpy.types.Panel):
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
        if not slot or not slot.texture:
            return

        btype = slot.blend_type  # todo: fix this hack if/when slots support pyRNA
        ex = False; texop = None
        if btype in TextureUnit.colour_op:
            if btype=='MIX' and slot.use_map_alpha and not slot.use_stencil:
                if slot.diffuse_color_factor >= 1.0:
                    texop = 'alpha_blend'
                else:
                    texop = TextureUnit.colour_op_ex[ btype ]
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

        box = layout.box()
        row = box.row()
        if texop:
            if ex:
                row.prop(slot, "blend_type", text=texop, icon='NEW')
            else:
                row.prop(slot, "blend_type", text=texop)
        else:
            row.prop(slot, "blend_type", text='(invalid option)')

        if btype == 'MIX':
            row.prop(slot, "use_stencil", text="")
            row.prop(slot, "use_map_alpha", text="")
            if texop == 'blend_manual':
                row = box.row()
                row.label(text="Alpha:")
                row.prop(slot, "diffuse_color_factor", text="")

        if hasattr(slot.texture, 'image') and slot.texture.image:
            row = box.row()
            n = '(invalid option)'
            if slot.texture.extension in TextureUnit.tex_address_mode:
                n = TextureUnit.tex_address_mode[ slot.texture.extension ]
            row.prop(slot.texture, "extension", text=n)
            if slot.texture.extension == 'CLIP':
                row.prop(slot, "color", text="Border Color")

        row = box.row()
        if slot.texture_coords == 'UV':
            row.prop(slot, "texture_coords", text="", icon='GROUP_UVS')
            row.prop(slot, "uv_layer", text='Layer')
        elif slot.texture_coords == 'REFLECTION':
            row.prop(slot, "texture_coords", text="", icon='MOD_UVPROJECT')
            n = '(invalid option)'
            if slot.mapping in 'FLAT SPHERE'.split(): n = ''
            row.prop(slot, "mapping", text=n)
        else:
            row.prop(slot, "texture_coords", text="(invalid mapping option)")

        # Animation and offset options
        split = layout.row()
        box = split.box()
        box.prop(slot, "offset", text="XY=offset,  Z=rotation")
        box = split.box()
        box.prop(slot, "scale", text="XY=scale (Z ignored)")

        box = layout.box()
        row = box.row()
        row.label(text='scrolling animation')

        # Can't use if its enabled by default row.prop(slot, "use_map_density", text="")
        row.prop(slot, "use_map_scatter", text="")
        row = box.row()
        row.prop(slot, "density_factor", text="X")
        row.prop(slot, "emission_factor", text="Y")

        box = layout.box()
        row = box.row()
        row.label(text='rotation animation')
        row.prop(slot, "emission_color_factor", text="")
        row.prop(slot, "use_from_dupli", text="")

        ## Image magick
        if hasattr(slot.texture, 'image') and slot.texture.image:
            img = slot.texture.image
            box = layout.box()
            row = box.row()
            row.prop( img, 'use_convert_format' )
            if img.use_convert_format:
                row.prop( img, 'convert_format' )
                if img.convert_format == 'jpg':
                    box.prop( img, 'jpeg_quality' )

            row = box.row()
            row.prop( img, 'use_color_quantize', text='Reduce Colors' )
            if img.use_color_quantize:
                row.prop( img, 'use_color_quantize_dither', text='dither' )
                row.prop( img, 'color_quantize', text='colors' )

            row = box.row()
            row.prop( img, 'use_resize_half' )
            if not img.use_resize_half:
                row.prop( img, 'use_resize_absolute' )
                if img.use_resize_absolute:
                    row = box.row()
                    row.prop( img, 'resize_x' )
                    row.prop( img, 'resize_y' )

## Ogre Documentation to UI

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
    def get_merge_group( ob ):
        return get_merge_group( ob, prefix='magicmerge' )

    @staticmethod
    def merge( group, path='/tmp', force_name=None ):
        print('-'*80)
        print(' mesh magick - merge ')
        exe = CONFIG['OGRETOOLS_MESH_MAGICK']
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

## Selector extras

class INFO_MT_instances(bpy.types.Menu):
    bl_label = "Instances"

    def draw(self, context):
        layout = self.layout
        inst = gather_instances()
        for data in inst:
            ob = inst[data][0]
            op = layout.operator(INFO_MT_instance.bl_idname, text=ob.name) # operator has no variable for button name?
            op.mystring = ob.name
        layout.separator()

class INFO_MT_instance(bpy.types.Operator):
    '''select instance group'''
    bl_idname = "ogre.select_instances"
    bl_label = "Select Instance Group"
    bl_options = {'REGISTER', 'UNDO'} # Options for this panel type
    mystring= StringProperty(name="MyString", description="hidden string", maxlen=1024, default="my string")

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
            op = layout.operator(INFO_MT_group.bl_idname, text=group.name)    # operator no variable for button name?
            op.mystring = group.name
        layout.separator()

class INFO_MT_group(bpy.types.Operator):
    '''select group'''
    bl_idname = "ogre.select_group"
    bl_label = "Select Group"
    bl_options = {'REGISTER'}                              # Options for this panel type
    mystring= StringProperty(name="MyString", description="hidden string", maxlen=1024, default="my string")

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        select_group( context, self.mystring )
        return {'FINISHED'}

## More UI

class MENU_preview_material_text(bpy.types.Menu):
    bl_label = 'preview'

    @classmethod
    def poll(self,context):
        if context.active_object and context.active_object.active_material:
            return True

    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material
        if mat:
            #CONFIG['TOUCH_TEXTURES'] = False
            preview = generate_material( mat )
            for line in preview.splitlines():
                if line.strip():
                    for ww in wordwrap( line ):
                        layout.label(text=ww)

@UI
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

        #layout.separator()

        #if _USE_JMONKEY_:
        #    row = layout.row(align=True)
        #    op = row.operator( 'jmonkey.preview', text='', icon='MONKEY' )

        # TODO
        #if _USE_TUNDRA_:
        #    row = layout.row(align=True)
        #    op = row.operator( 'tundra.preview', text='', icon='WORLD' )
        #    if TundraSingleton:
        #        op = row.operator( 'tundra.preview', text='', icon='META_CUBE' )
        #        op.EX_SCENE = False
        #        if not TundraSingleton.physics:
        #            op = row.operator( 'tundra.start_physics', text='', icon='PLAY' )
        #        else:
        #            op = row.operator( 'tundra.stop_physics', text='', icon='PAUSE' )
        #        op = row.operator( 'tundra.toggle_physics_debug', text='', icon='MOD_PHYSICS' )
        #        op = row.operator( 'tundra.exit', text='', icon='CANCEL' )

        op = layout.operator( 'ogremeshy.preview', text='', icon='PLUGIN' ); op.mesh = True

        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.menu("INFO_MT_file")
        sub.menu("INFO_MT_add")
        if rd.use_game_engine: sub.menu("INFO_MT_game")
        else: sub.menu("INFO_MT_render")

        row = layout.row(align=False); row.scale_x = 1.25
        row.menu("INFO_MT_instances", icon='NODETREE', text='')
        row.menu("INFO_MT_groups", icon='GROUP', text='')

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
                row.scale_y = 0.75; row.scale_x = 0.9
                row.prop( ob, 'layers', text='' )

            layout.separator()
            row = layout.row(align=True); row.scale_x = 1.1
            row.prop(scene.game_settings, 'material_mode', text='')
            row.prop(scene, 'camera', text='')

            layout.menu( 'MENU_preview_material_text', icon='TEXT', text='' )

            layout.menu( "INFO_MT_ogre_docs" )
            layout.operator("wm.window_fullscreen_toggle", icon='FULLSCREEN_ENTER', text="")
            if OgreToggleInterfaceOp.TOGGLE: layout.operator('ogre.toggle_interface', text='Ogre', icon='CHECKBOX_DEHLT')
            else: layout.operator('ogre.toggle_interface', text='Ogre', icon='CHECKBOX_HLT')

def export_menu_func_ogre(self, context):
    op = self.layout.operator(INFO_OT_createOgreExport.bl_idname, text="Ogre3D (.scene and .mesh)")

# TODO TUNDRA def export_menu_func_realxtend(self, context):
#    op = self.layout.operator(INFO_OT_createRealxtendExport.bl_idname, text="realXtend Tundra (.txml and .mesh)")

try:
    _header_ = bpy.types.INFO_HT_header
except:
    print('---blender2ogre addon enable---')

## Toggle button for blender2ogre UI panels

class OgreToggleInterfaceOp(bpy.types.Operator):
    '''Toggle Ogre UI'''
    bl_idname = "ogre.toggle_interface"
    bl_label = "Ogre UI"
    bl_options = {'REGISTER'}
    TOGGLE = True
    BLENDER_DEFAULT_HEADER = _header_

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        #global _header_
        if OgreToggleInterfaceOp.TOGGLE: #_header_:
            print( 'ogre.toggle_interface ENABLE' )
            bpy.utils.register_module(__name__)
            #_header_ = bpy.types.INFO_HT_header
            try: bpy.utils.unregister_class(_header_)
            except: pass
            bpy.utils.unregister_class( INFO_HT_microheader )   # moved to custom header
            OgreToggleInterfaceOp.TOGGLE = False
        else:
            print( 'ogre.toggle_interface DISABLE' )
            #bpy.utils.unregister_module(__name__); # this is not safe, can segfault blender, why?
            hide_user_interface()
            bpy.utils.register_class(_header_)
            restore_minimal_interface()
            OgreToggleInterfaceOp.TOGGLE = True
        return {'FINISHED'}

def get_minimal_interface_classes():
    # TODO TUNDRA , INFO_OT_createRealxtendExport
    return INFO_OT_createOgreExport, OgreToggleInterfaceOp, MiniReport, INFO_HT_microheader

def restore_minimal_interface():
    for cls in get_minimal_interface_classes():
        try: bpy.utils.register_class( cls )
        except: pass

class INFO_HT_microheader(bpy.types.Header):
    bl_space_type = 'INFO'
    def draw(self, context):
        layout = self.layout
        try:
            if OgreToggleInterfaceOp.TOGGLE:
                layout.operator('ogre.toggle_interface', text='Ogre', icon='CHECKBOX_DEHLT')
            else:
                layout.operator('ogre.toggle_interface', text='Ogre', icon='CHECKBOX_HLT')
        except: pass    # STILL REQUIRED?

## Blender world panel options for EC_SkyX creation
## todo: EC_SkyX has changes a bit lately, see that
## all these options are still correct and valid
## old todo (?): Move to tundra.py

@UI
class OgreSkyPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "world"
    bl_label = "Ogre Sky Settings"

    @classmethod
    def poll(cls, context):
        return True

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

class TextureUnit(object):
    colour_op = {
        'MIX'       :   'modulate',        # Ogre Default - was "replace" but that kills lighting
        'ADD'     :   'add',
        'MULTIPLY' : 'modulate',
        #'alpha_blend' : '',
    }
    colour_op_ex = {
        'MIX'       :    'blend_manual',
        'SCREEN': 'modulate_x2',
        'LIGHTEN': 'modulate_x4',
        'SUBTRACT': 'subtract',
        'OVERLAY':    'add_signed',
        'DIFFERENCE': 'dotproduct',        # best match?
        'VALUE': 'blend_diffuse_colour',
    }

    tex_address_mode = {
        'REPEAT': 'wrap',
        'EXTEND': 'clamp',
        'CLIP'       : 'border',
        'CHECKER' : 'mirror'
    }

@UI
class PANEL_Object(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Object+"

    @classmethod
    def poll(cls, context):
        _USE_TUNDRA_ = False # TODO
        if _USE_TUNDRA_ and context.active_object:
            return True

    def draw(self, context):
        ob = context.active_object
        layout = self.layout
        box = layout.box()
        box.prop( ob, 'cast_shadows' )

        box.prop( ob, 'use_draw_distance' )
        if ob.use_draw_distance:
            box.prop( ob, 'draw_distance' )
        #if ob.find_armature():
        if ob.type == 'EMPTY':
            box.prop( ob, 'use_avatar' )
            box.prop( ob, 'avatar_reference' )

@UI
class PANEL_Speaker(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_label = "Sound+"
    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type=='SPEAKER': return True
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.prop( context.active_object.data, 'play_on_load' )
        box.prop( context.active_object.data, 'loop' )
        box.prop( context.active_object.data, 'use_spatial' )

@UI
class PANEL_MultiResLOD(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    bl_label = "Multi-Resolution LOD"
    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type=='MESH':
            ob = context.active_object
            if ob.modifiers and ob.modifiers[0].type=='MULTIRES':
                return True
    def draw(self, context):
        ob = context.active_object
        layout = self.layout
        box = layout.box()
        box.prop( ob, 'use_multires_lod' )
        if ob.use_multires_lod:
            box.prop( ob, 'multires_lod_range' )

class bpyShaders(bpy.types.Operator):
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
        bpyShaders.create_material_passes( mat )
        return {'FINISHED'}

    ## setup from MaterialScripts.reset_rna( callback=bpyShaders.on_change_parent_material )
    @staticmethod
    def on_change_parent_material(mat,context):
        print(mat,context)
        print('callback', mat.ogre_parent_material)

    @staticmethod
    def get_subnodes(mat, type='TEXTURE'):
        d = {}
        for node in mat.nodes:
            if node.type==type: d[node.name] = node
        keys = list(d.keys())
        keys.sort()
        r = []
        for key in keys: r.append( d[key] )
        return r


    @staticmethod
    def get_texture_subnodes( parent, submaterial=None ):
        if not submaterial: submaterial = parent.active_node_material
        d = {}
        for link in parent.node_tree.links:
            if link.from_node and link.from_node.type=='TEXTURE':
                if link.to_node and link.to_node.type == 'MATERIAL_EXT':
                    if link.to_node.material:
                        if link.to_node.material.name == submaterial.name:
                            node = link.from_node
                            d[node.name] = node
        keys = list(d.keys())           # this breaks if the user renames the node - TODO improve me
        keys.sort()
        r = []
        for key in keys: r.append( d[key] )
        return r

    @staticmethod
    def get_connected_input_nodes( material, node ):
        r = []
        for link in material.node_tree.links:
            if link.to_node and link.to_node.name == node.name:
                r.append( link.from_node )
        return r

    @staticmethod
    def get_or_create_material_passes( mat, n=8 ):
        if not mat.node_tree:
            print('CREATING MATERIAL PASSES', n)
            bpyShaders.create_material_passes( mat, n )

        d = {}      # funky, blender259 had this in order, now blender260 has random order
        for node in mat.node_tree.nodes:
            if node.type == 'MATERIAL_EXT' and node.name.startswith('GEN.'):
                d[node.name] = node
        keys = list(d.keys())
        keys.sort()
        r = []
        for key in keys: r.append( d[key] )
        return r

    @staticmethod
    def get_or_create_texture_nodes( mat, n=6 ):    # currently not used
        #print('bpyShaders.get_or_create_texture_nodes( %s, %s )' %(mat,n))
        assert mat.node_tree    # must call create_material_passes first
        m = []
        for node in mat.node_tree.nodes:
            if node.type == 'MATERIAL_EXT' and node.name.startswith('GEN.'):
                m.append( node )
        if not m:
            m = bpyShaders.get_or_create_material_passes(mat)
        print(m)
        r = []
        for link in mat.node_tree.links:
            print(link, link.to_node, link.from_node)
            if link.to_node and link.to_node.name.startswith('GEN.') and link.from_node.type=='TEXTURE':
                r.append( link.from_node )
        if not r:
            print('--missing texture nodes--')
            r = bpyShaders.create_texture_nodes( mat, n )
        return r

    @staticmethod
    def create_material_passes( mat, n=8, textures=True ):
        #print('bpyShaders.create_material_passes( %s, %s )' %(mat,n))
        mat.use_nodes = True
        tree = mat.node_tree    # valid pointer now

        nodes = bpyShaders.get_subnodes( tree, 'MATERIAL' )  # assign base material
        if nodes and not nodes[0].material:
            nodes[0].material = mat

        r = []
        x = 680
        for i in range( n ):
            node = tree.nodes.new( type='MATERIAL_EXT' )
            node.name = 'GEN.%s' %i
            node.location.x = x; node.location.y = 640
            r.append( node )
            x += 220
        #mat.use_nodes = False  # TODO set user material to default output
        if textures:
            texnodes = bpyShaders.create_texture_nodes( mat )
            print( texnodes )
        return r

    @staticmethod
    def create_texture_nodes( mat, n=6, geoms=True ):
        #print('bpyShaders.create_texture_nodes( %s )' %mat)
        assert mat.node_tree    # must call create_material_passes first
        mats = bpyShaders.get_or_create_material_passes( mat )
        r = {}; x = 400
        for i,m in enumerate(mats):
            r['material'] = m; r['textures'] = []; r['geoms'] = []
            inputs = []     # other inputs mess up material preview #
            for tag in ['Mirror', 'Ambient', 'Emit', 'SpecTra', 'Ray Mirror', 'Translucency']:
                inputs.append( m.inputs[ tag ] )
            for j in range(n):
                tex = mat.node_tree.nodes.new( type='TEXTURE' )
                tex.name = 'TEX.%s.%s' %(j, m.name)
                tex.location.x = x - (j*16)
                tex.location.y = -(j*230)
                input = inputs[j]; output = tex.outputs['Color']
                link = mat.node_tree.links.new( input, output )
                r['textures'].append( tex )
                if geoms:
                    geo = mat.node_tree.nodes.new( type='GEOMETRY' )
                    link = mat.node_tree.links.new( tex.inputs['Vector'], geo.outputs['UV'] )
                    geo.location.x = x - (j*16) - 250
                    geo.location.y = -(j*250) - 1500
                    r['geoms'].append( geo )
            x += 220
        return r

@UI
class PANEL_node_editor_ui( bpy.types.Panel ):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_label = "Ogre Material"

    @classmethod
    def poll(self,context):
        if context.space_data.id:
            return True

    def draw(self, context):
        layout = self.layout
        topmat = context.space_data.id             # the top level node_tree
        mat = topmat.active_node_material        # the currently selected sub-material
        if not mat or topmat.name == mat.name:
            self.bl_label = topmat.name
            if not topmat.use_material_passes:
                layout.operator(
                    'ogre.force_setup_material_passes',
                    text="Ogre Material Layers",
                    icon='SCENE_DATA'
                )
            ogre_material_panel( layout, topmat, show_programs=False )
        elif mat:
            self.bl_label = mat.name
            ogre_material_panel( layout, mat, topmat, show_programs=False )

@UI
class PANEL_node_editor_ui_extra( bpy.types.Panel ):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_label = "Ogre Material Advanced"
    bl_options = {'DEFAULT_CLOSED'}
    @classmethod
    def poll(self,context):
        if context.space_data.id: return True
    def draw(self, context):
        layout = self.layout
        topmat = context.space_data.id             # the top level node_tree
        mat = topmat.active_node_material        # the currently selected sub-material
        if mat:
            self.bl_label = mat.name + ' (advanced)'
            ogre_material_panel_extra( layout, mat )
        else:
            self.bl_label = topmat.name + ' (advanced)'
            ogre_material_panel_extra( layout, topmat )

def ogre_material_panel_extra( parent, mat ):
    box = parent.box()
    header = box.row()

    if mat.use_fixed_pipeline:
        header.prop( mat, 'use_fixed_pipeline', text='Fixed Pipeline', icon='LAMP_SUN' )
        row = box.row()
        row.prop(mat, "use_vertex_color_paint", text="Vertex Colors")
        row.prop(mat, "use_shadeless")
        if mat.use_shadeless and not mat.use_vertex_color_paint:
            row = box.row()
            row.prop(mat, "diffuse_color", text='')
        elif not mat.use_shadeless:
            if not mat.use_vertex_color_paint:
                row = box.row()
                row.prop(mat, "diffuse_color", text='')
                row.prop(mat, "diffuse_intensity", text='intensity')
            row = box.row()
            row.prop(mat, "specular_color", text='')
            row.prop(mat, "specular_intensity", text='intensity')
            row = box.row()
            row.prop(mat, "specular_hardness")
            row = box.row()
            row.prop(mat, "ambient")
            #row = box.row()
            row.prop(mat, "emit")
        box.prop(mat, 'use_ogre_advanced_options', text='---guru options---' )
    else:
        header.prop( mat, 'use_fixed_pipeline', text='', icon='LAMP_SUN' )
        header.prop(mat, 'use_ogre_advanced_options', text='---guru options---' )

    if mat.use_ogre_advanced_options:
        box.prop(mat, 'offset_z')
        box.prop(mat, "use_shadows")
        box.prop(mat, 'ogre_depth_write' )
        for tag in 'ogre_colour_write ogre_lighting ogre_normalise_normals ogre_light_clip_planes ogre_light_scissor ogre_alpha_to_coverage ogre_depth_check'.split():
            box.prop(mat, tag)
        for tag in 'ogre_polygon_mode ogre_shading ogre_cull_hardware ogre_transparent_sorting ogre_illumination_stage ogre_depth_func ogre_scene_blend_op'.split():
            box.prop(mat, tag)

def ogre_material_panel( layout, mat, parent=None, show_programs=True ):
    box = layout.box()
    header = box.row()
    header.prop(mat, 'ogre_scene_blend', text='')
    if mat.ogre_scene_blend and 'alpha' in mat.ogre_scene_blend:
        row = box.row()
        if mat.use_transparency:
            row.prop(mat, "use_transparency", text='')
            row.prop(mat, "alpha")
        else:
            row.prop(mat, "use_transparency", text='Transparent')
    if not parent:
        return # only allow on pass1 and higher

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
                texnodes = bpyShaders.get_texture_subnodes( parent, submaterial=mat )
            elif mat.node_tree:
                texnodes = bpyShaders.get_texture_subnodes( mat )   # assume toplevel

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
                            inputs = bpyShaders.get_connected_input_nodes( parent, tex )
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

