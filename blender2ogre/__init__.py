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
from xml.sax.saxutils import XMLGenerator, quoteattr
from . import version as v

## Make sure we can import from same directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append( SCRIPT_DIR )

# TODO move this around
UI_CLASSES = []
def UI(cls):
    ''' Toggles the Ogre interface panels '''
    if cls not in UI_CLASSES:
        UI_CLASSES.append(cls)
    return cls
def hide_user_interface():
    for cls in UI_CLASSES:
        bpy.utils.unregister_class( cls )

## Avatar

bpy.types.Object.use_avatar = BoolProperty(
    name='enable avatar',
    description='enables EC_Avatar',
    default=False)
bpy.types.Object.avatar_reference = StringProperty(
    name='avatar reference',
    description='sets avatar reference URL',
    maxlen=128,
    default='')
BoolProperty( name='enable avatar', description='enables EC_Avatar', default=False) # todo: is this used?

# Tundra IDs

bpy.types.Object.uid = IntProperty(
    name="unique ID",
    description="unique ID for Tundra",
    default=0, min=0, max=2**14)

# Rendering

bpy.types.Object.use_draw_distance = BoolProperty(
    name='enable draw distance',
    description='use LOD draw distance',
    default=False)
bpy.types.Object.draw_distance = FloatProperty(
    name='draw distance',
    description='distance at which to begin drawing object',
    default=0.0, min=0.0, max=10000.0)
bpy.types.Object.cast_shadows = BoolProperty(
    name='cast shadows',
    description='cast shadows',
    default=False)
bpy.types.Object.use_multires_lod = BoolProperty(
    name='Enable Multires LOD',
    description='enables multires LOD',
    default=False)
bpy.types.Object.multires_lod_range = FloatProperty(
    name='multires LOD range',
    description='far distance at which multires is set to base level',
    default=30.0, min=0.0, max=10000.0)

## Physics

_physics_modes =  [
    ('NONE', 'NONE', 'no physics'),
    ('RIGID_BODY', 'RIGID_BODY', 'rigid body'),
    ('SOFT_BODY', 'SOFT_BODY', 'soft body'),
]
_collision_modes =  [
    ('NONE', 'NONE', 'no collision'),
    ('PRIMITIVE', 'PRIMITIVE', 'primitive collision type'),
    ('MESH', 'MESH', 'triangle-mesh or convex-hull collision type'),
    ('DECIMATED', 'DECIMATED', 'auto-decimated collision type'),
    ('COMPOUND', 'COMPOUND', 'children primitive compound collision type'),
    ('TERRAIN', 'TERRAIN', 'terrain (height map) collision type'),
]

bpy.types.Object.physics_mode = EnumProperty(
    items = _physics_modes,
    name = 'physics mode',
    description='physics mode',
    default='NONE')
bpy.types.Object.physics_friction = FloatProperty(
    name='Simple Friction',
    description='physics friction',
    default=0.1, min=0.0, max=1.0)
bpy.types.Object.physics_bounce = FloatProperty(
    name='Simple Bounce',
    description='physics bounce',
    default=0.01, min=0.0, max=1.0)
bpy.types.Object.collision_terrain_x_steps = IntProperty(
    name="Ogre Terrain: x samples",
    description="resolution in X of height map",
    default=64, min=4, max=8192)
bpy.types.Object.collision_terrain_y_steps = IntProperty(
    name="Ogre Terrain: y samples",
    description="resolution in Y of height map",
    default=64, min=4, max=8192)
bpy.types.Object.collision_mode = EnumProperty(
    items = _collision_modes,
    name = 'primary collision mode',
    description='collision mode',
    default='NONE')
bpy.types.Object.subcollision = BoolProperty(
    name="collision compound",
    description="member of a collision compound",
    default=False)

## Sound

bpy.types.Speaker.play_on_load = BoolProperty(
    name='play on load',
    default=False)
bpy.types.Speaker.loop = BoolProperty(
    name='loop sound',
    default=False)
bpy.types.Speaker.use_spatial = BoolProperty(
    name='3D spatial sound',
    default=True)

## ImageMagick

_IMAGE_FORMATS =  [
    ('NONE','NONE', 'do not convert image'),
    ('bmp', 'bmp', 'bitmap format'),
    ('jpg', 'jpg', 'jpeg format'),
    ('gif', 'gif', 'gif format'),
    ('png', 'png', 'png format'),
    ('tga', 'tga', 'targa format'),
    ('dds', 'dds', 'nvidia dds format'),
]

