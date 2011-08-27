# RUN: ./blender --python /path/to/integrateTundra.py
import os, sys, socket, select

PBUFFSIZE = 2048
PREVIEW = '/tmp/fastpreview.txml'
CONFIG_TUNDRA = '%s/Tundra2' %os.environ['HOME']
# might need 1024 bytes to stream: camera, object transform, material updates


import bpy
#sys.path.append( '~/blender2ogre' )
#import blender2ogre as b2ogre
#print( b2ogre )
b2ogre = bpy.ops.ogre

#print( dir(bpy.app.handlers))
#def prerender( a ):
#	print( 'callback' )
#bpy.app.handlers.render_pre.append( prerender )

import threading, time, subprocess, pickle

T = time.time()

def decompose( mat ):
	loc, rot, scale = mat.decompose()
	loc = (loc.x, loc.z, -loc.y)
	rot = (rot.w, rot.x, rot.z, -rot.y)
	scale = ( abs(scale.x), abs(scale.z), abs(scale.y) )
	return loc, rot, scale

def get_view_matrix():
	'''
<bpy_struct, RegionView3D at 0x7fe77e154438> ['__doc__', '__module__', '__slots__', 'bl_rna', 'is_perspective', 'lock_rotation', 'perspective_matrix', 'rna_type', 'show_sync_view', 'use_box_clip', 'view_distance', 'view_location', 'view_matrix', 'view_perspective', 'view_rotation'
	'''
	#print( dir(bpy.context) )
	#print('&'*80)
	#print( bpy.context.region_data, dir(bpy.context.region_data) )
	#print('%'*80)
	v = bpy.context.region_data
	assert v.is_perspective
	#print( dir( v.view_matrix) )
	return decompose(v.view_matrix.copy())


	for area in bpy.context.window.screen.areas:
		print( 'area', area )
		print( dir(area) )
		if area.type == 'VIEW_3D':
			for reg in area.regions:
				if reg.type == 'WINDOW':
					print( 'WIN REG', reg )
					print( dir(reg) )




TUNDRA_GEN_SCRIPT_PATH = '/tmp/interfaceTundra.py'	# for now put there by TundraBlender shell script

TUNDRA_CONFIG_XML = '''<?xml version="1.0"?>
<Tundra>
  <plugin path="OgreRenderingModule" />
  <plugin path="EnvironmentModule" />          
  <plugin path="OgreAssetEditorModule" />    
  <plugin path="PhysicsModule" />         
  <plugin path="TundraProtocolModule" />     
  <plugin path="JavascriptModule" />          
  <plugin path="AssetModule" />         
  <plugin path="AvatarModule" />               
  <plugin path="ECEditorModule" />            
  <plugin path="DebugStatsModule" />         
  <plugin path="SkyXHydrax" />                 
  <plugin path="SceneWidgetComponents" />    
  <plugin path="VlcPlugin" />                
  <plugin path="PythonScriptModule" />   
  <jsplugin path="cameraapplication.js" />
  <jsplugin path="FirstPersonMouseLook.js" />
  <jsplugin path="MenuBar.js" />
  <pyplugin path="%s" />
</Tundra>''' %TUNDRA_GEN_SCRIPT_PATH

TUNDRA_CONFIG_XML_PATH = '/tmp/tundra_config.xml'
with open( TUNDRA_CONFIG_XML_PATH, 'wb' ) as fp:
    fp.write( bytes(TUNDRA_CONFIG_XML,'utf-8') )


#try: os.unlink('/tmp/my_fifo')
#except: pass
#os.mkfifo('/tmp/my_fifo')

class Tundra(object):
	def __init__(self):
		exe = os.path.join( CONFIG_TUNDRA, 'Tundra.exe' )
		assert os.path.isfile( exe )

		#os.mkfifo('/tmp/io')

		if 0:	# debug pipe/fifo
			cmd = ['python', '/tmp/interfaceTundra.py']
			print( cmd )
			p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

		elif sys.platform == 'linux2':
			#cmd = ['wine', exe, '--file', PREVIEW, '--config', TUNDRA_CONFIG_XML_PATH]
			cmd = ['wine', exe, '--config', TUNDRA_CONFIG_XML_PATH, '--fpslimit', '100']
			print( cmd )
			p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
		else:
			cmd = [exe, '--file', PREVIEW, '--config', TUNDRA_CONFIG_XML_PATH]
			p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
		print( '--------------------tundra subprocess-------------------', p )
		self.proc = p
		#self.pipe = p.stdin

		#r,w=os.pipe()
		#print('PIPES', r, w)
		#r,w=os.fdopen(r,'rb',2048), os.fdopen(w,'wb',2048)
		#self.pipe = w
		#r.close()

		time.sleep(0.1)
		print('trying to open fifo for write')

		#self.pipe = TPIPE = open( '/tmp/io', 'wb' )	# OPEN AFTER client 'r+'
		#print( TPIPE )

		self.socket = sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		host='localhost'; port = 9978
		sock.connect((host, port))
		print('socket connected', sock)



