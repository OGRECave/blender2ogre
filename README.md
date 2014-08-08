# blender2ogre #

* License: [GNU LGPL](http://www.gnu.org/licenses/lgpl.html)
* [Source code repository](https://bitbucket.org/MindCalamity/blender2ogre)
* [Issue tracker](https://bitbucket.org/MindCalamity/blender2ogre/issues)
* [Ogre forum thread](http://ogre3d.org/forums/viewtopic.php?f=8&t=61485)
   
## Authors ##

This Blender addon was made possible by the following list of people. Anyone can contribute to the project by sending bug reports and feature requests [here](https://bitbucket.org/MindCalamity/blender2ogre/issues). Naturally the most welcome contribution is actual code via [pull requests](https://bitbucket.org/MindCalamity/blender2ogre/pull-requests). If you are planning to implement something "big", it's a good practise to discuss it in the issue tracker first with other authors. So that there is no overlap with other developers or the overall roadmap.
 
* [Brett](http://pyppet.blogspot.fi/)
* S. Rombauts
* F00bar
* Waruck
* [Mind Calamity](https://bitbucket.org/MindCalamity)
* Mr.Magne
* [Jonne Nauha](https://bitbucket.org/jonnenauha) aka Pforce
* vax456
* Sybren Stüvel

Additionally the following companies have supportted/sponsored the development efforts.

* [Adminotech Ltd.](http://www.meshmoon.com/)

## Repository notes ##

This is a fork of the [original version](https://code.google.com/p/blender2ogre/) which is no longer actively maintained. This fork is to continue mainaining support for new Blender releases and to develop the code base further with bug fixes and new functionality.

----------

## Download (Linux, Windows, OS X) ##

* [Download official releases](https://bitbucket.org/MindCalamity/blender2ogre/downloads)
* [Get latest sources](https://bitbucket.org/MindCalamity/blender2ogre/sources)
* Blender 2.71
* Blender 2.66
* Might also work with older versions of Blender

## Updating to new versions ##

If you are upgrading from a previous version of blender2ogre, and having problems, you may want to delete your old .pickle config file from `~/.blender/2.6x/config/scripts/blender2ogre.pickle` and restart blender.

----------

## Installing ##

Please refer to the download section and download the desired plugin version. This zip file
should be extracted into the blender scripts/addons folder.
You can find instructions on how to find this folder [here](http://wiki.blender.org/index.php/Doc:2.6/Manual/Extensions/Python/Add-Ons#Installation_of_an_Add-On).
After installing the addon enable it in Blender from `User Preferences > Add-Ons > Import-Export`. Search for `ogre` and check the box on the right. Remember to save as default if you want the addon to be enabled after you exit your Blender.
Integrated help docs will be shown in the upper right hand toolbar, replacing blender's normal `Help` menu, read them for assistance.

## Pre 0.6.1 ##

### 3rd party tutorials ###

* Meshmoon: Video and text instructions how to install and use blender2ogre addon. See [http://doc.meshmoon.com/index.html?page=from-blender-to-meshmoon-part-1](http://doc.meshmoon.com/index.html?page=from-blender-to-meshmoon-part-1)

----------

## Installing dependencies ##

This exporter writes Ogre mesh and skeleton files as XML `[.mesh.xml, .skeleton.xml]`. In order for the tool to create binary assets from them `[.mesh, .skeleton]`, you need the `OgreXMLConverter` command line tool that is provided by the Ogre project.
            
#### Windows ####

1. [Download the latest Ogre Command-line tools](http://www.ogre3d.org/download/tools)
2. Install to the default location.
3. See `Setting tool paths` section to configure the tool, if binary assets `[.mesh, .skeleton]` are not succesfully generated when exporting.

#### Linux ####

* Install the package `ogre-1.8-tools` or `ogre-tools` if your distro provides it. For example on Ubuntu `apt-get install ogre-1.8-tools`
* Or get [Ogre sources](https://bitbucket.org/sinbad/ogre), run CMake, `make && make install`. This should build `/usr/local/bin/OgreXMLConverter`

#### Mac OSX ####

1. [Download the latest pre-built SDK](http://www.ogre3d.org/download/tools) or build ogre from sources. If you build from sources the needed tools will be in `<Ogre Folder>/build/bin/Release`
2. Copy the OgreXMLConverter file to your `/usr/bin` folder. It's a hidden folder, so, to do that, open Terminal and enter the following commands `cd /usr/bin` and `open .` Finder will open on the `/usr/bin` folder.
3. Drag the `OgreMeshConverter` file over to that folder
4. Find `Ogre.framework`. If you build from sources it will be in `<Ogre Folder>/build/lib/Release`. The `Ogre.framework` shows as a "folder". Copy `Ogre.framework` to your `/Library/Frameworks` folder.

## Optional dependencies ##

See `Setting tool paths` section on how to configure the optional tools if default paths fail to find them.
        
#### Image Magick ####

* Install [Image Magick](http://www.imagemagick.org) to the default location.

#### OgreMeshy ####

* **Windows** Get the [latest Ogre Meshy](http://sourceforge.net/projects/ogremeshy/) and install to the default location. See the "Setting tool paths" section. Prefer using the 64-bit OgreMeshy for 64-bit Windows.                
* **Linux / Mac OSX** Get Ogre Meshy for Windows, install wine, extract OgreMeshy to `/home/yourname/OgreMeshy`

#### NVIDIA Texture Tools 2.0 with CUDA acceleration ####

* [http://code.google.com/p/nvidia-texture-tools/](http://code.google.com/p/nvidia-texture-tools/)
* **Note:** NVIDIA DDS, if you can not install "NVIDIA Texture Tools 2.0" above, you can still use [Legacy Utils](http://developer.nvidia.com/object/dds_utilities_legacy.html)

#### realXtend Tundra ####

Tundra is a 3D virtual world platform that uses Ogre3D for rendering. This plugin can export the Tundra scene format `.txml` directly along with the Ogre binary assets. Those scenes can be easily loaded and viewer by Tundra. Tundra also supports drag and drop imports for the Ogre scene file `.scene`.          

* **Windows and Mac OSX** [Download and install the latest Tundra](https://code.google.com/p/realxtend-naali/downloads/list)
* **Linux** For Linux there are no binary installers, build from sources with [these instructions](https://github.com/realXtend/tundra#compiling-from-sources).

## Setting tool paths ##

You can change the required and optional tool paths in Blender when you see the need for it. This usually needs to be done if you failed to install the tools to the default paths, or they cannot be found from the default paths.

* In Blender go to `Properties > Scene > Ogre Configuration File`
* Edit the required tool paths 
* Click `update config file` to store the new config. You may need to restart Blender for the changes to take effect.