bpy.types.Image.use_convert_format = BoolProperty(
    name='use convert format',
    default=False
)
bpy.types.Image.convert_format = EnumProperty(
    name='convert to format',
    description='converts to image format using imagemagick',
    items=_IMAGE_FORMATS,
    default='NONE')
bpy.types.Image.jpeg_quality = IntProperty(
    name="jpeg quality",
    description="quality of jpeg",
    default=80, min=0, max=100)
bpy.types.Image.use_color_quantize = BoolProperty(
    name='use color quantize',
    default=False)
bpy.types.Image.use_color_quantize_dither = BoolProperty(
    name='use color quantize dither',
    default=True)
bpy.types.Image.color_quantize = IntProperty(
    name="color quantize",
    description="reduce to N colors (requires ImageMagick)",
    default=32, min=2, max=256)
bpy.types.Image.use_resize_half = BoolProperty(
    name='resize by 1/2',
    default=False)
bpy.types.Image.use_resize_absolute = BoolProperty(
    name='force image resize',
    default=False)
bpy.types.Image.resize_x = IntProperty(
    name='resize X',
    description='only if image is larger than defined, use ImageMagick to resize it down',
    default=256, min=2, max=4096)
bpy.types.Image.resize_y = IntProperty(
    name='resize Y',
    description='only if image is larger than defined, use ImageMagick to resize it down',
    default=256, min=2, max=4096)

# Materials

bpy.types.Material.ogre_depth_write = BoolProperty(
    # Material.ogre_depth_write = AUTO|ON|OFF
    name='depth write',
    default=True)
bpy.types.Material.ogre_depth_check = BoolProperty(
    # If depth-buffer checking is on, whenever a pixel is about to be written to
    # the frame buffer the depth buffer is checked to see if the pixel is in front
    # of all other pixels written at that point. If not, the pixel is not written.
    # If depth checking is off, pixels are written no matter what has been rendered before.
    name='depth check',
    default=True)
bpy.types.Material.ogre_alpha_to_coverage = BoolProperty(
    # Sets whether this pass will use 'alpha to coverage', a way to multisample alpha
    # texture edges so they blend more seamlessly with the background. This facility
    # is typically only available on cards from around 2006 onwards, but it is safe to
    # enable it anyway - Ogre will just ignore it if the hardware does not support it.
    # The common use for alpha to coverage is foliage rendering and chain-link fence style textures.
    name='multisample alpha edges',
    default=False)
bpy.types.Material.ogre_light_scissor = BoolProperty(
    # This option is usually only useful if this pass is an additive lighting pass, and is
    # at least the second one in the technique. Ie areas which are not affected by the current
    # light(s) will never need to be rendered. If there is more than one light being passed to
    # the pass, then the scissor is defined to be the rectangle which covers all lights in screen-space.
    # Directional lights are ignored since they are infinite. This option does not need to be specified
    # if you are using a standard additive shadow mode, i.e. SHADOWTYPE_STENCIL_ADDITIVE or
    # SHADOWTYPE_TEXTURE_ADDITIVE, since it is the default behaviour to use a scissor for each additive
    # shadow pass. However, if you're not using shadows, or you're using Integrated Texture Shadows
    # where passes are specified in a custom manner, then this could be of use to you.
    name='light scissor',
    default=False)
bpy.types.Material.ogre_light_clip_planes = BoolProperty(
    name='light clip planes',
    default=False)
bpy.types.Material.ogre_normalise_normals = BoolProperty(
    name='normalise normals',
    default=False,
    description="Scaling objects causes normals to also change magnitude, which can throw off your lighting calculations. By default, the SceneManager detects this and will automatically re-normalise normals for any scaled object, but this has a cost. If you'd prefer to control this manually, call SceneManager::setNormaliseNormalsOnScale(false) and then use this option on materials which are sensitive to normals being resized.")
bpy.types.Material.ogre_lighting = BoolProperty(
    # Sets whether or not dynamic lighting is turned on for this pass or not. If lighting is turned off,
    # all objects rendered using the pass will be fully lit. This attribute has no effect if a vertex program is used.
    name='dynamic lighting',
    default=True)
