import bpy
from bpy.props import BoolProperty, StringProperty, FloatProperty, IntProperty, EnumProperty
from .ogre.material import IMAGE_FORMATS, load_user_materials

load_user_materials()

## Rendering
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
bpy.types.Image.use_convert_format = BoolProperty(
    name='use convert format',
    default=False)
bpy.types.Image.convert_format = EnumProperty(
    name='convert to format',
    description='converts to image format using imagemagick',
    items=IMAGE_FORMATS,
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

## Materials
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
    description='ogre parent material class',
    items=[ ('none', 'none', 'NONE') ],
    default='none')

bpy.types.World.ogre_skyX = BoolProperty(
    name="enable sky", description="ogre sky",
    default=False)
bpy.types.World.ogre_skyX_time = FloatProperty(
    name="Time Multiplier",
    description="change speed of day/night cycle",
    default=0.3,
    min=0.0, max=5.0)
bpy.types.World.ogre_skyX_wind = FloatProperty(
    name="Wind Direction",
    description="change direction of wind",
    default=33.0,
    min=0.0, max=360.0)
bpy.types.World.ogre_skyX_volumetric_clouds = BoolProperty(
    name="volumetric clouds", description="toggle ogre volumetric clouds",
    default=True)
bpy.types.World.ogre_skyX_cloud_density_x = FloatProperty(
    name="Cloud Density X",
    description="change density of volumetric clouds on X",
    default=0.1,
    min=0.0, max=5.0)
bpy.types.World.ogre_skyX_cloud_density_y = FloatProperty(
    name="Cloud Density Y",
    description="change density of volumetric clouds on Y",
    default=1.0,
    min=0.0, max=5.0)
