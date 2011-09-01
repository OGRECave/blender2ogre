import os, sys, time, pickle, socket, math
import threading, select

tundra = naali = None
try: import tundra
except: import naali

from PythonQt.QtGui import QVector3D


class Dummy(object): pass	# only needed for Tundra1

T = time.time()

## compact tags ##
TAGS = {}
for i,tag in enumerate('object type name transform data-name selected materials'.split()):
	TAGS[ tag ] = chr(i)		# up to 256

def get_entity( id ):
    return tundra.Scene().GetDefaultSceneRaw().GetEntityRaw(id)

def get_entity_component( id, type ):
    e = tundra.Scene().GetDefaultSceneRaw().GetEntityRaw(id)
    return e.GetComponentRaw("EC_%s" %type)


class TundraClient(object):
	def __init__(self):
		self.socket = sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		host='localhost'; port = 9978
		sock.bind((host, port))
		print('socket connected', sock)
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

		header = data[ : 4]
		s = data[ 4 : int(header)+4 ]
		objects = pickle.loads( s )	# protocol - blender sends a list of selected
		for o in objects: self.update_object( o )
		return True

	def update_object( self, o ):
		#scn = tundra.Scene().GetDefaultSceneRaw()
		#print( scn )

		name = o[ P.name ]
		if name not in self.objects:
			print('CreateEntity', name)
			e = Entity( o )
			self.objects[ name ] = e

		e = self.objects[ name ]
		e.update( d )