bpy.types.Material.ogre_colour_write = BoolProperty(
    # If colour writing is off no visible pixels are written to the screen during this pass. You might think
    # this is useless, but if you render with colour writing off, and with very minimal other settings,
    # you can use this pass to initialise the depth buffer before subsequently rendering other passes which
    # fill in the colour data. This can give you significant performance boosts on some newer cards, especially
    # when using complex fragment programs, because if the depth check fails then the fragment program is never run.
    name='color-write',
    default=True)
bpy.types.Material.use_fixed_pipeline = BoolProperty(
    # Fixed pipeline is oldschool
    # todo: whats the meaning of this?
    name='fixed pipeline',
    default=True)
bpy.types.Material.use_material_passes = BoolProperty(
    # hidden option - gets turned on by operator
    # todo: What is a hidden option, is this needed?
    name='use ogre extra material passes (layers)',
    default=False)
bpy.types.Material.use_in_ogre_material_pass = BoolProperty(
    name='Layer Toggle',
    default=True)
bpy.types.Material.use_ogre_advanced_options = BoolProperty(
    name='Show Advanced Options',
    default=False)
bpy.types.Material.use_ogre_parent_material = BoolProperty(
    name='Use Script Inheritance',
    default=False)
bpy.types.Material.ogre_parent_material = EnumProperty(
    name="Script Inheritence",
    description='ogre parent material class', #default='NONE',
    items=[])
bpy.types.Material.ogre_polygon_mode = EnumProperty(
    name='faces draw type',
    description="ogre face draw mode",
    items=[ ('solid', 'solid', 'SOLID'),
            ('wireframe', 'wireframe', 'WIREFRAME'),
            ('points', 'points', 'POINTS') ],
    default='solid')
bpy.types.Material.ogre_shading = EnumProperty(
    name='hardware shading',
    description="Sets the kind of shading which should be used for representing dynamic lighting for this pass.",
    items=[ ('flat', 'flat', 'FLAT'),
            ('gouraud', 'gouraud', 'GOURAUD'),
            ('phong', 'phong', 'PHONG') ],
    default='gouraud')
bpy.types.Material.ogre_cull_hardware = EnumProperty(
    name='hardware culling',
    description="If the option 'cull_hardware clockwise' is set, all triangles whose vertices are viewed in clockwise order from the camera will be culled by the hardware.",
    items=[ ('clockwise', 'clockwise', 'CLOCKWISE'),
            ('anticlockwise', 'anticlockwise', 'COUNTER CLOCKWISE'),
            ('none', 'none', 'NONE') ],
    default='clockwise')
bpy.types.Material.ogre_transparent_sorting = EnumProperty(
    name='transparent sorting',
    description="By default all transparent materials are sorted such that renderables furthest away from the camera are rendered first. This is usually the desired behaviour but in certain cases this depth sorting may be unnecessary and undesirable. If for example it is necessary to ensure the rendering order does not change from one frame to the next. In this case you could set the value to 'off' to prevent sorting.",
    items=[ ('on', 'on', 'ON'),
            ('off', 'off', 'OFF'),
            ('force', 'force', 'FORCE ON') ],
    default='on')
bpy.types.Material.ogre_illumination_stage = EnumProperty(
    name='illumination stage',
    description='When using an additive lighting mode (SHADOWTYPE_STENCIL_ADDITIVE or SHADOWTYPE_TEXTURE_ADDITIVE), the scene is rendered in 3 discrete stages, ambient (or pre-lighting), per-light (once per light, with shadowing) and decal (or post-lighting). Usually OGRE figures out how to categorise your passes automatically, but there are some effects you cannot achieve without manually controlling the illumination.',
    items=[ ('', '', 'autodetect'),
            ('ambient', 'ambient', 'ambient'),
            ('per_light', 'per_light', 'lights'),
            ('decal', 'decal', 'decal') ],
    default=''
)

_ogre_depth_func =  [
    ('less_equal', 'less_equal', '<='),
    ('less', 'less', '<'),
    ('equal', 'equal', '=='),
    ('not_equal', 'not_equal', '!='),
    ('greater_equal', 'greater_equal', '>='),
    ('greater', 'greater', '>'),
    ('always_fail', 'always_fail', 'false'),
    ('always_pass', 'always_pass', 'true'),
]

