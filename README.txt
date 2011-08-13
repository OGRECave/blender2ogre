Blender2Ogre
By: Hartshorn, S.Rombauts, PForce and F00bar
Sponsors: Adminotech Ltd
License: GNU LGPL
Version: 0.4.8 - July 27th 2011
Supports:
	Blender 2.58.1
	Linux, Windows, OSX

Upgrading?
	. if you are upgrading from a previous version of blender2ogre, and having problems, you may want to delete your old .cfg file:
		example linux: rm ~/.blender/2.58/config/scripts/blender2ogre.cfg

Getting Started:
	. After installing the addon (see below), enable it from "User Preferences->Add-Ons->Import-Export"
	. Integrated help docs will be shown in the upper right hand toolbar, replacing blender's normal 'Help' menu, read them!

Installing:
	Installing the Addon:
		. You can simply copy io_export_ogreDotScene.py to your blender installation under blender/2.58/scripts/addons_contrib/
		. Or you can use blenders interface, under user-prefs, click addons, click 'install-addon', and select: io_export_ogreDotScene.py

	Installing Dependencies:
		Linux:
			1. Get the Ogre source code, compile and "make install" that should give you: /usr/local/bin/OgreXMLConverter
			2. Get Ogre Meshy for Windows, install wine, extract OgreMeshy to /home/yourname/OgreMeshy

		Windows:
			1. extract the zip "blender2ogre-minimal-deps(win32,wine).zip"
			2. install OgreCommandLineTools_1.6.3.msi and msvcpp_2008_sp1_redist_vcredist_x86.exe
			3. copy OgreMeshy to C:\

		Get the latest Ogre Meshy from: http://sourceforge.net/projects/ogremeshy/


Installing OSX - by Night Elf:
    Compile OgreXMLConverter from source, and "make install"
    "So, apparently OgreXMLConverter wasn't working because it couldn't find Ogre.framework. 
    I got it working now. So, in case someone's having a similar problem, here's how to get this exporter working on OSX":

Add-on installation:
    Download the latest script
    In Blender: File > User Preferences... > Add-Ons > Install Add-On... and look for the io_export_ogreDotScene.py file
    Enable the add-on
    Ogre Command-Line Tools:
    Get the OgreMeshConverter tool by building Ogre from source or from the pre-built SDK. I built from source and it's in <Ogre Folder>/build/bin/Release.
    Copy the OgreMeshConverter file to your /usr/bin folder. It's a hidden folder, so, to do that, open Terminal and enter the following commands:
    CODE:
        cd /usr/bin
        open .
    Finder will open on the /usr/bin folder (There may be an easier way, I'm quite new to Mac OS...)
    Drag the OgreMeshConverter file over to that folder
    Ogre framework:
    Get the Ogre.framework by building Ogre form source or form the pre-built SDK. I built form soruce and it's in <Ogre Folder>/build/lib/Release. It shows like a folder.
    Copy Ogre.framework to your /Library/Frameworks folder.



Dependencies:
	Required:
		1. blender2.58
		2. Install Ogre Command Line tools to the default path ( C:\\OgreCommandLineTools )
			http://www.ogre3d.org/download/tools

	Optional:
		3. Install NVIDIA DDS Legacy Utilities	( install to default path )
			http://developer.nvidia.com/object/dds_utilities_legacy.html
			(Linux users will need to use Wine)

		4. Install Image Magick
			http://www.imagemagick.org

		5. Copy folder 'myshaders' to C:\\myshaders
			(Linux copy to your home folder)

		6. Copy OgreMeshy to C:\\OgreMeshy
			If your using 64bit Windows, you will need to download a 64bit OgreMeshy
			(Linux copy to your home folder)

Changelog:
    0.4.4 small fixes, lamp export fixed, vertex count correct
    0.4.3 small fixes, default axis now x z -y, fixed floating bones
    0.4.0 fixed uv textures
    0.3.8 fixed merge groups, OSX support
    0.3.7 big speed up for mesh export, and fixed shape animation - june 3rd
    0.3.6 more small fixes - may 16th
	0.3.4 small fixes - may11th
	0.3.2 added a config file - first Blender 2.57 release
    . issue7: Need for an add-on config file with user preferences
    . issue10: No more tabulation, using the standard 4 spaces recommanded by the Python PEP-8
    . Issue 14:	DEFAULT_IMAGE_MAGICK_CONVERT uninitialized under Windows

	0.3.1 small bug fix and optimization (Sébastien Rombauts)
		. issue1: os.getlogin() unreliable; using getpass.getuser() instead
		. issue5: speed optimization O(n^2) into O(n log n)
		
	0.3.0 milestone (Brett Hartshorn)
	
