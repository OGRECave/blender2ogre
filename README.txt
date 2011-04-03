Blender2Ogre
By: Brett Hartshorn
License: GNU LGPL

Platforms:
	Linux -  Ubuntu Lucid and wine1.2
	Windows
	OSX ??

Help:
	Integrated help docs will be shown in the upper right hand toolbar, replacing blender's normal 'Help' menu.
	( recommend that you read all of the help articles list there )

Installing:
	Installing the Addon:
		1. You can simply copy io_export_ogreDotScene.py to your blender installation under blender/2.56/scripts/addons/
			( manual copy is the safest way )
		2. Or you can use blenders interface, under user-prefs, click addons, and click 'install-addon'
			( this way fails to overwrite a previous version )

	Installing Dependencies:

		Get the Dependencies from google code "blender2ogre-minimal-deps(win32,wine).zip"
		Linux: run "install-linux.sh"
		Windows:
			1. extract the zip "blender2ogre-minimal-deps(win32,wine).zip"
			2. install OgreCommandLineTools_1.6.3.msi and msvcpp_2008_sp1_redist_vcredist_x86.exe
			3. copy OgreMeshy to C:\

Dependencies:
	Required:
		1. blender2.56		(svn 33087+)

		2. Install Ogre Command Line tools to the default path ( C:\\OgreCommandLineTools )
			http://www.ogre3d.org/download/tools
			(Linux users will need to use Wine)

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

	0.3.2 added a config file - first Blender 2.57 release
    . issue7: Need for an add-on config file with user preferences
    . issue10: No more tabulation, using the standard 4 spaces recommanded by the Python PEP-8
    . Issue 14:	DEFAULT_IMAGE_MAGICK_CONVERT uninitialized under Windows

	0.3.1 small bug fix and optimization (Sébastien Rombauts)
		. issue1: os.getlogin() unreliable; using getpass.getuser() instead
		. issue5: speed optimization O(n^2) into O(n log n)
		
	0.3.0 milestone (Brett Hartshorn)
	