bpy.types.Material.ogre_depth_func = EnumProperty(
    items=_ogre_depth_func,
    name='depth buffer function',
    description='If depth checking is enabled (see depth_check) a comparison occurs between the depth value of the pixel to be written and the current contents of the buffer. This comparison is normally less_equal, i.e. the pixel is written if it is closer (or at the same distance) than the current contents',
    default='less_equal')

_ogre_scene_blend_ops =  [
    ('add', 'add', 'DEFAULT'),
    ('subtract', 'subtract', 'SUBTRACT'),
    ('reverse_subtract', 'reverse_subtract', 'REVERSE SUBTRACT'),
    ('min', 'min', 'MIN'),
    ('max', 'max', 'MAX'),
]

bpy.types.Material.ogre_scene_blend_op = EnumProperty(
    items=_ogre_scene_blend_ops,
    name='scene blending operation',
    description='This directive changes the operation which is applied between the two components of the scene blending equation',
    default='add')

_ogre_scene_blend_types =  [
    ('one zero', 'one zero', 'DEFAULT'),
    ('alpha_blend', 'alpha_blend', "The alpha value of the rendering output is used as a mask. Equivalent to 'scene_blend src_alpha one_minus_src_alpha'"),
    ('add', 'add', "The colour of the rendering output is added to the scene. Good for explosions, flares, lights, ghosts etc. Equivalent to 'scene_blend one one'."),
    ('modulate', 'modulate', "The colour of the rendering output is multiplied with the scene contents. Generally colours and darkens the scene, good for smoked glass, semi-transparent objects etc. Equivalent to 'scene_blend dest_colour zero'"),
    ('colour_blend', 'colour_blend', 'Colour the scene based on the brightness of the input colours, but dont darken. Equivalent to "scene_blend src_colour one_minus_src_colour"'),
]
for mode in 'dest_colour src_colour one_minus_dest_colour dest_alpha src_alpha one_minus_dest_alpha one_minus_src_alpha'.split():
    _ogre_scene_blend_types.append( ('one %s'%mode, 'one %s'%mode, '') )
del mode

bpy.types.Material.ogre_scene_blend = EnumProperty(
    items=_ogre_scene_blend_types,
    name='scene blend',
    description='blending operation of material to scene',
    default='one zero')

## FAQ

_faq_ = '''

Q: I have hundres of objects, is there a way i can merge them on export only?
A: Yes, just add them to a group named starting with "merge", or link the group.

Q: Can i use subsurf or multi-res on a mesh with an armature?
A: Yes.

Q: Can i use subsurf or multi-res on a mesh with shape animation?
A: No.

Q: I don't see any objects when i export?
A: You must select the objects you wish to export.

Q: I don't see my animations when exported?
A: Make sure you created an NLA strip on the armature.

Q: Do i need to bake my IK and other constraints into FK on my armature before export?
A: No.

'''

## DOCUMENTATION
''' todo: Update the nonsense C:\Tundra2 paths from defaul config and fix this doc.
    Additionally point to some doc how to build opengl only version on windows if that really is needed and
    remove the old Tundra 7z link. '''

_doc_installing_ = '''
Installing:
    Installing the Addon:
        You can simply copy io_export_ogreDotScene.py to your blender installation under blender/2.6x/scripts/addons/
        and enable it in the user-prefs interface (CTRL+ALT+U)
        Or you can use blenders interface, under user-prefs, click addons, and click 'install-addon'
        (its a good idea to delete the old version first)

    Required:
        1. Blender 2.63

        2. Install Ogre Command Line tools to the default path: C:\\OgreCommandLineTools from http://www.ogre3d.org/download/tools
            * These tools are used to create the binary Mesh from the .xml mesh generated by this plugin.
            * Linux users may use above and Wine, or install from source, or install via apt-get install ogre-tools.

    Optional:
        3. Install NVIDIA DDS Legacy Utilities - Install them to default path.
            * http://developer.nvidia.com/object/dds_utilities_legacy.html
            * Linux users will need to use Wine.

        4. Install Image Magick
            * http://www.imagemagick.org

        5. Copy OgreMeshy to C:\\OgreMeshy
            * If your using 64bit Windows, you may need to download a 64bit OgreMeshy
            * Linux copy to your home folder.

        6. realXtend Tundra
            * For latest Tundra releases see http://code.google.com/p/realxtend-naali/downloads/list
              - You may need to tweak the config to tell your Tundra path or install to C:\Tundra2
            * Old OpenGL only build can be found from http://blender2ogre.googlecode.com/files/realxtend-Tundra-2.1.2-OpenGL.7z
              - Windows: extract to C:\Tundra2
              - Linux: extract to ~/Tundra2
'''