class SafeThread(object):
	def update_view( self, msg, sel ):
		msg['view'] = get_view_matrix()
	def update_selected( self, msg, sel ):
		msg['object'] = sel.name
		msg['type'] = sel.type
		msg['data-name'] = sel.data.name
		msg['transform'] =  decompose( sel.matrix_world.copy() )
		if sel.name not in self._objects:
			bpy.ops.ogre.export_realxtend( filepath=PREVIEW)
			self._objects[ sel.name ] = True
			if not self._scene_loaded:
				self._scene_loaded = True
				self.stream( {'command':'load', 'arg':PREVIEW} )

	def __init__(self):
		self._scene_loaded = False
		self._objects = {}
		self.buffer = []	# cmd buffer
		self.callbacks = [ self.update_view, self.update_selected ]
		self.slave = Tundra()
		#self.pipe = self.slave.pipe

		self._handle = None
		self.setup_callback( bpy.context )
		self.ready = threading._allocate_lock()
		self.ID = threading._start_new_thread( 
			self.loop, (None,) 
		)
		print( '.....thread started......')

	def loop(self, none):
		self.active = True
		i = 0; prev = time.time()
		while self.active:
			if not self.ready.locked(): time.sleep(0.001)
			else:	# threadsafe start
				#elif hasattr(bpy.context, 'active_object'):	# thread safe now
				#poll = select.select( [], [self.slave.socket], [] )
				#print( 'BLENDER POLL', poll )
				#if not poll[1]:
				#	print('waiting for tundra....')
				#	time.sleep(0.01)
				#	continue

				if not bpy.context.active_object: continue

				now = time.time()
				if now - prev > 0.033:	# don't flood Tundra
					prev = now
					sel = bpy.context.active_object

					msg = {}
					for cb in self.callbacks:
						cb( msg, sel )
					self.stream( msg )
					self.ready.release()	# thread release
					time.sleep(0.00001)	# release to blender
					#print( i ); i = 0
					if self.buffer:
						#print( 'sendall socket' )
						bin = self.buffer.pop()
						try:
							self.slave.socket.sendall( bin )
						except:
							print('send all error!')
							time.sleep(0.5)
							pass

					else: print( 'NO CALLBACKS' )
				else:
					self.ready.release()


				################
				#print( time.time()-T )
				#time.sleep( 0.001)



			i += 1
		print('thread exit')

	def preview( self, reg ):
		pass
	def postpixel( self, reg ):
		if not self.ready.locked():
			self.ready.acquire()
			time.sleep(0.0001)
			while self.ready.locked():	# must block to be safe
				time.sleep(0.0001)
		else: pass #time.sleep(0.033) dont block

	_handle = None
	def setup_callback( self, context ):
		if self._handle: return self._handle
		for area in bpy.context.window.screen.areas:
			if area.type == 'VIEW_3D':
				for reg in area.regions:
					if reg.type == 'WINDOW':
						# PRE_VIEW, POST_VIEW, POST_PIXEL
						## thread safe from pre_view to post_pixel?
						self._handle = reg.callback_add(		# better performance
							self.postpixel, (reg,), 'PRE_VIEW' )
						#self._handle = reg.callback_add(
						#	self.postpixel, (reg,), 'POST_PIXEL' )

						break


	def stream( self, o ):
		b = pickle.dumps( o, protocol=2 )
		print( 'streaming bytes', len(b) )
		n = len( b ); d = PBUFFSIZE - n -3
		if n > PBUFFSIZE:
			print( 'STREAM ERROR', n )
			return

		padding = b'#' * d

		if n < 10: header = '00%s' %n
		elif n < 100: header = '0%s' %n
		else: header = '%s' %n
		header = bytes( header, 'utf-8' )
		assert len(header) == 3

		print( 'to pipe', len(b))
		print( 'pickle', n )
		print( 'delta', d )
		w = header + b + padding
		assert len(w) == PBUFFSIZE
		self.buffer.insert(0, w )
		return w


t = SafeThread()
print( 'ok' )



class tundraheader(bpy.types.Header):
	bl_space_type = 'INFO'
	def draw(self, context):
		layout = self.layout
		#op = layout.operator( OGRE_toggle_toolbar_op.bl_idname, icon='UI' )
		layout.label( 'TundraBlender' )
bpy.utils.register_class( tundraheader )

