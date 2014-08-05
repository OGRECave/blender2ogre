
import os
import subprocess
import logging
from ..config import CONFIG

def OgreXMLConverter( infile, has_uvs=False ):
    # todo: Show a UI dialog to show this error. It's pretty fatal for normal usage.
    # We should show how to configure the converter location in config panel or tell the default path.
    exe = CONFIG['OGRETOOLS_XML_CONVERTER']
    if not os.path.isfile( exe ):
        logging.warn('Can\'t find OgreXMLConverter (can not convert XXX.mesh.xml to XXX.mesh' )
        return

    basicArguments = ''

    # LOD generation with OgreXMLConverter tool does not work. Currently the mesh files are generated
    # manually and referenced in the main mesh file.
    #if CONFIG['lodLevels']:
    #    basicArguments += ' -l %s -v %s -p %s' %(CONFIG['lodLevels'], CONFIG['lodDistance'], CONFIG['lodPercent'])

    if CONFIG['nuextremityPoints'] > 0:
        basicArguments += ' -x %s' %CONFIG['nuextremityPoints']

    if not CONFIG['generateEdgeLists']:
        basicArguments += ' -e'

    # note: OgreXmlConverter fails to convert meshes without UVs
    if CONFIG['generateTangents'] and has_uvs:
        basicArguments += ' -t'
        if CONFIG['tangentSemantic']:
            basicArguments += ' -td %s' %CONFIG['tangentSemantic']
        if CONFIG['tangentUseParity']:
            basicArguments += ' -ts %s' %CONFIG['tangentUseParity']
        if CONFIG['tangentSplitMirrored']:
            basicArguments += ' -tm'
        if CONFIG['tangentSplitRotated']:
            basicArguments += ' -tr'
    if not CONFIG['reorganiseBuffers']:
        basicArguments += ' -r'
    if not CONFIG['optimiseAnimations']:
        basicArguments += ' -o'

    # Make xml converter print less stuff, comment this if you want more debug info out
    basicArguments += ' -q'

    opts = '-log _ogre_debug.txt %s' %basicArguments
    path,name = os.path.split( infile )

    cmd = '%s %s' % (exe, opts)
    cmd = cmd.split() + [infile]
    subprocess.call( cmd )
