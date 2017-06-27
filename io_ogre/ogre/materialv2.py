# coding: utf-8
from itertools import chain
from os.path import join, split, splitext
import tempfile
import os
import shutil
import logging

import bpy

from .. import shader
from ..util import material_name, get_image_textures, texture_image_path, is_image_postprocessed
from .. import config 
from .material_templates import PBS_TEMPLATE, PBS_TEMPLATE_TEXTURED

class OgreMaterialGeneratorBase(object):
    def __init__(self, material, prefix=''):
        self.material = material
        self.material_name = material_name(self.material,prefix=prefix)        
        self.passes = []
        self.textures = []
        if material.node_tree:
            nodes = shader.get_subnodes( self.material.node_tree, type='MATERIAL_EXT' )
            for node in nodes:
                if node.material:
                    self.passes.append( node.material )
        
    def copy_programs(self,path):
        pass

    def copy_textures(self, target_path):
        slots = get_image_textures(self.material) + list(chain([get_image_textures(mat) for mat in self.passes]))
        for slot in slots:
            self.copy_texture(slot, target_path)
            

    def change_ext( self, name, image ):
        name_no_ext, _ = splitext(name)
        if image.convert_format != 'NONE':
            name = name_no_ext + "." + image.convert_format
        if config.get('FORCE_IMAGE_FORMAT') != 'NONE':
            name = name_no_ext + "." + config.get('FORCE_IMAGE_FORMAT')
        return name
            

    def copy_texture(self, slot, target_path):
        if not slot:
            return

        origin_filepath = texture_image_path(slot.texture)
        if origin_filepath == None:
            return

        tmp_filepath = None
        updated_image = False
        if origin_filepath == '.':
            # a is a packed png
            origin_filepath = slot.texture.image.filepath
            _, ext = splitext(origin_filepath)
            tmp_filepath = tempfile.mkstemp(suffix=ext)
            slot.texture.image.filepath = tmp_filepath 
            slot.texture.image.save()
            slot.texture.image.filepath = origin_filepath
            updated_image = True

        _, target_file_ext = split(origin_filepath)
        target_file, ext = splitext(target_file_ext)

        if not tmp_filepath:
            _, tmp_filepath = tempfile.mkstemp(suffix=ext)

        target_file_ext = self.change_ext(target_file_ext, slot.texture.image)
        target_filepath = join(target_path, target_file_ext)
        self.textures.append(target_filepath)
        if not os.path.isfile(target_filepath):
            # or os.stat(target_filepath).st_mtime < os.stat( origin_filepath ).st_mtime:
            updated_image = True
            shutil.copyfile(origin_filepath, tmp_filepath)
        else:
            logging.info("skip copy (%s). texture is already up to date.", origin_filepath)

        if updated_image:
            if is_image_postprocessed(slot.texture.image):
                logging.info("magick (%s) -> (%s)", tmp_filepath, origin_filepath)
                util.image_magick(slot.texture, tmp_filepath, target_filepath)
            else:
                shutil.copyfile(tmp_filepath, target_filepath)
                logging.info("copy (%s)", origin_filepath)


    

class OgreMaterialGeneratorV2(OgreMaterialGeneratorBase):

    
    def generate(self):
        print(self.textures)
        material = ""
        use_texture = None
        if len(self.textures) > 1:
            logger.warning("More that one texture, material can t handle that.")
        if len(self.textures) >= 1:
            use_texture = os.path.basename(self.textures[0])

        f = self.material.specular_intensity
        s = self.material.specular_color
        specular = "%s %s %s"%(s.r*f, s.g*f, s.b*f)
        
        f = self.material.diffuse_intensity
        s = self.material.diffuse_color
        diffuse = "%s %s %s"%(s.r*f, s.g*f, s.b*f)
            
        if use_texture == None:
            material = PBS_TEMPLATE.format(
                material_name=self.material_name,
                roughness=0.4,
                fresnel=1.33,
                diffuse=diffuse,
                specular=specular,
            )
        else:
            material = PBS_TEMPLATE_TEXTURED.format(
                material_name=self.material_name,
                roughness=0.4,
                fresnel=1.33,
                diffuse=diffuse,
                specular=specular,
                texture_file=use_texture
            )
        return material


    
