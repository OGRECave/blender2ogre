Blender2Ogre
By: Hartshorn, S.Rombauts, PForce and F00bar
Sponsors: Adminotech Ltd
License: GNU LGPL
Version: 0.5.6 2011

Supports:
	Blender 2.6
	Linux, Windows, OSX

Upgrading?
	. if you are upgrading from a previous version of blender2ogre, and having problems, you may want to delete your old .pickle file:
		example linux: rm ~/.blender/2.59/config/scripts/blender2ogre.pickle

Getting Started:
	. After installing the addon (see below), enable it from "User Preferences->Add-Ons->Import-Export"
	. Integrated help docs will be shown in the upper right hand toolbar, replacing blender's normal 'Help' menu, read them!

Setting Your Paths:
    If for some reason you can not install the dependencies below to the recommended paths, you can change the paths in
blender by going to "Properties>Scene>Ogre Configuration File", and then click "update config file"

Installing:
	Installing the Addon:
		. Use blenders interface, under user-prefs, click addons, click 'install-addon', and select: io_export_ogreDotScene.py
		. or you can simply copy io_export_ogreDotScene.py to your blender installation under blender/2.59/scripts/addons/

	Installing Dependencies:
		Linux:
			1. Get the Ogre source code, compile and "make install" that should give you: /usr/local/bin/OgreXMLConverter
				( "apt-get install ogre-tools" also works )
			2. Get Ogre Meshy for Windows, install wine, extract OgreMeshy to /home/yourname/OgreMeshy

		Windows:
			NOTE: OgreCommandLineTools 1.6.3 is old. Upgrade to 1.7 if possible
				1. extract the zip "blender2ogre-minimal-deps(win32,wine).zip"
				2. install OgreCommandLineTools_1.6.3.msi and msvcpp_2008_sp1_redist_vcredist_x86.exe
				3. copy OgreMeshy to C:\

		Get the latest Ogre Meshy from: http://sourceforge.net/projects/ogremeshy/

Dependencies:
	Required:
		1. blender2.6
		2. Install Ogre Command Line tools to the default path ( C:\\OgreCommandLineTools )
			http://www.ogre3d.org/download/tools

	Optional:
		3. NVIDIA Texture Tools 2.0 (with CUDA acceleration)
			http://code.google.com/p/nvidia-texture-tools/

		4. Install Image Magick
			http://www.imagemagick.org

		5. Copy OgreMeshy to C:\OgreMeshy
			If your using 64bit Windows, you will need to download a 64bit OgreMeshy
			(Linux copy to your home folder)

		6. RealXtend Tundra2
			http://blender2ogre.googlecode.com/files/realxtend-Tundra-2.1.2-OpenGL.7z
			Windows: extract to C:\Tundra2
			Linux: extract to Tundra2 in your home directory (~/Tundra2)

Note: Nvidia DDS, if you can not install "NVIDIA Texture Tools 2.0" above, you can still use
Legacy Utils below:
	http://developer.nvidia.com/object/dds_utilities_legacy.html


################################### OSX ########################################
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
    Get the Ogre.framework by building Ogre from source or from the pre-built SDK. I built form soruce and it's in <Ogre Folder>/build/lib/Release. It shows like a folder.
    Copy Ogre.framework to your /Library/Frameworks folder.



	
