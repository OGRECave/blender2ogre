***************************************************************************
Name            blender2ogre 
Version         0.6.0
License         GNU LGPL
Authors         Brett, S.Rombauts, F00bar, Waruck, Mind Calamity, 
                Mr.Magne, Jonne Nauha, vax456, Sybren Stüvel
Sponsors        Adminotech Ltd.
Forums Thread   http://ogre3d.org/forums/viewtopic.php?f=8&t=61485
***************************************************************************

Repository notes:
	This is a fork of the original version, which seems to be no longer
	maintained. There are going to be some updates and some new features
	coming to this version.

Supports
    - Blender 2.66
    - Linux, Windows, OSX

Note for upgrading
    If you are upgrading from a previous version of blender2ogre, 
    and having problems, you may want to delete your old .pickle config 
    file from ~/.blender/2.6x/config/scripts/blender2ogre.pickle and
    restart blender

Installing
    
    Using Windows .msi installer
        The addon script io_export_ogreDotScene.py has automatically been 
        copied to the correct place by the installer. 
        
        If the installer fails to detect a valid Blender installation 
        for the automatic copying, it will show a dialog for the user 
        and instructions how/where to copy it manually.
        
        The uninstall step also tries to automatically clean the script 
        file from Blender.
        
        Mandatory dependencies are installed to the blender2ogre install 
        directory. The script should automatically try to find them from 
        there and set them correctly to the addon config.

    Using an archive or plain io_export_ogreDotScene.py file
        Use Blenders interface, under user-preferences, click addons, 
        click "install-addon", and select io_export_ogreDotScene.py
        Or you can simply copy io_export_ogreDotScene.py to your 
        blender installation under blender/2.6x/scripts/addons/

        Installing Dependencies
            In order to create binary Ogre meshes, you need OgreXMLConverter.
            Try to use the latest Ogre tools, at the moment that would be 1.7
            
            Windows
                1. Download the latest Ogre Command-line tools from
                   http://www.ogre3d.org/download/tools
                2. Install to the default location.
                3. See "Setting Tool Paths" section if .mesh files
                   are not exported to configure the tools.

            Linux
                Get the Ogre source code, compile and "make install" that
                should give you /usr/local/bin/OgreXMLConverter
                or use "apt-get install ogre-tools" if your distro has it.

            Mac OSX by Night Elf
                1. Download the latest pre-built SDK from
                   http://www.ogre3d.org/download/tools or
                   build ogre from sources. If you build from sources
                   the needed tools will be in <Ogre Folder>/build/bin/Release
                2. Copy the OgreXMLConverter file to your /usr/bin folder. 
                   It's a hidden folder, so, to do that, open Terminal and 
                   enter the following commands:
                     cd /usr/bin
                     open .
                   Finder will open on the /usr/bin folder
                3. Drag the OgreMeshConverter file over to that folder
                4. Find Ogre.framework. If you build from soruces it will
                   be in <Ogre Folder>/build/lib/Release. The Ogre.framework 
                   shows as a "folder". Copy Ogre.framework to your 
                   /Library/Frameworks folder.
            
    Optional dependencies
        See "Setting Tool Paths" section on how to configure
        the optional tools if default paths fail to find them.
        
        1. Install Image Magick from http://www.imagemagick.org
           to the default location.

        2. OgreMeshy
            Windows
                Get the latest Ogre Meshy from 
                http://sourceforge.net/projects/ogremeshy/ and install to 
                the default location. See the "Setting Tool Paths" section.
                If your using 64bit Windows, you will need to download the 
                64bit OgreMeshy.
                
            Linux / Mac OSX
                Get Ogre Meshy for Windows, install wine, extract 
                OgreMeshy to /home/yourname/OgreMeshy

        3. NVIDIA Texture Tools 2.0 with CUDA acceleration
           http://code.google.com/p/nvidia-texture-tools/
           
           Note: Nvidia DDS, if you can not install "NVIDIA 
           Texture Tools 2.0" above, you can still use Legacy 
           Utils below: http://developer.nvidia.com/object/
           dds_utilities_legacy.html

        4. realXtend Tundra
            
            Windows and Mac OSX
                Download and install the latest Tundra from
                http://code.google.com/p/realxtend-naali/downloads/list
            
            Linux
                1. Download http://blender2ogre.googlecode.com/files/
                   realxtend-Tundra-2.1.2-OpenGL.7z
                2. Extract to your home directory ~/Tundra2
                
                Or build from sources https://github.com/realXtend/naali

Enabling blender2ogre
    - After installing the addon enable it in Blender from 
      User Preferences -> Add-Ons -> Import-Export. Search for
      'ogre' and check the box on the right. Remember to save as default
      if you want the plugin to be enabled after you exit your Blender.
    - Integrated help docs will be shown in the upper right hand toolbar, 
      replacing blender's normal 'Help' menu, read them for assistance.

Setting Tool Paths
    If for some reason you can not install the dependencies below to the 
    recommended paths, you can change the paths in Blender by going to 
    Properties -> Scene -> Ogre Configuration File and then click 
    "update config file" to store the new config. You may need to restart
    Blender for the changes to take effect.
