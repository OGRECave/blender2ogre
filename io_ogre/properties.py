import bpy
from bpy.props import BoolProperty, EnumProperty
from .ogre.material import load_user_materials

load_user_materials()

## Physics / collision
_collision_modes =  [
    ('NONE', 'NONE', 'no collision'),
    ('PRIMITIVE', 'PRIMITIVE', 'primitive collision type'),
    ('MESH', 'MESH', 'triangle-mesh or convex-hull collision type'),
    ('DECIMATED', 'DECIMATED', 'auto-decimated collision type'),
    ('COMPOUND', 'COMPOUND', 'children primitive compound collision type'),
    ('TERRAIN', 'TERRAIN', 'terrain (height map) collision type'),
]

bpy.types.Object.collision_mode = EnumProperty(
    items = _collision_modes,
    name = 'primary collision mode',
    description='collision mode',
    default='NONE')
bpy.types.Object.subcollision = BoolProperty(
    name="collision compound",
    description="member of a collision compound",
    default=False)

## Materials
bpy.types.Material.use_in_ogre_material_pass = BoolProperty(
    name='Layer Toggle',
    default=True)
bpy.types.Material.use_ogre_parent_material = BoolProperty(
    name='Use Script Inheritance',
    default=False)
bpy.types.Material.ogre_parent_material = EnumProperty(
    name="Script Inheritence",
    description='ogre parent material class',
    items=[ ('none', 'none', 'NONE') ],
    default='none')
