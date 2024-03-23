import os, logging
from .. import config

logger = logging.getLogger('program')

class OgreProgram(object):
    '''
    parses .program scripts
    saves bytes to copy later

    self.name = name of program reference
    self.source = name of shader program (.cg, .glsl)
    '''

    def save( self, path ):
        logger.info('Saving program to: %s' % path)
        f = open( os.path.join(path,self.source), 'wb' )
        f.write(self.source_bytes )
        f.close()
        for name in self.includes:
            f = open( os.path.join(path,name), 'wb' )
            f.write( self.includes[name] )
            f.close()

    PROGRAMS = {}

    def reload(self): # only one directory is allowed to hold shader programs
        if self.source not in os.listdir( config.get('SHADER_PROGRAMS') ):
            logger.error( 'Ogre material %s is missing source: %s' % (self.name,self.source) )
            logger.error( config.get('SHADER_PROGRAMS') )
            return False
        url = os.path.join(  config.get('SHADER_PROGRAMS'), self.source )
        logger.info('Shader source: %s' % url)
        self.source_bytes = open( url, 'rb' ).read()#.decode('utf-8')
        logger.info('Shader source num bytes: %s' % len(self.source_bytes))
        data = self.source_bytes.decode('utf-8')

        for line in data.splitlines():  # only cg shaders use the include macro?
            if line.startswith('#include') and line.count('"')==2:
                name = line.split()[-1].replace('"','').strip()
                logger.info('Shader includes: %s' % name)
                url = os.path.join(  config.get('SHADER_PROGRAMS'), name )
                self.includes[ name ] = open( url, 'rb' ).read()
        return True

    def __init__(self, name='', data=''):
        self.name=name
        self.data = data.strip()
        self.source = None
        self.includes = {} # cg files may use #include something.cg

        if self.name in OgreProgram.PROGRAMS:
            logger.info('<%s> --- Copy Ogre Program --- ' % self.name)
            other = OgreProgram.PROGRAMS
            self.source = other.source
            self.data = other.data
            self.entry_point = other.entry_point
            self.profiles = other.profiles

        if data: self.parse( self.data )
        if self.name: OgreProgram.PROGRAMS[ self.name ] = self

    def parse( self, txt ):
        self.data = txt
        logger.info('<%s> -- Parsing Ogre Shader Program-- ' % self.name )
        for line in self.data.splitlines():
            line = line.split('//')[0]
            line = line.strip()
            if line.startswith('vertex_program') or line.startswith('fragment_program'):
                a, self.name, self.type = line.split()

            elif line.startswith('source'): self.source = line.split()[-1]
            elif line.startswith('entry_point'): self.entry_point = line.split()[-1]
            elif line.startswith('profiles'): self.profiles = line.split()[1:]
