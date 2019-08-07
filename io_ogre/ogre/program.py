import os
from .. import config

class OgreProgram(object):
    '''
    parses .program scripts
    saves bytes to copy later

    self.name = name of program reference
    self.source = name of shader program (.cg, .glsl)
    '''

    def save( self, path ):
        print('saving program to', path)
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
            print( 'ERROR: ogre material %s is missing source: %s' %(self.name,self.source) )
            print( config.get('SHADER_PROGRAMS') )
            return False
        url = os.path.join(  config.get('SHADER_PROGRAMS'), self.source )
        print('shader source:', url)
        self.source_bytes = open( url, 'rb' ).read()#.decode('utf-8')
        print('shader source num bytes:', len(self.source_bytes))
        data = self.source_bytes.decode('utf-8')

        for line in data.splitlines():  # only cg shaders use the include macro?
            if line.startswith('#include') and line.count('"')==2:
                name = line.split()[-1].replace('"','').strip()
                print('shader includes:', name)
                url = os.path.join(  config.get('SHADER_PROGRAMS'), name )
                self.includes[ name ] = open( url, 'rb' ).read()
        return True

    def __init__(self, name='', data=''):
        self.name=name
        self.data = data.strip()
        self.source = None
        self.includes = {} # cg files may use #include something.cg

        if self.name in OgreProgram.PROGRAMS:
            print('---copy ogreprogram---', self.name)
            other = OgreProgram.PROGRAMS
            self.source = other.source
            self.data = other.data
            self.entry_point = other.entry_point
            self.profiles = other.profiles

        if data: self.parse( self.data )
        if self.name: OgreProgram.PROGRAMS[ self.name ] = self

    def parse( self, txt ):
        self.data = txt
        print('--parsing ogre shader program--' )
        for line in self.data.splitlines():
            line = line.split('//')[0]
            line = line.strip()
            if line.startswith('vertex_program') or line.startswith('fragment_program'):
                a, self.name, self.type = line.split()

            elif line.startswith('source'): self.source = line.split()[-1]
            elif line.startswith('entry_point'): self.entry_point = line.split()[-1]
            elif line.startswith('profiles'): self.profiles = line.split()[1:]

