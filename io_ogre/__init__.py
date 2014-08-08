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

'''
CHANGELOG
    0.6.1
    * code refactored, tested to work with 2.71
    0.6.0
    * patched to work with 2.66.
    0.5.9
    * apply patch from Thomas for Blender 2.6x support
    0.5.8
    * Clean all names that will be used as filenames on disk. Adjust all places
      that use these names for refs instead of ob.name/ob.data.name. Replaced chars
      are \, /, :, *, ?, ", <, >, | and spaces. Tested on work with ogre 
      material, mesh and skeleton writing/refs inside the files and txml refs.
      Shows warning at final report if we had to resort to the renaming so user 
      can possibly rename the object.
    * Added silent auto update checks if blender2ogre was installed using
      the .exe installer. This will keep people up to date when new versions are out.
    * Fix tracker issue 48: Needs to check if outputting to /tmp or 
      ~/.wine/drive_c/tmp on Linux. Thanks to vax456 for providing the patch,
      added him to contributors. Preview mesh's are now placed under /tmp 
      on Linux systems if the OgreMeshy executable ends with .exe
    * Fix tracker issue 46: add operationtype to <submesh>
    * Implement a modal dialog that reports if material names have invalid
      characters and cant be saved on disk. This small popup will show until
      user presses left or right mouse (anywhere).
    * Fix tracker issue 44: XML Attributes not properly escaped in .scene file
    * Implemented reading OgreXmlConverter path from windows registry.
      The .exe installer will ship with certain tools so we can stop guessing
      and making the user install tools separately and setting up paths.
    * Fix bug that .mesh files were not generated while doing a .txml export.
      This was result of the late 2.63 mods that forgot to update object
      facecount before determining if mesh should be exported.
    * Fix bug that changed settings in the export dialog were forgotten when you
      re-exported without closing blender. Now settings should persist always
      from the last export. They are also stored to disk so the same settings
      are in use when if you restart Blender.
    * Fix bug that once you did a export, the next time the export location was
      forgotten. Now on sequential exports, the last export path is remembered in
      the export dialog.
    * Remove all local:// from asset refs and make them relative in .txml export.
      Having relative refs is the best for local preview and importing the txml
      to existing scenes.
    * Make .material generate what version of this plugins was used to generate
      the material file. Will be helpful in production to catch things.
      Added pretty printing line endings so the raw .material data is easier to read.
    * Improve console logging for the export stages. Run Blender from
      cmd prompt to see this information.
    * Clean/fix documentation in code for future development
    * Add todo to code for future development
    * Restructure/move code for easier readability
    * Remove extra white spaces and convert tabs to space
    0.5.7
    * Update to Blender 2.6.3.
    * Fixed xz-y Skeleton rotation (again)
    * Added additional Keyframe at the end of each animation to prevent
      ogre from interpolating back to the start
    * Added option to ignore non-deformable bones
    * Added option to export nla-strips independently from each other

TODO
    * Remove this section and integrate below with code :)
    * Fix terrain collision offset bug
    * Add realtime transform (rotation is missing)
    * Fix camera rotated -90 ogre-dot-scene
    * Set description field for all pyRNA
'''

import os, sys, logging

# On startup blender may be able to read this file, but does not find
# any other file, since the curent directory is not in the module search
# path. Fix this by adding it.
#SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
#if SCRIPT_DIR not in sys.path:
#    sys.path.append( SCRIPT_DIR )

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
    bpy.utils.register_class(ui.OP_interface_toggle)
    bpy.utils.register_class(ui.HT_toggle_ogre)
    bpy.utils.register_class(ui.MT_mini_report)
    bpy.utils.register_class(ui.export.OP_ogre_export)
    ui.helper.register()
    # export drop down add ogre export function
    bpy.types.INFO_MT_file_export.append(ui.export.menu_func)

def unregister():
    logging.info('Unloading io_ogre %s', bl_info["version"])
    # remove the drop down
    bpy.types.INFO_MT_file_export.remove(ui.export.menu_func)
    # remove the interface toggle checkbox
    bpy.utils.unregister_class(ui.OP_interface_toggle)
    bpy.utils.unregister_class(ui.HT_toggle_ogre)
    bpy.utils.unregister_class(ui.MT_mini_report)
    bpy.utils.unregister_class(ui.export.OP_ogre_export)
    bpy.utils.unregister_class(ui.helper.MT_ogre_docs)
    ui.helper.unregister()

if __name__ == "__main__":
    register()

    try:
        index = sys.argv.index("--")
        from . import auto
        auto.export(sys.argv[index+1:])
    except ValueError:
        pass
