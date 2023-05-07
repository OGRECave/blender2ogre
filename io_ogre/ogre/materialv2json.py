
# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    # ...so we need to reload our submodule(s) using importlib
    import importlib
    if "config" in locals():
        importlib.reload(config)
    if "util" in locals():
        importlib.reload(util)
    if "report" in locals():
        importlib.reload(report)
    if "material" in locals():
        importlib.reload(material)

# This is only relevant on first run, on later reloads those modules
# are already in locals() and those statements do not do anything.
import logging, os, shutil, tempfile, json
from .. import config
from .. import util
from ..report import Report
from .material import material_name, ShaderImageTextureWrapper, gather_metallic_roughness_texture
from bpy_extras import node_shader_utils
import bpy.path

logger = logging.getLogger('materialv2json')

def dot_materialsv2json(materials, path=None, separate_files=True, prefix="mats", **kwargs):
    """Output v2 .material.json files"""
    if not materials:
        logger.warn("No materials, not writing .materials.json")

    if not path:
        path = tempfile.mkdtemp(prefix="ogre_io")

    generator = OgreMaterialv2JsonGenerator(materials, path, separate_files, prefix)
    generator.process_materials()


class OgreMaterialv2JsonGenerator(object):
    """Generator for v2 Json materials"""

    def __init__(self, materials, target_path, separate_files=True, prefix=''):
        self.materials = materials
        self.target_path = target_path
        self.separate_files = separate_files
        self.prefix = prefix
        self.convert_set = set()
        self.copy_set = set()
        self.remove_set = set()

    def process_materials(self):
        """Process all the materials, create the output json and copy textures"""
        if self.separate_files:
            for mat in self.materials:
                datablock = self.generate_pbs_datablock(mat)
                dst_filename = os.path.join(self.target_path, "{}.material.json".format(material_name(mat)))
                logger.info("Writing material '{}'".format(dst_filename))
                try:
                    with open(dst_filename, 'w') as fp:
                        json.dump({"pbs": {material_name(mat): datablock}}, fp, indent=2, sort_keys=True)
                    Report.materials.append(material_name(mat))
                except Exception as e:
                    logger.error("Unable to create material file '{}'".format(dst_filename))
                    Report.errors.append("Unable to create material file '{}'".format(dst_filename))
                    logger.error(e)
        else:
            dst_filename = os.path.join(self.target_path, "{}.material.json".format(self.prefix))
            fileblock = {"pbs": {}}
            for mat in self.materials:
                logger.info("Preparing material '{}' for file '{}".format(material_name(mat), dst_filename))
                fileblock["pbs"][material_name(mat)] = self.generate_pbs_datablock(mat)
            try:
                with open(dst_filename, 'w') as fp:
                    json.dump(fileblock, fp, indent=2, sort_keys=True)
            except Exception as e:
                logger.error("Unable to create material file '{}'".format(dst_filename))
                Report.errors.append("Unable to create material file '{}'".format(dst_filename))
                logger.error(e)

        self.copy_textures()

    def generate_pbs_datablock(self, material):
        """Generate a PBS datablock for a material.

        # PBS datablock generator
        based on the Ogre Next documentation.
        doc: https://ogrecave.github.io/ogre-next/api/latest/hlmspbsdatablockref.html

        ## Metallic Workflow
        Metalness texture fetching expects a single image with the metal
        texture in the Blue channel and the roughness texture in the Green
        channel. This is in line with the glTF standard setup.

        ## Specular Workflow
        Unsupported.


        ## Unsupported features

        ### fresnel
        This is used in the Specular workflows supported by Ogre. Right now we
        only support the metallic workflow.

        ### blendblock
        Blendblocks are used for advanced effects and don't fit into the
        standard Blender workflow. One commmon use would be to have better
        alpha blending on complex textures. Limit of 32 blend blocks at
        runtime also means we shouldn't "just generate them anyway."
        doc: https://ogrecave.github.io/ogre-next/api/latest/hlmsblendblockref.html

        ### macroblock
        Macroblocks are used for advanced effects and don't fit into the
        standard Blender workflow. One common use would be to render a skybox
        behind everything else in a scene. Limit of 32 macroblocks at runtime
        also means we shouldn't "just generate them anyway."
        doc: https://ogrecave.github.io/ogre-next/api/latest/hlmsmacroblockref.html

        ### sampler
        Samplerblocks are used for advanced texture handling like filtering,
        addressing, LOD, etc. These settings have signifigant visual and
        performance effects. Limit of 32 samplerblocks at runtime also means
        we shouldn't "just generate them anyway."

        ### recieve_shadows
        No receive shadow setting in Blender 2.8+ but was available in 2.79.
        We leave this unset which defaults to true. Maybe add support in
        the 2.7 branch?
        See: https://docs.blender.org/manual/en/2.79/render/blender_render/materials/properties/shadows.html#shadow-receiving-object-material
        ### shadow_const_bias
        Leave shadow const bias undefined to default. It is usually used to
        fix specific self-shadowing issues and is an advanced feature.

        ### brdf
        Leave brdf undefined to default. This setting has huge visual and
        performance impacts and is for specific use cases.
        doc: https://ogrecave.github.io/ogre-next/api/latest/hlmspbsdatablockref.html#dbParamBRDF

        ### reflection
        Leave reflection undefined to default. In most cases for reflections
        users will want to use generated cubemaps in-engine.

        ### detail_diffuse[0-3]
        Layered diffuse maps for advanced effects.

        ### detail_normal[0-3]
        Layered normal maps for advanced effects.

        ### detail_weight
        Texture acting as a mask for the detail maps.
        """

        logger.debug("Generating PBS datablock for '{}'".format(material.name))
        bsdf = node_shader_utils.PrincipledBSDFWrapper(material)

        # Initialize datablock
        datablock = {}
        logger.debug("Diffuse params")
        # Set up the diffuse paramenters
        datablock["diffuse"] = {
            "value": bsdf.base_color[0:3]
        }
        tex_filename = self.prepare_texture(bsdf.base_color_texture)
        if tex_filename:
            datablock["diffuse"]["texture"] = tex_filename

        # Set up emissive parameters
        tex_filename = self.prepare_texture(bsdf.emission_color_texture)
        if tex_filename:
            logger.debug("Emissive params")
            datablock["emissive"] = {
                "lightmap": False, # bsdf.emission_strength_texture not supported in Blender < 2.9.0
                "value": bsdf.emission_color[0:3]
            }
            datablock["emissive"]["texture"] = tex_filename


        # Set up metalness parameters
        tex_filename = self.prepare_texture(gather_metallic_roughness_texture(bsdf), channel=2)
        logger.debug("Metallic params")
        datablock["metalness"] = {
            "value": bsdf.metallic
        }
        if tex_filename:
            datablock["metalness"]["texture"] = tex_filename

        # Set up normalmap parameters, only if texture is present
        tex_filename = self.prepare_texture(bsdf.normalmap_texture)
        if tex_filename:
            logger.debug("Normalmap params")
            datablock["normal"] = {
                "value": bsdf.normalmap_strength
            }
            datablock["normal"]["texture"] = tex_filename

        # Set up roughness parameters
        tex_filename = self.prepare_texture(gather_metallic_roughness_texture(bsdf), channel=1)
        logger.debug("Roughness params")
        datablock["roughness"] = {
            "value": bsdf.roughness
        }
        if tex_filename:
            datablock["roughness"]["texture"] = tex_filename

        # Set up specular parameters
        logger.debug("Specular params")
        datablock["specular"] = {
            "value": material.specular_color[0:3]
        }
        tex_filename = self.prepare_texture(bsdf.specular_texture)
        if tex_filename:
            datablock["specular"]["texture"] = tex_filename

        # Set up transparency parameters, only if texture is present
        logger.debug("Transparency params")
        tex_filename = self.prepare_texture(bsdf.alpha_texture)
        if tex_filename:
            if tex_filename != datablock.get("diffuse", {}).get("texture", None):
                logger.warning("Alpha texture on material '{}' is not the same as "
                    "the diffuse texture! Probably will not work as expected.".format(
                    material.name))
            datablock["alpha_test"] = ["greater_equal", material.alpha_threshold]
        if bsdf.alpha != 1.0:
            transparency_mode = "None" # NOTE: This is an arbitrary mapping
            if material.blend_method == "CLIP":
                transparency_mode = "Fade"
            elif material.blend_method == "HASHED":
                transparency_mode = "Fade"
            elif material.blend_method == "BLEND":
                transparency_mode = "Transparent"

            datablock["transparency"] = {
                "mode": transparency_mode,
                "use_alpha_from_textures": True,    # DEFAULT
                "value": bsdf.alpha
            }
            # UNSUSED IN OGRE datablock["transparency"]["texture"] = tex_filename

        # Backface culling
        datablock["two_sided"] = not material.use_backface_culling

        # TODO: workflow for specular_fresnel, specular_ogre (default)
        if datablock.get("metalness", None):
            datablock["workflow"] = "metallic"
            try:
                datablock.pop("fresnel") # No fresnel if workflow is metallic
            except KeyError: pass

        return datablock

    def prepare_texture(self, tex, channel=None):
        """Prepare a texture for use

        channel is None=all channels, 0=red 1=green 2=blue
        """
        if not (tex and tex.image):
            return None

        src_filename = bpy.path.abspath(tex.image.filepath or tex.image.name)
        dst_filename = bpy.path.basename(src_filename)
        dst_filename = os.path.splitext(dst_filename)[0]
        if channel is not None :
            dst_filename="{}_c{}".format(dst_filename, channel)

        # pick target file format, prefer image format unless forced
        src_format = tex.image.file_format.lower()
        dst_format = src_format
        if config.get("FORCE_IMAGE_FORMAT") != "NONE":
            dst_format = config.get("FORCE_IMAGE_FORMAT")
        dst_filename = "{}.{}".format(dst_filename, dst_format)
        dst_filename = os.path.join(self.target_path, dst_filename)

        if tex.image.packed_file:
            # save the image out to a temporary file
            src_filename = "{}_{}".format(dst_filename, os.path.split(src_filename)[-1])
            self.remove_set.add(src_filename)
            orig_filepath = tex.image.filepath
            tex.image.filepath = src_filename
            tex.image.save()
            tex.image.filepath = orig_filepath

        if not os.path.isfile(src_filename):
            logger.error("Cannot find source image: '{}'".format(src_filename))
            Report.errors.append("Cannot find source image: '{}'".format(src_filename))
            return

        if src_format != dst_format or channel is not None:
            # using extensions to determine filetype? gross
            self.convert_set.add((tex.image, src_filename, dst_filename, channel))
        else:
            self.copy_set.add((src_filename, dst_filename))

        return os.path.split(dst_filename)[-1]

    def copy_textures(self):
        """Copy and/or convert textures from previous prepare_texture() calls"""
        for image, src_filename, dst_filename, channel in self.convert_set:
            logger.info("ImageMagick: {} -> {}".format(src_filename, dst_filename))
            util.image_magick(image, src_filename, dst_filename, separate_channel=channel)
        self.convert_set.clear()

        for src_filename, dst_filename in self.copy_set:
            if os.path.isfile(dst_filename):
                src_stat = os.stat(src_filename)
                dst_stat = os.stat(dst_filename)
                if src_stat.st_size == dst_stat.st_size and \
                    src_stat.st_mtime == dst_stat.st_mtime:
                    logger.info("Skipping '{}', file is up to date".format(dst_filename))
                    continue
            logger.info("Copying: {} -> {}".format(src_filename, dst_filename))
            shutil.copy2(src_filename, dst_filename)
        self.copy_set.clear()

        for filename in self.remove_set:
            os.unlink(filename)
        self.remove_set.clear()

