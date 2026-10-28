import bpy
from bpy.props import BoolProperty, EnumProperty
from .ogre.material import load_user_materials

load_user_materials()

## Physics / collision
bpy.types.Object.subcollision = BoolProperty(
    name="collision compound",
    description="Object is a collision proxy for its parent (legacy; objects named 'collision*' are detected as well)",
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
