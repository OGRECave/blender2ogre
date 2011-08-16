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


def dump( cmesh ):
	start = time.time()
	dotmesh(
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
	facesAddr=int, 
	facesSmoothAddr=int,
	facesMatAddr=int,
	vertsPosAddr=int,
	vertsNorAddr=int,
	numFaces=int,
	numVerts=int,
)
def dotmesh( facesAddr, facesSmoothAddr, facesMatAddr, vertsPosAddr, vertsNorAddr, numFaces, numVerts ):
	faces = rffi.cast( rffi.UINTP, facesAddr )
	facesSmooth = rffi.cast( rffi.CCHARP, facesSmoothAddr )
	facesMat = rffi.cast( rffi.USHORTP, facesMatAddr )

	vertsPos = rffi.cast( rffi.FLOATP, vertsPosAddr )
	vertsNor = rffi.cast( rffi.FLOATP, vertsNorAddr )

	file = streamio.open_file_as_stream('/tmp/rpystream', 'w')

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
			x = -rffi.cast( rffi.DOUBLE, vertsPos[ i ] )
			z = rffi.cast( rffi.DOUBLE, vertsPos[ i+1 ] )
			y = rffi.cast( rffi.DOUBLE, vertsPos[ i+2 ] )
			pos = (x,y,z)
			#if smooth:
			x = -rffi.cast( rffi.DOUBLE, vertsNor[ i ] )
			z = rffi.cast( rffi.DOUBLE, vertsNor[ i+1 ] )
			y = rffi.cast( rffi.DOUBLE, vertsNor[ i+2 ] )
			nor = (x,y,z)

			ID = (pos,nor)
			if ID not in fastlookup:
				xml = [
					'<vertex>',
					'<position x="%s" y="%s" z="%s" />' %pos,	# funny that tuple is valid here
					'<normal x="%s" y="%s" z="%s" />' %nor,
					'</vertex>'
				]
				VB.append( '\n'.join(xml) )

				fastlookup[ ID ] = ogre_vert_index
				triangle.append( ogre_vert_index )
				ogre_vert_index += 1
			else:
				triangle.append( fastlookup[ID] )
		triangles.append( triangle )
	VB.append( '</vertexbuffer>' )
	VB.append( '</sharedgeometry>' )

	file.write( '\n'.join(VB) )


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