## Options

AXIS_MODES =  [
    ('xyz', 'xyz', 'no swapping'),
    ('xz-y', 'xz-y', 'ogre standard'),
    ('-xzy', '-xzy', 'non standard'),
]

from . import config

# Make default material for missing materials:
# * Red flags for users so they can quickly see what they forgot to assign a material to.
# * Do not crash if no material on object - thats annoying for the user.

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

from .util import *
from .xml import *
from .report import *

Report = ReportSingleton()

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

## OgreMeshy

class OgreMeshyPreviewOp(bpy.types.Operator):
    '''helper to open ogremeshy'''
    bl_idname = 'ogremeshy.preview'
    bl_label = "opens ogremeshy in a subprocess"
    bl_options = {'REGISTER'}
    preview = BoolProperty(name="preview", description="fast preview", default=True)
    groups = BoolProperty(name="preview merge groups", description="use merge groups", default=False)
    mesh = BoolProperty(name="update mesh", description="update mesh (disable for fast material preview", default=True)

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type in ('MESH','EMPTY') and context.mode != 'EDIT_MESH':
            if context.active_object.type == 'EMPTY' and context.active_object.dupli_type != 'GROUP':
                return False
            else:
                return True

    def execute(self, context):
        Report.reset()
        Report.messages.append('running %s' %CONFIG['OGRE_MESHY'])

        if sys.platform.startswith('linux'):
            # If OgreMeshy ends with .exe, set the path for preview meshes to
            # the user's wine directory, otherwise to /tmp.
            if CONFIG['OGRE_MESHY'].endswith('.exe'):
                path = '%s/.wine/drive_c/tmp' % os.environ['HOME']
            else:
                path = '/tmp'
        elif sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
            path = '/tmp'
        else:
            path = 'C:\\tmp'

        mat = None
        mgroup = merged = None
        umaterials = []

        if context.active_object.type == 'MESH':
            mat = context.active_object.active_material
        elif context.active_object.type == 'EMPTY': # assume group
            obs = []
            for e in context.selected_objects:
                if e.type != 'EMPTY' and e.dupli_group: continue
                grp = e.dupli_group
                subs = []
                for o in grp.objects:
                    if o.type=='MESH': subs.append( o )
                if subs:
                    m = merge_objects( subs, transform=e.matrix_world )
                    obs.append( m )
            if obs:
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
            elif len(context.selected_objects)>1 and context.selected_objects:
                merged = merge_objects( context.selected_objects )

            if mgroup:
                for ob in mgroup.objects:
                    nmats = dot_mesh( ob, path=path )
                    for m in nmats:
                        if m not in umaterials: umaterials.append( m )
                MeshMagick.merge( mgroup, path=path, force_name='preview' )
            elif merged:
                umaterials = dot_mesh( merged, path=path, force_name='preview' )
            else:
                umaterials = dot_mesh( context.active_object, path=path, force_name='preview' )

        if mat or umaterials:
            #CONFIG['TOUCH_TEXTURES'] = True
            #CONFIG['PATH'] = path   # TODO deprecate
            data = ''
            for umat in umaterials:
                data += generate_material( umat, path=path, copy_programs=True, touch_textures=True ) # copies shader programs to path
            f=open( os.path.join( path, 'preview.material' ), 'wb' )
            f.write( bytes(data,'utf-8') ); f.close()

        if merged: context.scene.objects.unlink( merged )

        if sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
            if CONFIG['OGRE_MESHY'].endswith('.exe'):
                cmd = ['wine', CONFIG['OGRE_MESHY'], 'c:\\tmp\\preview.mesh' ]
            else:
                cmd = [CONFIG['OGRE_MESHY'], '/tmp/preview.mesh']
            print( cmd )
            #subprocess.call(cmd)
            subprocess.Popen(cmd)
        else:
            #subprocess.call([CONFIG_OGRE_MESHY, 'C:\\tmp\\preview.mesh'])
            subprocess.Popen( [CONFIG['OGRE_MESHY'], 'C:\\tmp\\preview.mesh'] )

        Report.show()
        return {'FINISHED'}

