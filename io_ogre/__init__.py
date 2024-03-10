# Copyright (C) 2010 Brett Hartshorn
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

bl_info = {
    "name": "OGRE Importer-Exporter (.scene, .mesh, .skeleton)",
    "author": "Brett, S.Rombauts, F00bar, Waruck, Mind Calamity, Mr.Magne, Jonne Nauha, vax456, Richard Plangger, Pavel Rojtberg, Guillermo Ojea Quintana",
    "version": (0, 8, 5),
    "blender": (2, 80, 0),
    "location": "File > Import and Export...",
    "description": "Import and Export to and from Ogre xml and binary formats",
    "wiki_url": "https://github.com/OGRECave/blender2ogre",
    "tracker_url": "https://github.com/OGRECave/blender2ogre/issues",
    "category": "Import-Export"
}

# https://blender.stackexchange.com/questions/2691/is-there-a-way-to-restart-a-modified-addon
# https://blender.stackexchange.com/questions/28504/blender-ignores-changes-to-python-scripts/28505
# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    # ...so we need to reload our submodule(s) using importlib
    import importlib
    if "config" in locals():
        importlib.reload(config)
    if "properties" in locals():
        importlib.reload(properties)
    if "ui" in locals():
        importlib.reload(ui)

# This is only relevant on first run, on later reloads those modules
# are already in locals() and those statements do not do anything.
from . import config
from . import properties
from . import ui

import os, sys, logging
from pprint import pprint
import bpy

# Import the plugin directory and setup the plugin
class Blender2OgreAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def apply_preferences_to_config(self, context):
        config.update_from_addon_preference(context)
        ui.update_meshpreview_button_visibility(True)

    IMAGE_MAGICK_CONVERT : bpy.props.StringProperty(
        name="IMAGE_MAGICK_CONVERT",
        subtype='FILE_PATH',
        default=config.CONFIG['IMAGE_MAGICK_CONVERT'],
        update=apply_preferences_to_config
    )
    OGRETOOLS_XML_CONVERTER : bpy.props.StringProperty(
        name="OGRETOOLS_XML_CONVERTER",
        subtype='FILE_PATH',
        default=config.CONFIG['OGRETOOLS_XML_CONVERTER'],
        update=apply_preferences_to_config
    )
    OGRETOOLS_MESH_UPGRADER : bpy.props.StringProperty(
        name="OGRETOOLS_MESH_UPGRADER",
        subtype='FILE_PATH',
        default=config.CONFIG['OGRETOOLS_MESH_UPGRADER'],
        update=apply_preferences_to_config
    )
    MESH_PREVIEWER : bpy.props.StringProperty(
        name="MESH_PREVIEWER",
        subtype='FILE_PATH',
        default=config.CONFIG['MESH_PREVIEWER'],
        update=apply_preferences_to_config
    )
    USER_MATERIALS : bpy.props.StringProperty(
        name="USER_MATERIALS",
        subtype='FILE_PATH',
        default=config.CONFIG['USER_MATERIALS'],
        update=apply_preferences_to_config
    )
    SHADER_PROGRAMS : bpy.props.StringProperty(
        name="SHADER_PROGRAMS",
        subtype='FILE_PATH',
        default=config.CONFIG['SHADER_PROGRAMS'],
        update=apply_preferences_to_config
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "OGRETOOLS_XML_CONVERTER")
        layout.prop(self, "OGRETOOLS_MESH_UPGRADER")
        layout.prop(self, "MESH_PREVIEWER")
        layout.prop(self, "IMAGE_MAGICK_CONVERT")
        layout.prop(self, "USER_MATERIALS")
        layout.prop(self, "SHADER_PROGRAMS")      

def register():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='[%(levelname)5s] %(message)s', datefmt='%H:%M:%S')

    logging.info('Starting io_ogre %s', bl_info["version"])
    
    # The UI modules define auto_register functions that
    # return classes that should be loaded by the plugin
    for clazz in ui.auto_register(True):
        bpy.utils.register_class(clazz)

    bpy.utils.register_class(Blender2OgreAddonPreferences)

    # Read user preferences
    config.update_from_addon_preference(bpy.context)

def unregister():
    logging.info('Unloading io_ogre %s', bl_info["version"])
    
    # Save the config
    config.save_config()
    
    # Unregister classes
    for clazz in ui.auto_register(False):
        bpy.utils.unregister_class(clazz)

    bpy.utils.unregister_class(Blender2OgreAddonPreferences)

if __name__ == "__main__":
    register()
