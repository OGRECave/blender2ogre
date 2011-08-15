#!/usr/bin/python
import os, sys, array, time, ctypes
sys.path.append('../../rpythonic')
import rpythonic
rpythonic.set_pypy_root( '../../pypy' )
################################
rpy = rpythonic.RPython()

import pypy.rpython.lltypesystem.rffi as rffi

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
	facesSmooth = rffi.cast( rffi.UCHARP, facesSmoothAddr )
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
		smooth = facesSmooth[ fidx ]
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
			x = -rffi.cast( rffi.DOUBLE, vertsNor[ i ] )
			z = rffi.cast( rffi.DOUBLE, vertsNor[ i+1 ] )
			y = rffi.cast( rffi.DOUBLE, vertsNor[ i+2 ] )
			nor = (x,y,z)

			ID = (pos,nor)
			if ID not in fastlookup:
				xml = [
					'<vertex>',
					'<position x="%s" y="%s" z="%s" />' %pos,
					'<normal x="%s" y="%s" z="%s" />' %nor,
					'</vertex>'
				]
				#VB.append( '\n'.join(xml) )

				fastlookup[ ID ] = ogre_vert_index
				triangle.append( ogre_vert_index )
				ogre_vert_index += 1
			else:
				triangle.append( fastlookup[ID] )
		triangles.append( triangle )
	VB.append( '</vertexbuffer>' )
	VB.append( '</sharedgeometry>' )
	print( '\n'.join(VB) )

	SMS = ['<submeshes>']
	#for matidx, matname in ...:
	SM = [
		'<submesh usesharedvertices="true" use32bitindexes="true" material="%s">' %'somemat',
		'<faces count="%s">' %100,
	]
	for tri in triangles:
		s = '<face v1="%s" v2="%s" v3="%s" />' %tri
		SM.append( s )
	SM.append( '</faces>' )
	SM.append( '</submesh>' )

	print( '\n'.join(SM) )

		
rpy.cache('blender2ogre', refresh=1)

############### testing ##############


