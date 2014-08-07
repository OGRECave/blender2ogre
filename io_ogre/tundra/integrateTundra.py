# RUN: ./blender --python /path/to/integrateTundra.py
import os, sys, socket, select
import threading, time, subprocess, pickle

PBUFFSIZE = 2048
PREVIEW_PATH = '/tmp'
PREVIEW = '/tmp/fastpreview.txml'
if sys.platform == 'linux2':
	#CONFIG_TUNDRA = '%s/Tundra2' %os.environ['HOME']
	CONFIG_TUNDRA = '/opt/realxtend-tundra'
	#assert os.path.isdir( CONFIG_TUNDRA )
else:
	CONFIG_TUNDRA = 'C:\\Tundra'
	assert os.path.isdir( CONFIG_TUNDRA )


import bpy

sys.path.append( os.path.dirname(os.path.abspath(__file__)) )
import blender2ogre as b2ogre

print( b2ogre, dir(b2ogre) )
b2ogre.register()

print(dir(b2ogre))

#print( dir(bpy.app.handlers))
#def prerender( a ):
#	print( 'callback' )
#bpy.app.handlers.render_pre.append( prerender )


T = time.time()


## compact tags ##
class CompactByteCode(object): pass
P = CompactByteCode()
for i,tag in enumerate('name type transform data active materials'.split()):
	TAGS[ tag ] = chr(i)		# up to 256


def get_material_names( ob ):
	r = []
	for m in ob.data.materials:
		if m:	r.append( m.name )
		else: r.append( None )
	return r

def get_materials( ob ):
	r = []
	for m in ob.data.materials:
		if m:	r.append( m )
		else: r.append( None )
	return r


def decompose( mat ):
	loc, rot, scale = mat.decompose()
	loc = (loc.x, loc.z, -loc.y)
	#rot = (rot.w, rot.x, rot.z, -rot.y)
	x,z,y = rot.to_euler(); rot = (x,y,z)
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
  <plugin path="VlcPlugin" />
  <plugin path="SceneWidgetComponents" />    
  <plugin path="PythonScriptModule" />   
  <jsplugin path="MenuBar.js" />
  <jsplugin path="cameraapplication.js" />
  <jsplugin path="FirstPersonMouseLook.js" />
  <pyplugin path="%s" />
