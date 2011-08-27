import os, sys, time, pickle, socket
import threading, select

T = time.time()
print( '*'*80 )
try:
	import tundra

except:
	print( 'running pipe debug mode' )


def get_entity( id ):
    return tundra.Scene().GetDefaultSceneRaw().GetEntityRaw(id)

def get_entity_component( id, type ):
    e = tundra.Scene().GetDefaultSceneRaw().GetEntityRaw(id)
    return e.GetComponentRaw("EC_%s" %type)

print('^'*80)
print('HELLO WORLD')
print('^'*80)

#print( 'CLIENT opening fifo' )
#PIPE = open( '/tmp/io', 'r+')

def test():
	#r,w=os.pipe()
	#print('SPIPES', r, w)
	#r = 13; w = 16
	#r,w=os.fdopen(r,'r',2048), os.fdopen(w,'w',2048)
	#pipe = r
	#w.close()
	print( 'trying to open fifo READ....' )
	pipe = open( '/tmp/io', 'r+' )#, os.O_RDONLY | os.O_NONBLOCK)
	print( 'ok' )
	while True:
		print('(child) waiting.................................................' )
		#data = sys.stdin.read( 2048 )
		data = pipe.read( 2048, 0.1 )
		pipe.flush()
		print( '(child) got bytes', len(data) )
		if not data:
			#time.sleep(0.01); continue
			print( '(child) parent crashed...' )
			break
		assert len(data) == 2048

		header = data[ : 3]
		print( '(child) reading length', header )
		s = data[ 3 : int(header)+3 ]
		p = pickle.loads( s )
		print( 'UNpickle', p )

#test()
#assert 0


def testUDP():
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	host='localhost'; port = 8081
	sock.bind((host, port))
	print('socket connected', sock)
	print( 'ok' )
	while True:
		print('(child SOCKET) waiting.................................................' )
		#data = sys.stdin.read( 2048 )
		data = sock.recv( 2048 )
		print( '(child) got bytes', len(data) )
		if not data:
			#time.sleep(0.01); continue
			print( '(child) parent crashed...' )
			break
		assert len(data) == 2048

		header = data[ : 3]
		print( '(child) reading length', header )
		s = data[ 3 : int(header)+3 ]
		p = pickle.loads( s )
		print( 'UNpickle', p )

#testUDP()
#assert 0

class Thread(object):
	def __init__(self):
		#self.ID = threading._start_new_thread( self.loop, (None,) )
		#self.loop(1)

		self.socket = sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		host='localhost'; port = 9978
		sock.bind((host, port))
		print('socket connected', sock)

		print( '/'*120 )
		print( '(child THREAD)', host, port )

		self.objects = {}

	def loop(self, none):
		while True: self.update( 1.0 )
	def update( self, _time ):
		sock = self.socket
		poll = select.select( [ sock ], [], [], 0.01 )
		#print( 'poll', poll )
		if not poll[0]:
			#print('WAITING')
			time.sleep(0.01)
			return True

		data = sock.recv( 2048 )
		assert len(data) == 2048
		if not data:
			#time.sleep(0.01); continue
			print( '(child) parent crashed...' )
			return

		header = data[ : 3]
		#print( '(child) reading length', header )
		s = data[ 3 : int(header)+3 ]
		p = pickle.loads( s )
		print( 'UNpickle', p )
		self.process( p )
		return True

	def process( self, d ):
		scn = tundra.Scene().GetDefaultSceneRaw()
		print( scn )

		#time.sleep(0.01)

		if 'object' in d:
			name = d['object']
			if name not in self.objects:
				print('CreateEntity', name)
				e = Entity( d )
				self.objects[ name ] = e
			e = self.objects[ name ]
			e.update( d )

