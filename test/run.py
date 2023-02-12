import bpy
bpy.ops.preferences.addon_enable(module='io_ogre')
bpy.ops.ogre.export(filepath="test.scene")