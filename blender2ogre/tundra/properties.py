import bpy
from bpy.props import BoolProperty, StringProperty, FloatProperty, IntProperty, EnumProperty

# Avatar?

bpy.types.Object.use_avatar = BoolProperty(
    name='enable avatar',
    description='enables EC_Avatar',
    default=False)
bpy.types.Object.avatar_reference = StringProperty(
    name='avatar reference',
    description='sets avatar reference URL',
    maxlen=128,
    default='')

# Tundra IDs

bpy.types.Object.uid = IntProperty(
    name="unique ID",
    description="unique ID for Tundra",
    default=0, min=0, max=2**14)