## Ogre Documentation to UI

_OGRE_DOCS_ = []
def ogredoc( cls ):
    tag = cls.__name__.split('_ogredoc_')[-1]
    cls.bl_label = tag.replace('_', ' ')
    _OGRE_DOCS_.append( cls )
    return cls

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

'''

@ogredoc
class _ogredoc_Bugs( INFO_MT_ogre_helper ):
    mydoc = '''
Known Issues:
    . shape animation breaks when using modifiers that change the vertex count
        (Any modifier that changes the vertex count is bad with shape anim or armature anim)
    . never rename the nodes created by enabling Ogre-Material-Layers
    . never rename collision proxy meshes created by the Collision Panel
    . lighting in Tundra is not excatly the same as in Blender
Tundra Streaming:
    . only supports streaming transform of up to 10 objects selected objects
    . the 3D view must be shown at the time you open Tundra
    . the same 3D view must be visible to stream data to Tundra
    . only position and scale are updated, a bug on the Tundra side prevents rotation update
    . animation playback is broken if you rename your NLA strips after opening Tundra
'''

# Ogre v1.7 Doc

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
    # custom user props
    for prop in mesh.items():
        propname, propvalue = prop
        if not propname.startswith('_'):
            user = doc.createElement('user_data')
            o.appendChild( user )
            user.setAttribute( 'name', propname )
            user.setAttribute( 'value', str(propvalue) )
            user.setAttribute( 'type', type(propvalue).__name__ )

## MeshMagick

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

## Ogre Command Line Tools Documentation

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

## Ogre Command Line Tools

def OgreXMLConverter( infile, has_uvs=False ):
    # todo: Show a UI dialog to show this error. It's pretty fatal for normal usage.
    # We should show how to configure the converter location in config panel or tell the default path.
    exe = CONFIG['OGRETOOLS_XML_CONVERTER']
    if not os.path.isfile( exe ):
        print( 'WARNING: can not find OgreXMLConverter (can not convert XXX.mesh.xml to XXX.mesh' )
        return

    basicArguments = ''

    # LOD generation with OgreXMLConverter tool does not work. Currently the mesh files are generated
    # manually and referenced in the main mesh file.
    #if CONFIG['lodLevels']:
    #    basicArguments += ' -l %s -v %s -p %s' %(CONFIG['lodLevels'], CONFIG['lodDistance'], CONFIG['lodPercent'])

    if CONFIG['nuextremityPoints'] > 0:
        basicArguments += ' -x %s' %CONFIG['nuextremityPoints']

    if not CONFIG['generateEdgeLists']:
        basicArguments += ' -e'

    # note: OgreXmlConverter fails to convert meshes without UVs
    if CONFIG['generateTangents'] and has_uvs:
        basicArguments += ' -t'
        if CONFIG['tangentSemantic']:
            basicArguments += ' -td %s' %CONFIG['tangentSemantic']
        if CONFIG['tangentUseParity']:
            basicArguments += ' -ts %s' %CONFIG['tangentUseParity']
        if CONFIG['tangentSplitMirrored']:
            basicArguments += ' -tm'
        if CONFIG['tangentSplitRotated']:
            basicArguments += ' -tr'
    if not CONFIG['reorganiseBuffers']:
        basicArguments += ' -r'
    if not CONFIG['optimiseAnimations']:
        basicArguments += ' -o'

    # Make xml converter print less stuff, comment this if you want more debug info out
    basicArguments += ' -q'

    opts = '-log _ogre_debug.txt %s' %basicArguments
    path,name = os.path.split( infile )

    cmd = '%s %s' %(exe, opts)
    cmd = cmd.split() + [infile]
    subprocess.call( cmd )


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

        if _USE_TUNDRA_:
            row = layout.row(align=True)
            op = row.operator( 'tundra.preview', text='', icon='WORLD' )
            if TundraSingleton:
                op = row.operator( 'tundra.preview', text='', icon='META_CUBE' )
                op.EX_SCENE = False
                if not TundraSingleton.physics:
                    op = row.operator( 'tundra.start_physics', text='', icon='PLAY' )
                else:
                    op = row.operator( 'tundra.stop_physics', text='', icon='PAUSE' )
                op = row.operator( 'tundra.toggle_physics_debug', text='', icon='MOD_PHYSICS' )
                op = row.operator( 'tundra.exit', text='', icon='CANCEL' )

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

def export_menu_func_realxtend(self, context):
    op = self.layout.operator(INFO_OT_createRealxtendExport.bl_idname, text="realXtend Tundra (.txml and .mesh)")

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
    TOGGLE = True  #restore_minimal_interface()
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

def get_minimal_interface_classes():
    return INFO_OT_createOgreExport, INFO_OT_createRealxtendExport, OgreToggleInterfaceOp, MiniReport, INFO_HT_microheader

_USE_TUNDRA_ = False

def restore_minimal_interface():
    #if not hasattr( bpy.ops.ogre..   #always true
    for cls in get_minimal_interface_classes():
        try: bpy.utils.register_class( cls )
        except: pass
    return False

    try:
        bpy.utils.register_class( INFO_HT_microheader )
        for op in get_minimal_interface_classes(): bpy.utils.register_class( op )
        return False
    except:
        print( 'b2ogre minimal UI already setup' )
        return True

MyShaders = None

def register():
    print('Starting blender2ogre', v.version_str())
    global MyShaders, _header_, _USE_TUNDRA_
    #bpy.utils.register_module(__name__)    ## do not load all the ogre panels by default
    #_header_ = bpy.types.INFO_HT_header
    #bpy.utils.unregister_class(_header_)
    restore_minimal_interface()

    # only test for Tundra2 once - do not do this every panel redraw ##
    if os.path.isdir( CONFIG['TUNDRA_ROOT'] ): _USE_TUNDRA_ = True
    else: _USE_TUNDRA_ = False

    bpy.types.INFO_MT_file_export.append(export_menu_func_ogre)
    bpy.types.INFO_MT_file_export.append(export_menu_func_realxtend)

    bpy.utils.register_class(PopUpDialogOperator)

    if os.path.isdir( CONFIG['USER_MATERIALS'] ):
        scripts,progs = update_parent_material_path( CONFIG['USER_MATERIALS'] )
        for prog in progs:
            print('Ogre shader program', prog.name)
    else:
        print('[WARNING]: Invalid my-shaders path %s' % CONFIG['USER_MATERIALS'])

def unregister():
    print('Unloading blender2ogre', v.version_str())
    bpy.utils.unregister_module(__name__)
    try: bpy.utils.register_class(_header_)
    except: pass
    
    # If the addon is disabled while the UI is toggled, reset it for next time.
    # "Untoggling" it by setting the value to True seems a bit counter-intuitive.
    OgreToggleInterfaceOp.TOGGLE = True
    bpy.types.INFO_MT_file_export.remove(export_menu_func_ogre)
    bpy.types.INFO_MT_file_export.remove(export_menu_func_realxtend)
    # This seems to be not registered by the time this function is called.
    #bpy.utils.unregister_class(PopUpDialogOperator)


## Blender world panel options for EC_SkyX creation
## todo: EC_SkyX has changes a bit lately, see that
## all these options are still correct and valid
## old todo (?): Move to tundra.py

bpy.types.World.ogre_skyX = BoolProperty(
    name="enable sky", description="ogre sky",
    default=False
)
bpy.types.World.ogre_skyX_time = FloatProperty(
    name="Time Multiplier",
    description="change speed of day/night cycle",
    default=0.3,
    min=0.0, max=5.0
)
bpy.types.World.ogre_skyX_wind = FloatProperty(
    name="Wind Direction",
    description="change direction of wind",
    default=33.0,
    min=0.0, max=360.0
)
bpy.types.World.ogre_skyX_volumetric_clouds = BoolProperty(
    name="volumetric clouds", description="toggle ogre volumetric clouds",
    default=True
)
bpy.types.World.ogre_skyX_cloud_density_x = FloatProperty(
    name="Cloud Density X",
    description="change density of volumetric clouds on X",
    default=0.1,
    min=0.0, max=5.0
)
bpy.types.World.ogre_skyX_cloud_density_y = FloatProperty(
    name="Cloud Density Y",
    description="change density of volumetric clouds on Y",
    default=1.0,
    min=0.0, max=5.0
)

## Sky UI panel

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

## Public API (continued)

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

    MaterialScripts.reset_rna( callback=bpyShaders.on_change_parent_material )
    return scripts, progs

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

## Blender addon main entry point.
## Allows directly running by "blender --python blender2ogre.py"

if __name__ == "__main__":
    register()
