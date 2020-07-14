import bpy
from bpy.props import BoolProperty, StringProperty, FloatProperty, IntProperty, EnumProperty
from .ogre.material import IMAGE_FORMATS, load_user_materials

load_user_materials()
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

# Materials
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