class Entity(object):
	"""
PythonScriptModule: (Entity (Entity 0x0C22B410), ['Action', 'Actions', 'AddComponent', 'Clone', 'ComponentAdded', 'ComponentRemoved', 'Components', 'ConnectAction', 'CreateComponent', 'Description', 'EnterView', 'EntityRemoved', 'Exec', 'GetAttribute', 'GetAttributes', 'GetComponent', 'GetComponentRaw', 'GetComponents', 'GetComponentsRaw', 'GetFramework', 'GetOrCreateComponent', 'GetOrCreateComponentRaw', 'Id', 'IsLocal', 'IsTemporary', 'LeaveView', 'Name', 'ParentScene', 'RemoveAction', 'RemoveComponent', 'RemoveComponentRaw', 'SerializeToXML', 'SerializeToXMLString', 'SetDescription', 'SetName', 'SetTemporary', 'ToString', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'description', 'destroyed', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'id', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'name', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'toString', 'tr'])
	"""

	def __init__(self, info):
		self.info = info
		self.entity = tundra.Helper().CreateEntity()
		self.components = {}
		extras = []
		if 'type' in info:
			T = info['type']
			self.data_name = info['data-name']

			if T == 'MESH':
				extras.append( 'EC_Mesh' )
				self._mesh_url = 'local:///tmp/%s.mesh' %self.data_name

			elif T == 'LAMP':
				extras.append( 'EC_Light' )

		#EC_TransformGizmo
		for tag in 'EC_Name EC_Placeable'.split() + extras:
			ec = self.entity.GetOrCreateComponentRaw( tag )
			self.components[ tag ] = ec
			setattr( self, tag, ec )
			print( ec, dir(ec) )
			if tag == 'EC_Mesh':
				print( '-'*80 )
				ec.SetMeshRef( self._mesh_url )
				#matname = ec.GetMaterialName( index )
				#print( 'EC_MESH - material name', matname )

		print( self.EC_Name, dir( self.EC_Name) )

	"""
PythonScriptModule: (EC_Mesh (EC_Mesh 0x0C3C47AC), ['ApplyMaterial', 'AttributeChanged', 'AutoSetPlaceable', 'ComponentChanged', 'ComponentNameChanged', 'EmitAttributeChanged', 'ForceSkeletonUpdate', 'GetAdjustOrientation', 'GetAdjustPosition', 'GetAdjustScale', 'GetAdjustmentSceneNode', 'GetAttachmentEntity', 'GetAttachmentMaterialName', 'GetAttachmentMorphWeight', 'GetAttachmentNumMaterials', 'GetAttachmentOrientation', 'GetAttachmentPosition', 'GetAttachmentScale', 'GetAttributeNames', 'GetAttributeQVariant', 'GetAvailableBones', 'GetBone', 'GetBoneDerivedOrientation', 'GetBoneDerivedPosition', 'GetBoneOrientation', 'GetBonePosition', 'GetBoundingBox', 'GetDrawDistance', 'GetEntity', 'GetFramework', 'GetMatName', 'GetMaterialName', 'GetMeshName', 'GetMorphWeight', 'GetNumAttachments', 'GetNumMaterials', 'GetNumSubMeshes', 'GetPlaceable', 'GetSkeletonName', 'GetWorldSize', 'HasAttachmentMesh', 'HasDynamicStructure', 'HasMesh', 'IsTemporary', 'LocalToParent', 'LocalToWorld', 'MaterialChanged', 'MeshAboutToBeDestroyed', 'MeshChanged', 'NetworkSyncEnabled', 'NumAttributes', 'ParentEntity', 'ParentEntityDetached', 'ParentEntitySet', 'ParentScene', 'RemoveAllAttachments', 'RemoveAttachmentMesh', 'RemoveMesh', 'SetAdjustOrientation', 'SetAdjustPosition', 'SetAdjustScale', 'SetAttachmentMaterial', 'SetAttachmentMesh', 'SetAttachmentMorphWeight', 'SetAttachmentOrientation', 'SetAttachmentPosition', 'SetAttachmentScale', 'SetCastShadows', 'SetDrawDistance', 'SetMaterial', 'SetMesh', 'SetMeshRef', 'SetMeshWithSkeleton', 'SetMorphWeight', 'SetNetworkSyncEnabled', 'SetPlaceable', 'SetTemporary', 'SetUpdateMode', 'SkeletonChanged', 'UpdateMode', 'View', 'ViewEnabled', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'castShadows', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'disconnect', 'drawDistance', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'meshMaterial', 'meshRef', 'moveToThread', 'name', 'networkSyncEnabled', 'nodeTransformation', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'skeletonRef', 'startTimer', 'thread', 'timerEvent', 'tr', 'typeName', 'updateMode'])

	"""

	def update( self, info ):
		trans = info['transform']
		print( 'TRANs', trans )
		pos, rot, scale = trans
		x,y,z = pos
		self.EC_Placeable.SetPosition( x,y,z )
		x,y,z = scale
		self.EC_Placeable.SetScale( x,y,z )
		#q = self.EC_Placeable.Orientation
		#print( q, dir(q) )
		#print( self.EC_Placeable.SetOrientation( q ) )

	"""
 (EC_Name (EC_Name 0x0C2294EC), ['AttributeChanged', 'ComponentChanged', 'ComponentNameChanged', 'EmitAttributeChanged', 'GetAttributeNames', 'GetAttributeQVariant', 'GetFramework', 'HasDynamicStructure', 'IsTemporary', 'NetworkSyncEnabled', 'NumAttributes', 'ParentEntity', 'ParentEntityDetached', 'ParentEntitySet', 'ParentScene', 'SetNetworkSyncEnabled', 'SetTemporary', 'SetUpdateMode', 'UpdateMode', 'ViewEnabled', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'description', 'destroyed', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'name', 'networkSyncEnabled', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'tr', 'typeName', 'updateMode'])

PythonScriptModule: (EC_Placeable (EC_Placeable 0x0C22A7D4), ['AboutToBeDestroyed', 'AttributeChanged', 'Children', 'ComponentChanged', 'ComponentNameChanged', 'DumpNodeHierarhy', 'EmitAttributeChanged', 'GetAttributeNames', 'GetAttributeQVariant', 'GetFramework', 'HasDynamicStructure', 'Hide', 'IsAttached', 'IsTemporary', 'LocalToParent', 'LocalToWorld', 'NetworkSyncEnabled', 'NumAttributes', 'Orientation', 'ParentEntity', 'ParentEntityDetached', 'ParentEntitySet', 'ParentScene', 'ParentToLocal', 'Position', 'Scale', 'SetNetworkSyncEnabled', 'SetOrientation', 'SetOrientationAndScale', 'SetParent', 'SetPosition', 'SetScale', 'SetTemporary', 'SetTransform', 'SetUpdateMode', 'SetWorldTransform', 'Show', 'ToggleVisibility', 'UpdateMode', 'ViewEnabled', 'WorldOrientation', 'WorldPosition', 'WorldScale', 'WorldToLocal', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'disconnect', 'drawDebug', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'name', 'networkSyncEnabled', 'objectName', 'parent', 'parentBone', 'parentRef', 'property', 'removeEventFilter', 'selectionLayer', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'tr', 'transform', 'typeName', 'updateMode', 'visible'])

PythonScriptModule: (EC_TransformGizmo (EC_TransformGizmo 0x0C22BEC4), ['AttributeChanged', 'ComponentChanged', 'ComponentNameChanged', 'CurrentGizmoType', 'EmitAttributeChanged', 'GetAttributeNames', 'GetAttributeQVariant', 'GetFramework', 'GizmoType', 'HasDynamicStructure', 'IsTemporary', 'IsVisible', 'NetworkSyncEnabled', 'NumAttributes', 'ParentEntity', 'ParentEntityDetached', 'ParentEntitySet', 'ParentScene', 'Rotate', 'Rotated', 'Scale', 'Scaled', 'SetCurrentGizmoType', 'SetNetworkSyncEnabled', 'SetPosition', 'SetTemporary', 'SetUpdateMode', 'SetVisible', 'Translate', 'Translated', 'UpdateMode', 'ViewEnabled', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'name', 'networkSyncEnabled', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'tr', 'typeName', 'updateMode'])
	"""

t = Thread()
for i in range(100):
	print i
	time.sleep(0.01)
print('thread exit')

frameAPI = tundra.Frame()
print( frameAPI, dir( frameAPI ) )
'''(FrameAPI (FrameAPI 0x01C0F920), ['DelayedExecute', 'FrameNumber', 'PostFrameUpdate', 'Updated', 'WallClockTime', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'tr'])
'''
print( '_'*80)

print( frameAPI.Updated, dir(frameAPI.Updated) )

def mycb(*args): print('hello world') 
#updater = frameAPI.Updated(1.0)
#print( updater, dir(updater) )

#frameAPI.Updated = mycb
#frameAPI.connect( 'Updated(float)', mycb )
frameAPI.connect( 'Updated(float)', t.update )


print( 'EXIT' )