class Entity(object):
	"""
PythonScriptModule: (Entity (Entity 0x0C22B410), ['Action', 'Actions', 'AddComponent', 'Clone', 'ComponentAdded', 'ComponentRemoved', 'Components', 'ConnectAction', 'CreateComponent', 'Description', 'EnterView', 'EntityRemoved', 'Exec', 'GetAttribute', 'GetAttributes', 'GetComponent', 'GetComponentRaw', 'GetComponents', 'GetComponentsRaw', 'GetFramework', 'GetOrCreateComponent', 'GetOrCreateComponentRaw', 'Id', 'IsLocal', 'IsTemporary', 'LeaveView', 'Name', 'ParentScene', 'RemoveAction', 'RemoveComponent', 'RemoveComponentRaw', 'SerializeToXML', 'SerializeToXMLString', 'SetDescription', 'SetName', 'SetTemporary', 'ToString', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'description', 'destroyed', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'id', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'name', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'toString', 'tr'])
	"""

	def __init__(self, info):
		self.info = info
		if naali: self.entity = naali.createEntity()#; print( self.entity, dir(self.entity) )
		else: self.entity = tundra.Helper().CreateEntity()
		#self.entity.SetName( info['object'] )
		self.components = {}
		extras = []

		T = info[ P.type ]
		self.data_name = info[ P.data ][ P.name ]

		if T == 'MESH':
			extras.append( 'EC_Mesh' )
			self._mesh_url = 'local://%s.mesh' %self.data_name
			self._materials = info['materials']

		elif T == 'LAMP':
			extras.append( 'EC_Light' )

		#EC_TransformGizmo
		for tag in 'EC_Name EC_Placeable'.split() + extras:
			ec = self.entity.GetOrCreateComponentRaw( tag )
			self.components[ tag ] = ec
			setattr( self, tag, ec )
			print( ec, dir(ec) )

			if tag == 'EC_Light':
				ec.castShadows = True
				print( ec.diffColor, dir(ec.diffColor) )
				ec.constAtten = 1.0	# sane default

			if tag == 'EC_Mesh':
				print( '-'*80 )
				ec.SetMeshRef( self._mesh_url )
				#matname = ec.GetMaterialName( index )
				#print( 'EC_MESH - material name', matname )
				print( ec.meshMaterial, dir(ec.meshMaterial) )
				for i,matname in enumerate(self._materials):
					#u = 'local:///tmp/%s.material' %matname
					u = 'local://%s.material' %matname
					print( 'SETTING MATERIAL', u )
					#assert ec.SetMaterial( i, u )
					ec.SetMaterial( i, u )
				#ec.ApplyMaterial()


	"""
(EC_Mesh (EC_Mesh 0x0C3C47AC), 
['ApplyMaterial', 'AttributeChanged', 'AutoSetPlaceable', 'ComponentChanged', 'ComponentNameChanged', 'EmitAttributeChanged', 'ForceSkeletonUpdate', 'GetAdjustOrientation', 'GetAdjustPosition', 'GetAdjustScale', 'GetAdjustmentSceneNode', 'GetAttachmentEntity', 'GetAttachmentMaterialName', 'GetAttachmentMorphWeight', 'GetAttachmentNumMaterials', 'GetAttachmentOrientation', 'GetAttachmentPosition', 'GetAttachmentScale', 'GetAttributeNames', 'GetAttributeQVariant', 'GetAvailableBones', 'GetBone', 'GetBoneDerivedOrientation', 'GetBoneDerivedPosition', 'GetBoneOrientation', 'GetBonePosition', 'GetBoundingBox', 'GetDrawDistance', 'GetEntity', 'GetFramework', 'GetMatName', 'GetMaterialName', 'GetMeshName', 'GetMorphWeight', 'GetNumAttachments', 'GetNumMaterials', 'GetNumSubMeshes', 'GetPlaceable', 'GetSkeletonName', 'GetWorldSize', 'HasAttachmentMesh', 'HasDynamicStructure', 'HasMesh', 'IsTemporary', 'LocalToParent', 'LocalToWorld', 'MaterialChanged', 'MeshAboutToBeDestroyed', 'MeshChanged', 'NetworkSyncEnabled', 'NumAttributes', 'ParentEntity', 'ParentEntityDetached', 'ParentEntitySet', 'ParentScene', 'RemoveAllAttachments', 'RemoveAttachmentMesh', 'RemoveMesh', 'SetAdjustOrientation', 'SetAdjustPosition', 'SetAdjustScale', 'SetAttachmentMaterial', 'SetAttachmentMesh', 'SetAttachmentMorphWeight', 'SetAttachmentOrientation', 'SetAttachmentPosition', 'SetAttachmentScale', 'SetCastShadows', 'SetDrawDistance', 'SetMaterial', 'SetMesh', 'SetMeshRef', 'SetMeshWithSkeleton', 'SetMorphWeight', 'SetNetworkSyncEnabled', 'SetPlaceable', 'SetTemporary', 'SetUpdateMode', 'SkeletonChanged', 'UpdateMode', 'View', 'ViewEnabled', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'castShadows', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'disconnect', 'drawDistance', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'meshMaterial', 'meshRef', 'moveToThread', 'name', 'networkSyncEnabled', 'nodeTransformation', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'skeletonRef', 'startTimer', 'thread', 'timerEvent', 'tr', 'typeName', 'updateMode'])

	"""

	def update( self, info ):
		trans = info['transform']
		#print( 'TRANs', trans )
		#print( self.EC_Placeable, dir(self.EC_Placeable) )
		pos, rot, scale = trans
		x,y,z = pos
		#self.EC_Placeable.SetPosition( x,y,z )	# T2
		#self.EC_Placeable.position.setX(x)		# not allowed
		self.EC_Placeable.position = QVector3D( x,-z,y )

		#print( self.EC_Placeable.orientation )
		x,z,y = rot
		self.EC_Placeable.orientationEuler = QVector3D( math.degrees(x),math.degrees(y),math.degrees(z) )
		#q = self.EC_Placeable.Orientation
		#print( q, dir(q) )
		#print( self.EC_Placeable.SetOrientation( q ) )


		x,y,z = scale
		self.EC_Placeable.scale = QVector3D( x,y,z )
		#self.EC_Placeable.SetScale( x,y,z )		# T2



		if 0:	# Rex bug, SetMaterial is broken
			ec = self.EC_Mesh
			for i,matname in enumerate(self._materials):
				#u = 'local:///tmp/%s.material' %matname
				u = '%s.material' %matname
				print( u )
				#assert ec.SetMaterial( i, u )
				res = ec.SetMaterial( i, u )
				print('result', res )
			ec.ApplyMaterial()

	"""
 (EC_Name (EC_Name 0x0C2294EC), ['AttributeChanged', 'ComponentChanged', 'ComponentNameChanged', 'EmitAttributeChanged', 'GetAttributeNames', 'GetAttributeQVariant', 'GetFramework', 'HasDynamicStructure', 'IsTemporary', 'NetworkSyncEnabled', 'NumAttributes', 'ParentEntity', 'ParentEntityDetached', 'ParentEntitySet', 'ParentScene', 'SetNetworkSyncEnabled', 'SetTemporary', 'SetUpdateMode', 'UpdateMode', 'ViewEnabled', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'description', 'destroyed', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'name', 'networkSyncEnabled', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'tr', 'typeName', 'updateMode'])

PythonScriptModule: (EC_Placeable (EC_Placeable 0x0C22A7D4), ['AboutToBeDestroyed', 'AttributeChanged', 'Children', 'ComponentChanged', 'ComponentNameChanged', 'DumpNodeHierarhy', 'EmitAttributeChanged', 'GetAttributeNames', 'GetAttributeQVariant', 'GetFramework', 'HasDynamicStructure', 'Hide', 'IsAttached', 'IsTemporary', 'LocalToParent', 'LocalToWorld', 'NetworkSyncEnabled', 'NumAttributes', 'Orientation', 'ParentEntity', 'ParentEntityDetached', 'ParentEntitySet', 'ParentScene', 'ParentToLocal', 'Position', 'Scale', 'SetNetworkSyncEnabled', 'SetOrientation', 'SetOrientationAndScale', 'SetParent', 'SetPosition', 'SetScale', 'SetTemporary', 'SetTransform', 'SetUpdateMode', 'SetWorldTransform', 'Show', 'ToggleVisibility', 'UpdateMode', 'ViewEnabled', 'WorldOrientation', 'WorldPosition', 'WorldScale', 'WorldToLocal', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'disconnect', 'drawDebug', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'name', 'networkSyncEnabled', 'objectName', 'parent', 'parentBone', 'parentRef', 'property', 'removeEventFilter', 'selectionLayer', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'tr', 'transform', 'typeName', 'updateMode', 'visible'])

PythonScriptModule: (EC_TransformGizmo (EC_TransformGizmo 0x0C22BEC4), ['AttributeChanged', 'ComponentChanged', 'ComponentNameChanged', 'CurrentGizmoType', 'EmitAttributeChanged', 'GetAttributeNames', 'GetAttributeQVariant', 'GetFramework', 'GizmoType', 'HasDynamicStructure', 'IsTemporary', 'IsVisible', 'NetworkSyncEnabled', 'NumAttributes', 'ParentEntity', 'ParentEntityDetached', 'ParentEntitySet', 'ParentScene', 'Rotate', 'Rotated', 'Scale', 'Scaled', 'SetCurrentGizmoType', 'SetNetworkSyncEnabled', 'SetPosition', 'SetTemporary', 'SetUpdateMode', 'SetVisible', 'Translate', 'Translated', 'UpdateMode', 'ViewEnabled', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'name', 'networkSyncEnabled', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'tr', 'typeName', 'updateMode'])


17:30:30 [PythonScript] (EC_Light (EC_Light 0x952ced8), ['AttributeChanged', 'ComponentChanged', 'ComponentNameChanged', 'EmitAttributeChanged', 'GetAttributeNames', 'GetAttributeQVariant', 'GetFramework', 'GetNetworkSyncEnabled', 'GetNumberOfAttributes', 'GetParentEntity', 'GetParentScene', 'GetUpdateMode', 'HasDynamicStructure', 'IsSerializable', 'IsTemporary', 'ParentEntityDetached', 'ParentEntitySet', 'SetNetworkSyncEnabled', 'SetTemporary', 'SetUpdateMode', 'ViewEnabled', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'castShadows', 'childEvent', 'children', 'className', 'connect', 'constAtten', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'diffColor', 'direction', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'innerAngle', 'installEventFilter', 'isWidgetType', 'killTimer', 'linearAtten', 'moveToThread', 'name', 'networkSyncEnabled', 'objectName', 'outerAngle', 'parent', 'property', 'quadraAtten', 'range', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'specColor', 'startTimer', 'thread', 'timerEvent', 'tr', 'type', 'typeName', 'updateMode'])

	"""

Client = TundraClient()


def attach_frame_update_callback( func ):
	'''(FrameAPI (FrameAPI 0x01C0F920), ['DelayedExecute', 'FrameNumber', 'PostFrameUpdate', 'Updated', 'WallClockTime', '__dict__', '__doc__', '__module__', '__weakref__', 'blockSignals', 'childEvent', 'children', 'className', 'connect', 'customEvent', 'delete', 'deleteLater', 'destroyed', 'disconnect', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'help', 'installEventFilter', 'isWidgetType', 'killTimer', 'moveToThread', 'objectName', 'parent', 'property', 'removeEventFilter', 'setObjectName', 'setParent', 'setProperty', 'signalsBlocked', 'startTimer', 'thread', 'timerEvent', 'tr'])
	'''
	if naali:
		naali.frame.connect( 'Updated(float)', func )

	else:
		frameAPI = tundra.Frame()
		frameAPI.connect( 'Updated(float)', func )


attach_frame_update_callback( Client.update )


