#!/usr/bin/python
import os, sys, array, time, ctypes

if __name__ == '__main__':	# standalone from python2
	sys.path.append('../../rpythonic')
	import rpythonic
	rpythonic.set_pypy_root( '../../pypy' )
	import pypy.rpython.lltypesystem.rffi as rffi
	from pypy.rlib import streamio

else:	# from inside blender
	import rpythonic

################################
rpy = rpythonic.RPython( 'blender2ogre' )


class Mesh(object):

    def __init__(self, data):
        self.numVerts = N = len( data.vertices )
        self.numFaces = Nfaces = len(data.faces)

        self.vertex_positions = (ctypes.c_float * (N * 3))()
        data.vertices.foreach_get( 'co', self.vertex_positions )
        v = self.vertex_positions

        self.vertex_normals = (ctypes.c_float * (N * 3))()
        data.vertices.foreach_get( 'normal', self.vertex_normals )

        self.faces = (ctypes.c_uint * (Nfaces * 4))()
        data.faces.foreach_get( 'vertices_raw', self.faces )

        self.faces_normals = (ctypes.c_float * (Nfaces * 3))()
        data.faces.foreach_get( 'normal', self.faces_normals )

        self.faces_smooth = (ctypes.c_bool * Nfaces)() 
        data.faces.foreach_get( 'use_smooth', self.faces_smooth )

        self.faces_material_index = (ctypes.c_ushort * Nfaces)() 
        data.faces.foreach_get( 'material_index', self.faces_material_index )

        self.vertex_colors = []
        if len( data.vertex_colors ):
            vc = data.vertex_colors[0]
            n = len(vc.data)
            # no colors_raw !!?
            self.vcolors1 = (ctypes.c_float * (n * 3))()  # face1
            vc.data.foreach_get( 'color1', self.vcolors1 )
            self.vertex_colors.append( self.vcolors1 )

            self.vcolors2 = (ctypes.c_float * (n * 3))()  # face2
            vc.data.foreach_get( 'color2', self.vcolors2 )
            self.vertex_colors.append( self.vcolors2 )

            self.vcolors3 = (ctypes.c_float * (n * 3))()  # face3
            vc.data.foreach_get( 'color3', self.vcolors3 )
            self.vertex_colors.append( self.vcolors3 )

            self.vcolors4 = (ctypes.c_float * (n * 3))()  # face4
            vc.data.foreach_get( 'color4', self.vcolors4 )
            self.vertex_colors.append( self.vcolors4 )

        self.uv_textures = []
        if data.uv_textures.active:
            for layer in data.uv_textures:
                n = len(layer.data) * 8
                a = (ctypes.c_float * n)()
                layer.data.foreach_get( 'uv_raw', a )   # 4 faces
                self.uv_textures.append( a )


def save( blenderobject, path ):
	cmesh = Mesh( blenderobject.data )
	start = time.time()
	dotmesh(
		path,
		ctypes.addressof( cmesh.faces ),
		ctypes.addressof( cmesh.faces_smooth ),
		ctypes.addressof( cmesh.faces_material_index ),
		ctypes.addressof( cmesh.vertex_positions ),
		ctypes.addressof( cmesh.vertex_normals ),
		cmesh.numFaces,
		cmesh.numVerts,
	)
	print( 'mesh dumped in %s seconds' %(time.time()-start) )


@rpy.bind(
	path=str,
	facesAddr=int, 
	facesSmoothAddr=int,
	facesMatAddr=int,
	vertsPosAddr=int,
	vertsNorAddr=int,
	numFaces=int,
	numVerts=int,
	materials=[str],
)
def dotmesh( path, facesAddr, facesSmoothAddr, facesMatAddr, vertsPosAddr, vertsNorAddr, numFaces, numVerts, materials ):
	for matname in materials:
		print( 'Material Name: %s' %matname )

	file = streamio.open_file_as_stream( path, 'w')

	faces = rffi.cast( rffi.UINTP, facesAddr )		# face vertex indices
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
		smooth = ord( facesSmooth[ fidx ] )		# ctypes.c_bool > char > int

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

			SIG = (pos,nor, matidx)
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
				'<position x="%s" y="%s" z="%s" />' %pos,	# funny that tuple is valid here
				'<normal x="%s" y="%s" z="%s" />' %nor,
				'</vertex>'
			]
			VB.append( '\n'.join(xml) )

			ogre_vert_index += 1

		triangles.append( triangle )
	VB.append( '</vertexbuffer>' )
	VB.append( '</sharedgeometry>' )

	file.write( '\n'.join(VB) )
	del VB		# free memory

	SMS = ['<submeshes>']
	#for matidx, matname in ...:
	SM = [
		'<submesh usesharedvertices="true" use32bitindexes="true" material="%s">' %'somemat',
		'<faces count="%s">' %'100',
	]
	for tri in triangles:
		#x,y,z = tri	# rpython bug, when in a new 'block' need to unpack/repack tuple
		#s = '<face v1="%s" v2="%s" v3="%s" />' %(x,y,z)
		assert isinstance(tri,tuple) #and len(tri)==3		# this also works
		s = '<face v1="%s" v2="%s" v3="%s" />' %tri		# but tuple is not valid here
		SM.append( s )
	SM.append( '</faces>' )
	SM.append( '</submesh>' )

	file.write( '\n'.join(SM) )
	file.close()






if __name__ == '__main__':
	rpy.cache(refresh=1)


