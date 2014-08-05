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
    * code refactored
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

import blender2ogre.version as v

bl_info = {
    "name": "OGRE Exporter (.scene, .mesh, .skeleton) and RealXtend (.txml)",
    "author": "Brett, S.Rombauts, F00bar, Waruck, Mind Calamity, Mr.Magne, Jonne Nauha, vax456",
    "version": v.version(),
    "blender": (2, 6, 6),
    "location": "File > Export...",
    "description": "Export to Ogre xml and binary formats",
    "wiki_url": "http://code.google.com/p/blender2ogre/w/list",
    "tracker_url": "http://code.google.com/p/blender2ogre/issues/list",
    "category": "Import-Export"
}

# import the plugin directory and setup the plugin
import blender2ogre
