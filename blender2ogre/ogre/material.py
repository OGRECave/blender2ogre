## Ogre Material object(s) that is utilized during export stages

from .. import version as v

def material_name( mat, clean = False ):
    if type(mat) is str:
        return mat
    elif not mat.library:
        return mat.name
    else:
        if clean:
            return clean_object_name(mat.name + mat.library.filepath.replace('/','_'))

def generate_material(mat, path='/tmp', copy_programs=False, touch_textures=False):
    ''' returns generated material string '''

    safename = material_name(mat) # supports blender library linking
    M = '// %s generated by blender2ogre %s\n\n' % (mat.name, v.version_str())

    M += 'material %s \n{\n' % safename # start material
    if mat.use_shadows:
        M += indent(1, 'receive_shadows on \n')
    else:
        M += indent(1, 'receive_shadows off \n')

    M += indent(1, 'technique', '{' ) # technique GLSL, CG
    w = OgreMaterialGenerator(mat, path=path, touch_textures=touch_textures)

    if copy_programs:
        progs = w.get_active_programs()
        for prog in progs:
            if prog.source:
                prog.save(path)
            else:
                print( '[WARNING}: material %s uses program %s which has no source' % (mat.name, prog.name) )

    header = w.get_header()
    passes = w.get_passes()

    M += '\n'.join(passes)
    M += indent(1, '}' )      # end technique
    M += '}\n'                # end material

    if len(header) > 0:
        return header + '\n' + M
    else:
        return M

def get_shader_program( name ):
    if name in OgreProgram.PROGRAMS:
        return OgreProgram.PROGRAMS[ name ]
    else:
        print('WARNING: no shader program named: %s' %name)

def get_shader_programs():
    return OgreProgram.PROGRAMS.values()

def parse_material_and_program_scripts( path, scripts, progs, missing ):   # recursive
    for name in os.listdir(path):
        url = os.path.join(path,name)
        if os.path.isdir( url ):
            parse_material_and_program_scripts( url, scripts, progs, missing )

        elif os.path.isfile( url ):
            if name.endswith( '.material' ):
                print( '<found material>', url )
                scripts.append( MaterialScripts( url ) )

            if name.endswith('.program'):
                print( '<found program>', url )
                data = open( url, 'rb' ).read().decode('utf-8')

                chk = []; chunks = [ chk ]
                for line in data.splitlines():
                    line = line.split('//')[0]
                    if line.startswith('}'):
                        chk.append( line )
                        chk = []; chunks.append( chk )
                    elif line.strip():
                        chk.append( line )

                for chk in chunks:
                    if not chk: continue
                    p = OgreProgram( data='\n'.join(chk) )
                    if p.source:
                        ok = p.reload()
                        if not ok: missing.append( p )
                        else: progs.append( p )

def get_ogre_user_material( name ):
    if name in MaterialScripts.ALL_MATERIALS:
        return MaterialScripts.ALL_MATERIALS[ name ]

