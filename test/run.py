import bpy
bpy.ops.preferences.addon_enable(module='io_ogre')
bpy.ops.ogre.export(filepath="test.scene")

# Regression test for issue #145: exporting a material with an image that only
# exists in memory (e.g. a generated image) must not crash the export.
import os
import tempfile

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
