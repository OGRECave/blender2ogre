import bpy
bpy.ops.preferences.addon_enable(module='io_ogre')
bpy.ops.ogre.export(filepath="test.scene")

# Regression test for issue #145: exporting a material with an image that only
# exists in memory (e.g. a generated image) must not crash the export.
import os
import tempfile

from io_ogre.ogre import scene
from io_ogre.ogre.material import dot_material
from io_ogre.report import Report

target_path = tempfile.mkdtemp(prefix="b2o_test_")

image = bpy.data.images.new("generated_texture", 4, 4)
image.generated_color = (1.0, 0.0, 1.0, 1.0)

material = bpy.data.materials.new("generated_texture")
material.use_nodes = True
node_tree = material.node_tree
bsdf = node_tree.nodes.get("Principled BSDF")
texture = node_tree.nodes.new("ShaderNodeTexImage")
texture.image = image
node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])

Report.errors.clear()
dot_material(material, target_path)

assert not Report.errors, "Material export reported errors: %s" % Report.errors
assert os.path.isfile(os.path.join(target_path, "generated_texture.png")), \
    "Generated image was not written to the target path"

# Regression test for issue #267: a hidden, unselected child named "collision*"
# is exported as the collision mesh of its parent, without becoming a node.
collision_path = tempfile.mkdtemp(prefix="b2o_collision_test_")

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0)
visual = bpy.context.active_object
visual.name = "rock"
visual.data.name = "collision_target"

bpy.ops.mesh.primitive_cube_add(size=1.0)
proxy = bpy.context.active_object
proxy.name = "collision." + visual.name
proxy.parent = visual
proxy.hide_set(True)
proxy.select_set(False)

# Only the visual object is selected for export, as in the usual workflow
bpy.ops.object.select_all(action='DESELECT')
visual.select_set(True)

Report.errors.clear()
scene.dot_scene(collision_path, scene_name="CollisionTest")
assert not Report.errors, "Collision export reported errors: %s" % Report.errors

with open(os.path.join(collision_path, "CollisionTest.scene")) as f:
    scene_xml = f.read()

collision_file = "collision_target_collision.mesh"
assert 'collisionFile="%s"' % collision_file in scene_xml, \
    "Collision proxy was not referenced by the visual entity"
assert os.path.isfile(os.path.join(collision_path, collision_file)), \
    "Collision proxy mesh was not written"
assert 'name="collision.' not in scene_xml, \
    "Collision proxy must not be exported as a scene node"
