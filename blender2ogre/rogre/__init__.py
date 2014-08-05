
try:
    import .rogremesh as Rmesh
except:
    Rmesh = None
    print( 'WARNING: "io_export_rogremesh" is missing' )

if Rmesh and Rmesh.rpy.load():
    _USE_RPYTHON_ = True
else:
    _USE_RPYTHON_ = False
    print( 'Rpython module is not cached, you must exit Blender to compile the module:' )
    print( 'cd io_export_rogremesh; python rogremesh.py' )



# If we end up here we are outside blender (compile optional C module)
assert __name__ == '__main__'
print('Trying to compile Rpython C-library')
assert sys.version_info.major == 2  # rpython only works from Python2
print('...searching for rpythonic...')
sys.path.append('../rpythonic')
import rpythonic
rpythonic.set_pypy_root( '../pypy' )
import pypy.rpython.lltypesystem.rffi as rffi
from pypy.rlib import streamio
rpy = rpythonic.RPython( 'blender2ogre' )

@rpy.bind(
    path=str,
    facesAddr=int,
    facesSmoothAddr=int,
    facesMatAddr=int,
    vertsPosAddr=int,
    vertsNorAddr=int,
    numFaces=int,
    numVerts=int,
    materialNames=str, # [str] is too tricky to convert py-list to rpy-list
)

def dotmesh( path, facesAddr, facesSmoothAddr, facesMatAddr, vertsPosAddr, vertsNorAddr, numFaces, numVerts, materialNames ):
    print('PATH----------------', path)
    materials = []
    for matname in materialNames.split(';'):
        print( 'Material Name: %s' %matname )
        materials.append( matname )

    file = streamio.open_file_as_stream( path, 'w')

    faces = rffi.cast( rffi.UINTP, facesAddr ) # face vertex indices
    facesSmooth = rffi.cast( rffi.CCHARP, facesSmoothAddr )
    facesMat = rffi.cast( rffi.USHORTP, facesMatAddr )

    vertsPos = rffi.cast( rffi.FLOATP, vertsPosAddr )
    vertsNor = rffi.cast( rffi.FLOATP, vertsNorAddr )

    VB = [
        '<sharedgeometry>',
        '<vertexbuffer positions="true" normals="true">'
    ]
    fastlookup = {}
    ogre_vert_index = 0
    triangles = []
    for fidx in range( numFaces ):
        smooth = ord( facesSmooth[ fidx ] ) # ctypes.c_bool > char > int

        matidx = facesMat[ fidx ]
        i = fidx*4
        ai = faces[ i ]; bi = faces[ i+1 ]
        ci = faces[ i+2 ]; di = faces[ i+3 ]

        triangle = []
        for J in [ai, bi, ci]:
            i = J*3
            x = rffi.cast( rffi.DOUBLE, vertsPos[ i ] )
            y = rffi.cast( rffi.DOUBLE, vertsPos[ i+1 ] )
            z = rffi.cast( rffi.DOUBLE, vertsPos[ i+2 ] )
            pos = (x,y,z)
            #if smooth:
            x = rffi.cast( rffi.DOUBLE, vertsNor[ i ] )
            y = rffi.cast( rffi.DOUBLE, vertsNor[ i+1 ] )
            z = rffi.cast( rffi.DOUBLE, vertsNor[ i+2 ] )
            nor = (x,y,z)

            SIG = (pos,nor)#, matidx)
            skip = False
            if J in fastlookup:
                for otherSIG in fastlookup[ J ]:
                    if SIG == otherSIG:
                        triangle.append( fastlookup[J][otherSIG] )
                        skip = True
                        break

                if not skip:
                    triangle.append( ogre_vert_index )
                    fastlookup[ J ][ SIG ] = ogre_vert_index

            else:
                triangle.append( ogre_vert_index )
                fastlookup[ J ] = { SIG : ogre_vert_index }

            if skip: continue

            xml = [
                '<vertex>',
                '<position x="%s" y="%s" z="%s" />' %pos,    # funny that tuple is valid here
                '<normal x="%s" y="%s" z="%s" />' %nor,
                '</vertex>'
            ]
            VB.append( '\n'.join(xml) )

            ogre_vert_index += 1

        triangles.append( triangle )
    VB.append( '</vertexbuffer>' )
    VB.append( '</sharedgeometry>' )

    file.write( '\n'.join(VB) )
    del VB        # free memory

    SMS = ['<submeshes>']
    #for matidx, matname in ...:
    SM = [
        '<submesh usesharedvertices="true" use32bitindexes="true" material="%s" operationtype="triangle_list">' % 'somemat',
        '<faces count="%s">' %'100',
    ]
    for tri in triangles:
        #x,y,z = tri    # rpython bug, when in a new 'block' need to unpack/repack tuple
        #s = '<face v1="%s" v2="%s" v3="%s" />' %(x,y,z)
        assert isinstance(tri,tuple) #and len(tri)==3        # this also works
        s = '<face v1="%s" v2="%s" v3="%s" />' %tri        # but tuple is not valid here
        SM.append( s )
    SM.append( '</faces>' )
    SM.append( '</submesh>' )

    file.write( '\n'.join(SM) )
    file.close()

rpy.cache(refresh=1)
sys.exit('OK: module compiled and cached')

