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

import os, sys, logging

bl_info = {
    "name": "OGRE Exporter (.scene, .mesh, .skeleton) and RealXtend (.txml)",
    "author": "Brett, S.Rombauts, F00bar, Waruck, Mind Calamity, Mr.Magne, Jonne Nauha, vax456",
    "version": (0, 6, 1),
    "blender": (2, 7, 1),
    "location": "File > Export...",
    "description": "Export to Ogre xml and binary formats",
    "wiki_url": "https://bitbucket.org/MindCalamity/blender2ogre/overview",
    "tracker_url": "https://bitbucket.org/MindCalamity/blender2ogre/issues?status=new&status=open",
    "category": "Import-Export"
}

# import the plugin directory and setup the plugin
import bpy
from . import config
from . import properties
from . import ui

def register():
    logging.info('Starting io_ogre %s', bl_info["version"])
    # the ui modules define auto_register functions that
    # return classes that should be loaded by the plugin
    for clazz in ui.auto_register(True):
        bpy.utils.register_class(clazz)

def unregister():
    logging.info('Unloading io_ogre %s', bl_info["version"])
    for clazz in ui.auto_register(False):
        bpy.utils.unregister_class(clazz)

if __name__ == "__main__":
    register()

    try:
        index = sys.argv.index("--")
        from . import auto
        auto.export(sys.argv[index+1:])
    except ValueError:
        pass