</Tundra>''' %TUNDRA_GEN_SCRIPT_PATH



TUNDRA_CONFIG_XML_PATH = '/tmp/tundra_config.xml'
with open( TUNDRA_CONFIG_XML_PATH, 'wb' ) as fp:
    fp.write( bytes(TUNDRA_CONFIG_XML,'utf-8') )



class TundraServer(object):
	def update_view( self, msg, sel ):
		msg['view'] = get_view_matrix()
	def update_selected( self, msg, sel ):
		msg['object'] = sel.name
		msg['type'] = sel.type
		msg['data-name'] = sel.data.name
		msg['transform'] =  decompose( sel.matrix_world.copy() )
		if sel.name not in self._objects:
			#bpy.ops.ogre.export_realxtend( filepath=PREVIEW, EX_MESH_OVERWRITE=False)
			self._objects[ sel.name ] = sel.type
			if sel.type == 'MESH':
				mats = b2ogre.dot_mesh( sel, path=PREVIEW_PATH )
				self.sync_material( sel )

			#if not self._scene_loaded:
			#	self._scene_loaded = True
			#	self.stream( {'command':'load', 'arg':PREVIEW} )


	def update_materials( self, msg, sel ):
		if sel.type != 'MESH': return

		msg['materials'] = get_material_names( sel )
		if not all( self._materials.values() ):
			for name in self._materials:
				if not self._materials[name]:
					self._materials[name] = True
					m = bpy.data.materials[ name ]
					data = b2ogre.generate_material( m, PREVIEW_PATH )
					print( data )
					with open(os.path.join(PREVIEW_PATH, name+'.material'), 'wb' ) as fp:
						fp.write( bytes(data,'utf-8') )


	def sync_mesh( self, ob ):
		if ob.name in self._objects:
			self._objects.pop( ob.name )
		print( self._area, dir(self._area) )
		print( self._region, dir(self._region) )
		self._region.tag_redraw()

	def sync_material( self, ob ):
		for m in get_materials( ob ):
			self._materials[ m.name ] = False
		self._region.tag_redraw()


	def __init__(self):
		self._scene_loaded = False
		self._objects = {}
		self._materials = {}
		self.buffer = []	# cmd buffer
		self.callbacks = [ self.update_view, self.update_selected, self.update_materials ]

		## launch Tundra ##
		if sys.platform == 'linux2':
			exe = os.path.join( CONFIG_TUNDRA, 'run-server.sh' )
			assert os.path.isfile( exe )
			cmd = [exe, '--config', TUNDRA_CONFIG_XML_PATH, '--fpslimit', '100', '--storage', '/tmp/']
			print( cmd )
			p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
		else:
			exe = os.path.join( CONFIG_TUNDRA, 'Tundra.exe' )
			assert os.path.isfile( exe )
			cmd = [exe, '--file', PREVIEW, '--config', TUNDRA_CONFIG_XML_PATH]
			p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

		self.proc = p
		self.socket = sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		host='localhost'; port = 9978
		sock.connect((host, port))
		print('socket connected', sock)


		self._handle = None
		self.setup_callback( bpy.context )
		self.ready = threading._allocate_lock()
		self.ID = threading._start_new_thread( 
			self.loop, (None,) 
		)
		print( '.....thread started......')

	def loop(self, none):
		self.active = True
		prev = time.time()
		while self.active:
			if not self.ready.locked(): time.sleep(0.001)	# not threadsafe
			else:	# threadsafe start

				if not bpy.context.active_object: continue

				now = time.time()
				if now - prev > 0.033:	# don't flood Tundra
					prev = now
					sel = bpy.context.active_object

					msg = {}
					for cb in self.callbacks:
						cb( msg, sel )
					self.ready.release()	      # thread release

					self.stream( msg )	# releases GIL
					if self.buffer:
						bin = self.buffer.pop()
						try:
							self.socket.sendall( bin )
						except:
							print('send all error!')
							time.sleep(0.5)
							pass

					else: print( 'NO CALLBACKS' )
				else:
					self.ready.release()


		print('thread exit')


	def threadsafe( self, reg ):
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
						self._handle = reg.callback_add(
							self.threadsafe, (reg,), 'PRE_VIEW' )
						self._area = area
						self._region = reg
						break


	def stream( self, o ):
		b = pickle.dumps( o, protocol=2 )
		print( 'streaming bytes', len(b) )
		n = len( b ); d = PBUFFSIZE - n -4
		if n > PBUFFSIZE:
			print( 'STREAM ERROR', n )
			return

		padding = b'#' * d

		if n < 10: header = '000%s' %n
		elif n < 100: header = '00%s' %n
		elif n < 1000: header = '0%s' %n
		else: header = '%s' %n
		header = bytes( header, 'utf-8' )
		assert len(header) == 4

		w = header + b + padding
		assert len(w) == PBUFFSIZE
		self.buffer.insert(0, w )
		return w


TundraSingleton = TundraServer()
print( 'ok' )

class _sync_mesh_op(bpy.types.Operator):
	'''sync mesh in tundra'''
	bl_idname = 'tundra.sync_mesh'
	bl_label = "sync mesh in tundra"
	bl_options = {'REGISTER'}
	@classmethod
	def poll(cls, context):
		if context.active_object and context.active_object.type in ('MESH','EMPTY') and context.mode != 'EDIT_MESH':
			if context.active_object.type == 'EMPTY' and context.active_object.dupli_type != 'GROUP': return False
			else: return True

	def invoke(self, context, event):
		TundraSingleton.sync_mesh( context.active_object )
		return {'FINISHED'}
bpy.utils.register_class( _sync_mesh_op )

class _sync_material_op(bpy.types.Operator):
	'''sync material in tundra'''
	bl_idname = 'tundra.sync_material'
	bl_label = "sync material in tundra"
	bl_options = {'REGISTER'}
	@classmethod
	def poll(cls, context):
		if context.active_object and context.active_object.type in ('MESH','EMPTY') and context.mode != 'EDIT_MESH':
			if context.active_object.type == 'EMPTY' and context.active_object.dupli_type != 'GROUP': return False
			else: return True

	def invoke(self, context, event):
		TundraSingleton.sync_material( context.active_object )
		return {'FINISHED'}
bpy.utils.register_class( _sync_material_op )


class tundraheader(bpy.types.Header):
	bl_space_type = 'INFO'
	def poll( self, context ):
		if context.active_object.type == 'MESH': return True

	def draw(self, context):
		layout = self.layout
		op = layout.operator( 'tundra.sync_mesh', text='mesh', icon='PLUG' )
		op = layout.operator( 'tundra.sync_material', text='material', icon='PLUG' )

bpy.utils.register_class( tundraheader )



