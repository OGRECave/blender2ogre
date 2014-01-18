# blender2ogre #

* **License** [GNU LGPL](http://www.gnu.org/licenses/lgpl.html)
* **Authors** Brett, S.Rombauts, F00bar, Waruck, [Mind Calamity](https://bitbucket.org/MindCalamity), Mr.Magne, [Jonne Nauha](https://bitbucket.org/jonnenauha), vax456, Sybren Stüvel
* **Sponsors** Adminotech Ltd.
* [Forum thread](http://ogre3d.org/forums/viewtopic.php?f=8&t=61485) 

## Repository notes ##

This is a fork of the [original version](https://code.google.com/p/blender2ogre/) which is no longer actively maintained. This fork is to continue mainaining support for new Blender releases and to develop the code base further with bug fixes and new functionality. 

## Support and download ##

* Blender 2.66 and various older versions 
* Linux, Windows, OSX
* [Download official releases](https://code.google.com/p/blender2ogre/downloads)
* [Get latest sources](https://bitbucket.org/MindCalamity/blender2ogre)

## Updating to new versions ##

If you are upgrading from a previous version of blender2ogre, and having problems, you may want to delete your old .pickle config file from `~/.blender/2.6x/config/scripts/blender2ogre.pickle` and restart blender.

## Installing ##
    
### Using Windows .msi installer ###

**Note:** The Windows MSI installer is not available for all releases!

The addon script `io_export_ogreDotScene.py` has automatically been copied to the correct place by the installer. 
        
If the installer fails to detect a valid Blender installation for the automatic copying, it will show a dialog for the user and instructions how/where to copy it manually.
        
The uninstall step also tries to automatically clean the script file from Blender.
        
Mandatory dependencies are installed to the blender2ogre install directory. The script should automatically try to find them from there and set them correctly to the addon config.

### Using an .zip archive release (or raw io_export_ogreDotScene.py file) ###

If you are using a .zip arhive release. Extract it to disk, you will find `io_export_ogreDotScene.py` inside of it.

Use Blenders interface, under user-preferences, click addons, click `install-addon`, and select `io_export_ogreDotScene.py`. 

Or you can simply copy `io_export_ogreDotScene.py` to your blender installation under `blender/2.6x/scripts/addons/`

## Enabling the blender2ogre addon ##
* After installing the addon enable it in Blender from `User Preferences > Add-Ons > Import-Export`. Search for `ogre` and check the box on the right. Remember to save as default if you want the addon to be enabled after you exit your Blender.
* Integrated help docs will be shown in the upper right hand toolbar, replacing blender's normal `Help` menu, read them for assistance.

### 3rd party install tutorials ###

* Meshmoon: Video and text instructions how to install and use blender2ogre addon. 
 * [http://doc.meshmoon.com/index.html?page=from-blender-to-meshmoon-part-1](http://doc.meshmoon.com/index.html?page=from-blender-to-meshmoon-part-1)

## Installing Dependencies ##

This exporter writes Ogre mesh and skeleton files as XML `[.mesh.xml, .skeleton.xml]`. In order for the tool to create binary assets from them `[.mesh, .skeleton]`, you need the `OgreXMLConverter` command line tool that is provided by the Ogre project.
            
#### Windows ####
1. [Download the latest Ogre Command-line tools](http://www.ogre3d.org/download/tools)
2. Install to the default location.
3. See `Setting Tool Paths` section to configure the tool, if binary assets `[.mesh, .skeleton]` are not succesfully generated when exporting.

#### Linux ####

* Install the package `ogre-1.8-tools` or `ogre-tools` if your distro provides it. For example on Ubuntu `apt-get install ogre-1.8-tools`
* Or get [Ogre sources](https://bitbucket.org/sinbad/ogre), run CMake, `make && make install`. This should build `/usr/local/bin/OgreXMLConverter`

#### Mac OSX by Night Elf ####

1. [Download the latest pre-built SDK](http://www.ogre3d.org/download/tools) or build ogre from sources. If you build from sources the needed tools will be in `<Ogre Folder>/build/bin/Release`
2. Copy the OgreXMLConverter file to your `/usr/bin` folder. It's a hidden folder, so, to do that, open Terminal and enter the following commands: `cd /usr/bin` `open .` Finder will open on the `/usr/bin` folder.
3. Drag the `OgreMeshConverter` file over to that folder
4. Find `Ogre.framework`. If you build from sources it will be in `<Ogre Folder>/build/lib/Release`. The `Ogre.framework` shows as a "folder". Copy `Ogre.framework` to your `/Library/Frameworks` folder.
            
## Optional dependencies ##

See `Setting Tool Paths` section on how to configure the optional tools if default paths fail to find them.
        
1. Image Magick
 * Install [Image Magick](http://www.imagemagick.org) to the default location.
2. OgreMeshy
 * **Windows** Get the [latest Ogre Meshy](http://sourceforge.net/projects/ogremeshy/) and install to the default location. See the "Setting Tool Paths" section. Prefer using the 64-bit OgreMeshy for 64-bit Windows.                
 * **Linux / Mac OSX** Get Ogre Meshy for Windows, install wine, extract OgreMeshy to `/home/yourname/OgreMeshy`
3. NVIDIA Texture Tools 2.0 with CUDA acceleration
 * http://code.google.com/p/nvidia-texture-tools/
 * Note: Nvidia DDS, if you can not install "NVIDIA Texture Tools 2.0" above, you can still use [Legacy Utils](http://developer.nvidia.com/object/dds_utilities_legacy.html)

4. realXtend Tundra
 * Tundra is a 3D virtual world platform that uses Ogre3D for rendering. This plugin can export the Tundra scene format `.txml` directly along with the Ogre binary assets. Those scenes can be easily loaded and viewer by Tundra. Tundra also supports drag and drop imports for the Ogre scene file `.scene`.          
 * **Windows and Mac OSX** [Download and install the latest Tundra](https://code.google.com/p/realxtend-naali/downloads/list)
 * **Linux** For Linux there are no binary installers, build from sources with [these instructions](https://github.com/realXtend/tundra#compiling-from-sources).

## Setting Tool Paths ##

If for some reason you can not install the dependencies above to the recommended paths, you can change the paths in Blender by going to `Properties > Scene > Ogre Configuration File`, edit the paths and then click `update config file` to store the new config. You may need to restart Blender for the changes to take effect.