class OgreMaterialScript(object):
    def get_programs(self):
        progs = []
        for name in list(self.vertex_programs.keys()) + list(self.fragment_programs.keys()):
            p = get_shader_program( name )  # OgreProgram.PROGRAMS
            if p: progs.append( p )
        return progs

    def __init__(self, txt, url):
        self.url = url
        self.data = txt.strip()
        self.parent = None
        self.vertex_programs = {}
        self.fragment_programs = {}
        self.texture_units = {}
        self.texture_units_order = []
        self.passes = []

        line = self.data.splitlines()[0]
        assert line.startswith('material')
        if ':' in line:
            line, self.parent = line.split(':')
        self.name = line.split()[-1]
        print( 'new ogre material: %s' %self.name )

        brace = 0
        self.techniques = techs = []
        prog = None  # pick up program params
        tex = None  # pick up texture_unit options, require "texture" ?
        for line in self.data.splitlines():
            #print( line )
            rawline = line
            line = line.split('//')[0]
            line = line.strip()
            if not line: continue

            if line == '{': brace += 1
            elif line == '}': brace -= 1; prog = None; tex = None

            if line.startswith( 'technique' ):
                tech = {'passes':[]}; techs.append( tech )
                if len(line.split()) > 1: tech['technique-name'] = line.split()[-1]
            elif techs:
                if line.startswith('pass'):
                    P = {'texture_units':[], 'vprogram':None, 'fprogram':None, 'body':[]}
                    tech['passes'].append( P )
                    self.passes.append( P )

                elif tech['passes']:
                    P = tech['passes'][-1]
                    P['body'].append( rawline )

                    if line == '{' or line == '}': continue

                    if line.startswith('vertex_program_ref'):
                        prog = P['vprogram'] = {'name':line.split()[-1], 'params':{}}
                        self.vertex_programs[ prog['name'] ] = prog
                    elif line.startswith('fragment_program_ref'):
                        prog = P['fprogram'] = {'name':line.split()[-1], 'params':{}}
                        self.fragment_programs[ prog['name'] ] = prog

                    elif line.startswith('texture_unit'):
                        prog = None
                        tex = {'name':line.split()[-1], 'params':{}}
                        if tex['name'] == 'texture_unit': # ignore unnamed texture units
                            print('WARNING: material %s contains unnamed texture_units' %self.name)
                            print('---unnamed texture units will be ignored---')
                        else:
                            P['texture_units'].append( tex )
                            self.texture_units[ tex['name'] ] = tex
                            self.texture_units_order.append( tex['name'] )

                    elif prog:
                        p = line.split()[0]
                        if p=='param_named':
                            items = line.split()
                            if len(items) == 4: p, o, t, v = items
                            elif len(items) == 3:
                                p, o, v = items
                                t = 'class'
                            elif len(items) > 4:
                                o = items[1]; t = items[2]
                                v = items[3:]

                            opt = { 'name': o, 'type':t, 'raw_value':v }
                            prog['params'][ o ] = opt
                            if t=='float': opt['value'] = float(v)
                            elif t in 'float2 float3 float4'.split(): opt['value'] = [ float(a) for a in v ]
                            else: print('unknown type:', t)

                    elif tex:   # (not used)
                        tex['params'][ line.split()[0] ] = line.split()[ 1 : ]

        for P in self.passes:
            lines = P['body']
            while lines and ''.join(lines).count('{')!=''.join(lines).count('}'):
                if lines[-1].strip() == '}': lines.pop()
                else: break
            P['body'] = '\n'.join( lines )
            assert P['body'].count('{') == P['body'].count('}')     # if this fails, the parser choked

        #print( self.techniques )
        self.hidden_texture_units = rem = []
        for tex in self.texture_units.values():
            if 'texture' not in tex['params']:
                rem.append( tex )
        for tex in rem:
            print('WARNING: not using texture_unit because it lacks a "texture" parameter', tex['name'])
            self.texture_units.pop( tex['name'] )

        if len(self.techniques)>1:
            print('WARNING: user material %s has more than one technique' %self.url)

    def as_abstract_passes( self ):
        r = []
        for i,P in enumerate(self.passes):
            head = 'abstract pass %s/PASS%s' %(self.name,i)
            r.append( head + '\n' + P['body'] )
        return r

class MaterialScripts(object):
    ALL_MATERIALS = {}
    ENUM_ITEMS = []

    def __init__(self, url):
        self.url = url
        self.data = ''
        data = open( url, 'rb' ).read()
        try:
            self.data = data.decode('utf-8')
        except:
            self.data = data.decode('latin-1')

        self.materials = {}
        ## chop up .material file, find all material defs ####
        mats = []
        mat = []
        skip = False    # for now - programs must be defined in .program files, not in the .material
        for line in self.data.splitlines():
            if not line.strip(): continue
            a = line.split()[0]             #NOTE ".split()" strips white space
            if a == 'material':
                mat = []; mats.append( mat )
                mat.append( line )
            elif a in ('vertex_program', 'fragment_program', 'abstract'):
                skip = True
            elif mat and not skip:
                mat.append( line )
            elif skip and line=='}':
                skip = False

        ##########################
        for mat in mats:
            omat = OgreMaterialScript( '\n'.join( mat ), url )
            if omat.name in self.ALL_MATERIALS:
                print( 'WARNING: material %s redefined' %omat.name )
                #print( '--OLD MATERIAL--')
                #print( self.ALL_MATERIALS[ omat.name ].data )
                #print( '--NEW MATERIAL--')
                #print( omat.data )
            self.materials[ omat.name ] = omat
            self.ALL_MATERIALS[ omat.name ] = omat
            if omat.vertex_programs or omat.fragment_programs:  # ignore materials without programs
                self.ENUM_ITEMS.append( (omat.name, omat.name, url) )

    @classmethod # only call after parsing all material scripts
    def reset_rna(self, callback=None):
        bpy.types.Material.ogre_parent_material = EnumProperty(
            name="Script Inheritence",
            description='ogre parent material class',
            items=self.ENUM_ITEMS,
            #update=callback
        )
