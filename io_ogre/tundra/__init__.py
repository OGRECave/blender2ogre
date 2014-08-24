
import bpy
from ..ogre.export import _OgreCommonExport_
from bpy.props import BoolProperty, StringProperty, FloatProperty, IntProperty, EnumProperty
from .. import config
from ..config import CONFIG
from .. import xml

class _TXML_(_OgreCommonExport_):
    '''
    <component type="EC_Script" sync="1" name="myscript">
        <attribute value="" name="Script ref"/>
        <attribute value="false" name="Run on load"/>
        <attribute value="0" name="Run mode"/>
        <attribute value="" name="Script application name"/>
        <attribute value="" name="Script class name"/>
    </component>
    '''

    def create_tundra_document( self, context ):
        # todo: Make a way in the gui to give prefix for the refs
        # This can be very useful if you want to give deployment URL
        # eg. "http://www.myassets.com/myscene/". By default this needs
        # to be an empty string, it will operate best for local preview
        # and importing the scene content to existing scenes with relative refs.
        proto = ''

        doc = xml.RDocument()
        scn = doc.createElement('scene')
        doc.appendChild( scn )

        # EC_Script
        if 0: # todo: tundra bug (what does this mean?)
            e = doc.createElement( 'entity' )
            doc.documentElement.appendChild( e )
            e.setAttribute('id', len(doc.documentElement.childNodes)+1 )

            c = doc.createElement( 'component' ); e.appendChild( c )
            c.setAttribute( 'type', 'EC_Script' )
            c.setAttribute( 'sync', '1' )
            c.setAttribute( 'name', 'myscript' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Script ref')
            #a.setAttribute('value', "%s%s"%(proto,TUNDRA_GEN_SCRIPT_PATH) )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Run on load')
            a.setAttribute('value', 'true' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Run mode')
            a.setAttribute('value', '0' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Script application name')
            a.setAttribute('value', 'blender2ogre' )

        # Check lighting settings
        sun = hemi = None
        if get_lights_by_type('SUN'):
            sun = get_lights_by_type('SUN')[0]
        if get_lights_by_type('HEMI'):
            hemi = get_lights_by_type('HEMI')[0]

        # Environment
        if bpy.context.scene.world.mist_settings.use_mist or sun or hemi:
            # Entity for environment components
            e = doc.createElement( 'entity' )
            doc.documentElement.appendChild( e )
            e.setAttribute('id', len(doc.documentElement.childNodes)+1 )

            # EC_Fog
            c = doc.createElement( 'component' ); e.appendChild( c )
            c.setAttribute( 'type', 'EC_Fog' )
            c.setAttribute( 'sync', '1' )
            c.setAttribute( 'name', 'Fog' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Color')
            if bpy.context.scene.world.mist_settings.use_mist:
                A = bpy.context.scene.world.mist_settings.intensity
                R,G,B = bpy.context.scene.world.horizon_color
                a.setAttribute('value', '%s %s %s %s'%(R,G,B,A))
            else:
                a.setAttribute('value', '0.4 0.4 0.4 1.0')

            if bpy.context.scene.world.mist_settings.use_mist:
                mist = bpy.context.scene.world.mist_settings

                a = doc.createElement('attribute'); c.appendChild( a )
                a.setAttribute('name', 'Start distance')
                a.setAttribute('value', mist.start)

                a = doc.createElement('attribute'); c.appendChild( a )
                a.setAttribute('name', 'End distance')
                a.setAttribute('value', mist.start+mist.depth)

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Exponential density')
            a.setAttribute('value', 0.001)

            # EC_EnvironmentLight
            c = doc.createElement( 'component' ); e.appendChild( c )
            c.setAttribute( 'type', 'EC_EnvironmentLight' )
            c.setAttribute( 'sync', '1' )
            c.setAttribute( 'name', 'Environment Light' )

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Sunlight color')
            if sun:
                R,G,B = sun.data.color
                a.setAttribute('value', '%s %s %s 1' %(R,G,B))
            else:
                a.setAttribute('value', '0 0 0 1')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Brightness') # brightness of sunlight
            if sun:
                a.setAttribute('value', sun.data.energy*10) # 10=magic
            else:
                a.setAttribute('value', '0')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Ambient light color')
            if hemi:
                R,G,B = hemi.data.color * hemi.data.energy * 3.0
                if R>1.0: R=1.0
                if G>1.0: G=1.0
                if B>1.0: B=1.0
                a.setAttribute('value', '%s %s %s 1' %(R,G,B))
            else:
                a.setAttribute('value', '0 0 0 1')

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Sunlight direction vector')
            a.setAttribute('value', '-0.25 -1.0 -0.25')   # TODO, get the sun rotation from blender

            a = doc.createElement('attribute'); c.appendChild( a )
            a.setAttribute('name', 'Sunlight cast shadows')
            a.setAttribute('value', 'true')

        # EC_SkyX
        if context.scene.world.ogre_skyX:
            c = doc.createElement( 'component' ); e.appendChild( c )
            c.setAttribute( 'type', 'EC_SkyX' )
            c.setAttribute( 'sync', '1' )
            c.setAttribute( 'name', 'SkyX' )

            a = doc.createElement('attribute'); a.setAttribute('name', 'Weather (volumetric clouds only)')
            den = (
                context.scene.world.ogre_skyX_cloud_density_x,
                context.scene.world.ogre_skyX_cloud_density_y
            )
            a.setAttribute('value', '%s %s' %den)
            c.appendChild( a )

            config = (
                ('time', 'Time multiplier'),
                ('volumetric_clouds','Volumetric clouds'),
                ('wind','Wind direction'),
            )
            for bname, aname in config:
                a = doc.createElement('attribute')
                a.setAttribute('name', aname)
                s = str( getattr(context.scene.world, 'ogre_skyX_'+bname) )
                a.setAttribute('value', s.lower())
                c.appendChild( a )

        return doc

    def export(self):
        pass
        # this was copied from the OgreCommonExport function ogre_export

        # realXtend Tundra .txml scene description export
        # TUNDRA TODO re enable this export type
        #if self.EXPORT_TYPE == 'REX':
        #    rex = self.create_tundra_document(context)
        #    proxies = []
        #    for ob in objects:
        #        print("  Processing %s [%s]" % (ob.name, ob.type))

        #        # This seemingly needs to be done as its done in .scene
        #        # export. Fixed a bug that no .meshes were exported when doing
        #        # a Tundra export.
        #        if ob.type == 'MESH':
        #            ob.data.update(calc_tessface=True)

        #        # EC_Light
        #        if ob.type == 'LAMP':
        #            TE = self.tundra_entity(rex, ob, path=path, collision_proxies=proxies)
        #            self.tundra_light( TE, ob )
        #        # EC_Sound
        #        elif ob.type == 'SPEAKER':
        #            TE = self.tundra_entity(rex, ob, path=path, collision_proxies=proxies)
        #        # EC_Mesh
        #        elif ob.type == 'MESH' and len(ob.data.tessfaces):
        #            if ob.modifiers and ob.modifiers[0].type=='MULTIRES' and ob.use_multires_lod:
        #                mod = ob.modifiers[0]
        #                basename = ob.name
        #                dataname = ob.data.name
        #                ID = uid( ob ) # ensure uid
        #                TE = self.tundra_entity(rex, ob, path=path, collision_proxies=proxies)

        #                for level in range( mod.total_levels+1 ):
        #                    ob.uid += 1
        #                    mod.levels = level
        #                    ob.name = '%s.LOD%s' %(basename,level)
        #                    ob.data.name = '%s.LOD%s' %(dataname,level)
        #                    TE = self.tundra_entity(
        #                        rex, ob, path=path, collision_proxies=proxies, parent=basename,
        #                        matrix=mathutils.Matrix(), visible=False
        #                    )
        #                    self.tundra_mesh( TE, ob, url, exported_meshes )

        #                ob.uid = ID
        #                ob.name = basename
        #                ob.data.name = dataname
        #            else:
        #                TE = self.tundra_entity( rex, ob, path=path, collision_proxies=proxies )
        #                self.tundra_mesh( TE, ob, url, exported_meshes )

        #    # EC_RigidBody separate collision meshes
        #    for proxy in proxies:
        #        self.dot_mesh(
        #            proxy,
        #            path=os.path.split(url)[0],
        #            force_name='_collision_%s' %proxy.data.name
        #        )

        #    if self.EX_SCENE:
        #        if not url.endswith('.txml'):
        #            url += '.txml'
        #        data = rex.toprettyxml()
        #        f = open( url, 'wb' ); f.write( bytes(data,'utf-8') ); f.close()
        #        print('  Exported Tundra Scene:', url)

    # Creates new Tundra entity
    def tundra_entity( self, doc, ob, path='/tmp', collision_proxies=[], parent=None, matrix=None,visible=True ):
        assert not ob.subcollision

        #  Tundra TRANSFORM
        if not matrix:
            matrix = ob.matrix_world.copy()

        # todo: Make a way in the gui to give prefix for the refs
        # This can be very useful if you want to give deployment URL
        # eg. "http://www.myassets.com/myscene/". By default this needs
        # to be an empty string, it will operate best for local preview
        # and importing the scene content to existing scenes with relative refs.
        proto = ''

        # Entity
        entityid = uid(ob)
        objectname = clean_object_name(ob.name)
        print("  Creating Tundra Enitity with ID", entityid)

        e = doc.createElement( 'entity' )
        doc.documentElement.appendChild( e )
        e.setAttribute('id', entityid)

        # EC_Name
        print ("    - EC_Name with", objectname)

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Name")
        c.setAttribute('sync', '1')
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "name" )
        a.setAttribute('value', objectname )
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "description" )
        a.setAttribute('value', "" )

        # EC_Placeable
        print ("    - EC_Placeable ")

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Placeable")
        c.setAttribute('sync', '1')
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Transform" )
        x,y,z = swap(matrix.to_translation())
        loc = '%6f,%6f,%6f' %(x,y,z)
        x,y,z = swap(matrix.to_euler())
        x = math.degrees( x ); y = math.degrees( y ); z = math.degrees( z )
        if ob.type == 'CAMERA':
            x -= 90
        elif ob.type == 'LAMP':
            x += 90
        rot = '%6f,%6f,%6f' %(x,y,z)
        x,y,z = swap(matrix.to_scale())
        scl = '%6f,%6f,%6f' %(abs(x),abs(y),abs(z)) # Tundra2 clamps any negative to zero
        a.setAttribute('value', "%s,%s,%s" %(loc,rot,scl) )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Show bounding box" )
        a.setAttribute('value', "false" )
        # Don't mark bounding boxes to show in Tundra!
        #if ob.show_bounds or ob.type != 'MESH':
        #    a.setAttribute('value', "true" )
        #else:
        #    a.setAttribute('value', "false" )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Visible" )
        if visible:
            a.setAttribute('value', 'true') # overrides children's setting - not good!
        else:
            a.setAttribute('value', 'false')

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Selection layer" )
        a.setAttribute('value', 1)

        # Tundra parenting to EC_Placeable.
        # todo: Verify this inserts correct ent name or id here.
        #   <attribute value="" name="Parent entity ref"/>
        #   <attribute value="" name="Parent bone name"/>
        if parent:
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Parent entity ref" )
            a.setAttribute('value', parent)

        if ob.type != 'MESH':
            c = doc.createElement('component'); e.appendChild( c )
            c.setAttribute('type', 'EC_Name')
            c.setAttribute('sync', '1')
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "name" )
            a.setAttribute('value', objectname)

        # EC_Sound: Supports wav and ogg
        if ob.type == 'SPEAKER':
            print ("    - EC_Sound")
            c = doc.createElement('component'); e.appendChild( c )
            c.setAttribute('type', 'EC_Sound')
            c.setAttribute('sync', '1')

            if ob.data.sound:
                abspath = bpy.path.abspath( ob.data.sound.filepath )
                soundpath, soundfile = os.path.split( abspath )
                soundref = "%s%s" % (proto, soundfile)
                print ("      Sounds ref:", soundref)
                a = doc.createElement('attribute'); c.appendChild(a)
                a.setAttribute('name', 'Sound ref' )
                a.setAttribute('value', soundref)
                if not os.path.isfile( os.path.join(path,soundfile) ):
                    open( os.path.join(path,soundfile), 'wb' ).write( open(abspath,'rb').read() )

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', 'Sound radius inner' )
            a.setAttribute('value', ob.data.cone_angle_inner)

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', 'Sound radius outer' )
            a.setAttribute('value', ob.data.cone_angle_outer)

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', 'Sound gain' )
            a.setAttribute('value', ob.data.volume)

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', 'Play on load' )
            if ob.data.play_on_load:
                a.setAttribute('value', 'true')
            else:
                a.setAttribute('value', 'false')

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', 'Loop sound' )
            if ob.data.loop:
                a.setAttribute('value', 'true')
            else:
                a.setAttribute('value', 'false')

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', 'Spatial' )
            if ob.data.use_spatial:
                a.setAttribute('value', 'true')
            else:
                a.setAttribute('value', 'false')

        # EC_Camera
        ''' todo: This is really not very helpful. Apps define
            camera logic in Tundra. By default you will have
            a freecamera to move around the scene etc. This created
            camera wont be activated except if a script does so.
            Best leave camera (creation) logic for the inworld apps.
            At least remove the default "export cameras" for txml. '''
        if ob.type == 'CAMERA':
            print ("    - EC_Camera")
            c = doc.createElement('component'); e.appendChild( c )
            c.setAttribute('type', 'EC_Camera')
            c.setAttribute('sync', '1')
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Up vector" )
            a.setAttribute('value', '0.0 1.0 0.0')
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Near plane" )
            a.setAttribute('value', '0.01')
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Far plane" )
            a.setAttribute('value', '2000')
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Vertical FOV" )
            a.setAttribute('value', '45')
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Aspect ratio" )
            a.setAttribute('value', '')

        NTF = None

        # EC_Rigidbody
        # Any object can have physics, although it needs
        # EC_Placeable to have position etc.
        if ob.physics_mode != 'NONE' or ob.collision_mode != 'NONE':
            TundraTypes = {
                'BOX' : 0,
                'SPHERE' : 1,
                'CYLINDER' : 2,
                'CONE' : 0, # Missing in Tundra
                'CAPSULE' : 3,
                'TRIANGLE_MESH' : 4,
                #'HEIGHT_FIELD': 5, # Missing in Blender
                'CONVEX_HULL' : 6
            }

            com = doc.createElement('component'); e.appendChild( com )
            com.setAttribute('type', 'EC_RigidBody')
            com.setAttribute('sync', '1')

            # Mass
            # * Does not affect static collision types (TriMesh and ConvexHull)
            # * You can have working collisions with mass 0
            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Mass')
            if ob.physics_mode == 'RIGID_BODY':
                a.setAttribute('value', ob.game.mass)
            else:
                a.setAttribute('value', '0.0')

            SHAPE = a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Shape type')
            a.setAttribute('value', TundraTypes[ ob.game.collision_bounds_type ] )

            print ("    - EC_RigidBody with shape type", TundraTypes[ob.game.collision_bounds_type])

            M = ob.game.collision_margin
            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Size')
            if ob.game.collision_bounds_type in 'TRIANGLE_MESH CONVEX_HULL'.split():
                a.setAttribute('value', '%s %s %s' %(1.0+M, 1.0+M, 1.0+M) )
            else:
                #x,y,z = swap(ob.matrix_world.to_scale())
                x,y,z = swap(ob.dimensions)
                a.setAttribute('value', '%s %s %s' %(abs(x)+M,abs(y)+M,abs(z)+M) )

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Collision mesh ref')
            #if ob.game.use_collision_compound:
            if ob.collision_mode == 'DECIMATED':
                proxy = None
                for child in ob.children:
                    if child.subcollision and child.name.startswith('DECIMATED'):
                        proxy = child; break
                if proxy:
                    collisionref = "%s_collision_%s.mesh" % (proto, proxy.data.name)
                    a.setAttribute('value', collisionref)
                    if proxy not in collision_proxies:
                        collision_proxies.append( proxy )
                else:
                    print('[WARNINIG]: Collision proxy mesh not found' )
                    assert 0
            elif ob.collision_mode == 'TERRAIN':
                NTF = save_terrain_as_NTF( path, ob )
                SHAPE.setAttribute( 'value', '5' ) # HEIGHT_FIELD
            elif ob.type == 'MESH':
                # todo: Remove this. There is no need to set mesh collision ref
                # if TriMesh or ConvexHull is used, it will be auto picked from EC_Mesh
                # in the same Entity.
                collisionref = "%s%s.mesh" % (proto, clean_object_name(ob.data.name))
                a.setAttribute('value', collisionref)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Friction')
            #avg = sum( ob.game.friction_coefficients ) / 3.0
            a.setAttribute('value', ob.physics_friction)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Restitution')
            a.setAttribute('value', ob.physics_bounce)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Linear damping')
            a.setAttribute('value', ob.game.damping)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Angular damping')
            a.setAttribute('value', ob.game.rotation_damping)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Linear factor')
            a.setAttribute('value', '1.0 1.0 1.0')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Angular factor')
            a.setAttribute('value', '1.0 1.0 1.0')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Kinematic')
            a.setAttribute('value', 'false' )

            # todo: Find out what Phantom actually means and if this
            # needs to be set for NONE collision rigids. I don't actually
            # see any reason to make EC_RigidBody if collision is NONE
            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Phantom')
            if ob.collision_mode == 'NONE':
                a.setAttribute('value', 'true' )
            else:
                a.setAttribute('value', 'false' )

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Draw Debug')
            a.setAttribute('value', 'false' )

            # Never mark rigids to have draw debug, it can
            # be toggled in tundra for visual debugging.
            #if ob.collision_mode == 'NONE':
            #    a.setAttribute('value', 'false' )
            #else:
            #    a.setAttribute('value', 'true' )

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Linear velocity')
            a.setAttribute('value', '0.0 0.0 0.0')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Angular velocity')
            a.setAttribute('value', '0.0 0.0 0.0')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Collision Layer')
            a.setAttribute('value', -1)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Collision Mask')
            a.setAttribute('value', -1)

        # EC_Terrain
        if NTF:
            xp = NTF['xpatches']
            yp = NTF['ypatches']
            depth = NTF['depth']

            print ("    - EC_Terrain")
            com = doc.createElement('component'); e.appendChild( com )
            com.setAttribute('type', 'EC_Terrain')
            com.setAttribute('sync', '1')

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Transform')
            x,y,z = ob.dimensions
            sx,sy,sz = ob.scale
            x *= 1.0/sx
            y *= 1.0/sy
            z *= 1.0/sz
            #trans = '%s,%s,%s,' %(-xp/4, -z/2, -yp/4)
            trans = '%s,%s,%s,' %(-xp/4, -depth, -yp/4)
            # scaling in Tundra happens after translation
            nx = x/(xp*16)
            ny = y/(yp*16)
            trans += '0,0,0,%s,%s,%s' %(nx,depth, ny)
            a.setAttribute('value', trans )

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Grid Width')
            a.setAttribute('value', xp)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Grid Height')
            a.setAttribute('value', yp)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Tex. U scale')
            a.setAttribute('value', 1.0)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Tex. V scale')
            a.setAttribute('value', 1.0)

            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Material')
            a.setAttribute('value', '')

            for i in range(4):
                a = doc.createElement('attribute'); com.appendChild( a )
                a.setAttribute('name', 'Texture %s' %i)
                a.setAttribute('value', '')

            # todo: Check that NTF['name'] is the actual valid asset ref
            # and not the disk path.
            heightmapref = "%s%s" % (proto, NTF['name'])
            print ("      Heightmap ref:", heightmapref)
            a = doc.createElement('attribute'); com.appendChild( a )
            a.setAttribute('name', 'Heightmap')
            a.setAttribute('value', heightmapref )

        # Enitity XML generation done, return the element.
        return e

    # EC_Mesh
    def tundra_mesh( self, e, ob, url, exported_meshes ):
        # todo: Make a way in the gui to give prefix for the refs
        # This can be very useful if you want to give deployment URL
        # eg. "http://www.myassets.com/myscene/". By default this needs
        # to be an empty string, it will operate best for local preview
        # and importing the scene content to existing scenes with relative refs.
        proto = ''

        objectname = clean_object_name(ob.data.name)
        meshname = "%s.mesh" % objectname
        meshref = "%s%s.mesh" % (proto, objectname)

        print ("    - EC_Mesh")
        print ("      - Mesh ref:", meshref)

        if self.EX_MESH:
            murl = os.path.join( os.path.split(url)[0], meshname )
            exists = os.path.isfile( murl )
            if not exists or (exists and self.EX_MESH_OVERWRITE):
                if meshname not in exported_meshes:
                    exported_meshes.append( meshname )
                    self.dot_mesh( ob, os.path.split(url)[0] )

        doc = e.document

        if ob.find_armature():
            print ("    - EC_AnimationController")
            c = doc.createElement('component'); e.appendChild( c )
            c.setAttribute('type', "EC_AnimationController")
            c.setAttribute('sync', '1')

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Mesh")
        c.setAttribute('sync', '1')

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Mesh ref" )
        a.setAttribute('value',  meshref)

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Mesh materials" )

        # Query object its materials and make a proper material ref string of it.
        # note: We assume blindly here that the 'submesh' indexes are correct in the material list.
        mymaterials = ob.data.materials
        if mymaterials is not None and len(mymaterials) > 0:
            mymatstring = '' # generate ; separated material list
            for mymat in mymaterials:
                if mymat is None:
                    continue

                mymatstring += proto + material_name(mymat, True) + '.material;'
            mymatstring = mymatstring[:-1]  # strip ending ;
            a.setAttribute('value', mymatstring )
        else:
            # default to nothing to avoid error prints in .txml import
            a.setAttribute('value', "" )

        if ob.find_armature():
            skeletonref = "%s%s.skeleton" % (proto, clean_object_name(ob.data.name))
            print ("      Skeleton ref:", skeletonref)
            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', "Skeleton ref" )
            a.setAttribute('value', skeletonref)

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', "Draw distance" )
        if ob.use_draw_distance:
            a.setAttribute('value', ob.draw_distance )
        else:
            a.setAttribute('value', "0" )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'Cast shadows' )
        if ob.cast_shadows:
            a.setAttribute('value', 'true' )
        else:
            a.setAttribute('value', 'false' )

    # EC_Light
    def tundra_light( self, e, ob ):
        '''
            <component type="EC_Light" sync="1">
            <attribute value="1" name="light type"/>
            <attribute value="1 1 1 1" name="diffuse color"/>
            <attribute value="1 1 1 1" name="specular color"/>
            <attribute value="true" name="cast shadows"/>
            <attribute value="29.9999828" name="light range"/>
            <attribute value="1" name="brightness"/>
            <attribute value="0" name="constant atten"/>
            <attribute value="1" name="linear atten"/>
            <attribute value="0" name="quadratic atten"/>
            <attribute value="30" name="light inner angle"/>
            <attribute value="40" name="light outer angle"/>
            </component>
        '''

        if ob.data.type not in 'POINT SPOT'.split():
            return

        doc = e.document

        c = doc.createElement('component'); e.appendChild( c )
        c.setAttribute('type', "EC_Light")
        c.setAttribute('sync', '1')

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'light type' )
        if ob.data.type=='POINT':
            a.setAttribute('value', '0' )
        elif ob.data.type=='SPOT':
            a.setAttribute('value', '1' )
        #2 = directional light.  blender has no directional light?

        R,G,B = ob.data.color
        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'diffuse color' )
        if ob.data.use_diffuse:
            a.setAttribute('value', '%s %s %s 1' %(R,G,B) )
        else:
            a.setAttribute('value', '0 0 0 1' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'specular color' )
        if ob.data.use_specular:
            a.setAttribute('value', '%s %s %s 1' %(R,G,B) )
        else:
            a.setAttribute('value', '0 0 0 1' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'cast shadows' )
        if ob.data.type=='HEMI':
            a.setAttribute('value', 'false' ) # HEMI no .shadow_method
        elif ob.data.shadow_method != 'NOSHADOW':
            a.setAttribute('value', 'true' )
        else:
            a.setAttribute('value', 'false' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'light range' )
        a.setAttribute('value', ob.data.distance*2 )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'brightness' )
        a.setAttribute('value', ob.data.energy )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'constant atten' )
        a.setAttribute('value', '0' )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'linear atten' )
        energy = ob.data.energy
        if energy <= 0.0:
            energy = 0.001
        a.setAttribute('value', (1.0/energy)*0.25 )

        a = doc.createElement('attribute'); c.appendChild(a)
        a.setAttribute('name', 'quadratic atten' )
        a.setAttribute('value', '0.0' )

        if ob.data.type=='SPOT':
            outer = math.degrees(ob.data.spot_size) / 2.0
            inner = outer * (1.0-ob.data.spot_blend)

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', 'light inner angle' )
            a.setAttribute('value', '%s'%inner )

            a = doc.createElement('attribute'); c.appendChild(a)
            a.setAttribute('name', 'light outer angle' )
            a.setAttribute('value', '%s' %outer )

class INFO_OT_createRealxtendExport( bpy.types.Operator, _TXML_):
    '''Export RealXtend Scene'''
    bl_idname = "ogre.export_realxtend"
    bl_label = "Export RealXtend"
    bl_options = {'REGISTER', 'UNDO'}

    EXPORT_TYPE = 'REX'

class TundraPreviewOp( _OgreCommonExport_, bpy.types.Operator ):
    '''helper to open Tundra2 (realXtend)'''
    bl_idname = 'tundra.preview'
    bl_label = "opens Tundra2 in a non-blocking subprocess"
    bl_options = {'REGISTER'}
    EXPORT_TYPE = 'REX'

    filepath= StringProperty(
        name="File Path",
        description="Filepath used for exporting Tundra .txml file",
        maxlen=1024,
        default="/tmp/preview.txml",
        subtype='FILE_PATH')
    # override defaults
    EX_FORCE_CAMERA = BoolProperty(
        name="Force Camera",
        description="export active camera",
        default=False)
    # override defaults
    EX_FORCE_LAMPS = BoolProperty(
        name="Force Lamps",
        description="export all lamps",
        default=False)

    @classmethod
    def poll(cls, context):
        if context.active_object and context.mode != 'EDIT_MESH':
            return True

    def invoke(self, context, event):
        global TundraSingleton
        syncmats = []
        obs = []
        if TundraSingleton:
            actob = context.active_object
            obs = TundraSingleton.deselect_previously_updated(context)
            for ob in obs:
                if ob.type=='MESH':
                    syncmats.append( ob )
                    if ob.name == actob.name:
                        export_mesh( ob, path='/tmp/rex' )

        if not os.path.isdir( '/tmp/rex' ): os.makedirs( '/tmp/rex' )
        path = '/tmp/rex/preview.txml'
        self.ogre_export( path, context, force_material_update=syncmats )
        if not TundraSingleton:
            TundraSingleton = TundraPipe( context )
        elif self.EX_SCENE:
            TundraSingleton.load( context, path )

        for ob in obs:
            ob.select = True # restore selection
        return {'FINISHED'}

## realXtend Tundra preview
## todo: This only work if the custom py script is enabled in Tundra
## It's nice when it works but PythonScriptModule is not part of the
## default Tundra distro anymore, so this is atm kind of dead.
TundraSingleton = None

class Tundra_StartPhysicsOp(bpy.types.Operator):
    '''TundraSingleton helper'''
    bl_idname = 'tundra.start_physics'
    bl_label = "start physics"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if TundraSingleton: return True
    def invoke(self, context, event):
        TundraSingleton.start()
        return {'FINISHED'}

class Tundra_StopPhysicsOp(bpy.types.Operator):
    '''TundraSingleton helper'''
    bl_idname = 'tundra.stop_physics'
    bl_label = "stop physics"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if TundraSingleton: return True
    def invoke(self, context, event):
        TundraSingleton.stop()
        return {'FINISHED'}

class Tundra_PhysicsDebugOp(bpy.types.Operator):
    '''TundraSingleton helper'''
    bl_idname = 'tundra.toggle_physics_debug'
    bl_label = "stop physics"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if TundraSingleton: return True
    def invoke(self, context, event):
        TundraSingleton.toggle_physics_debug()
        return {'FINISHED'}

class Tundra_ExitOp(bpy.types.Operator):
    '''TundraSingleton helper'''
    bl_idname = 'tundra.exit'
    bl_label = "quit tundra"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if TundraSingleton: return True
    def invoke(self, context, event):
        TundraSingleton.exit()
        return {'FINISHED'}

## Server object to talk with realXtend Tundra with UDP
## Requires Tundra to be running a py script.

class Server(object):
    def stream( self, o ):
        b = pickle.dumps( o, protocol=2 ) #protocol2 is python2 compatible
        #print( 'streaming bytes', len(b) )
        n = len( b ); d = STREAM_BUFFER_SIZE - n -4
        if n > STREAM_BUFFER_SIZE:
            print( 'ERROR: STREAM OVERFLOW:', n )
            return
        padding = b'#' * d
        if n < 10: header = '000%s' %n
        elif n < 100: header = '00%s' %n
        elif n < 1000: header = '0%s' %n
        else: header = '%s' %n
        header = bytes( header, 'utf-8' )
        assert len(header) == 4
        w = header + b + padding
        assert len(w) == STREAM_BUFFER_SIZE
        self.buffer.insert(0, w )
        return w

    def multires_lod( self ):
        '''
        Ogre builtin LOD sucks for character animation
        '''
        ob = bpy.context.active_object
        cam = bpy.context.scene.camera

        if ob and cam and ob.type=='MESH' and ob.use_multires_lod:
            delta = bpy.context.active_object.matrix_world.to_translation() - cam.matrix_world.to_translation()
            dist = delta.length
            #print( 'Distance', dist )
            if ob.modifiers and ob.modifiers[0].type == 'MULTIRES' and ob.modifiers[0].total_levels > 1:
                mod = ob.modifiers[0]
                step = ob.multires_lod_range / mod.total_levels
                level = mod.total_levels - int( dist / step )
                if mod.levels != level: mod.levels = level
                return level

    def sync( self ):   # 153 bytes per object + n bytes for animation names and weights
        LOD = self.multires_lod()

        p = STREAM_PROTO
        i = 0; msg = []
        for ob in bpy.context.selected_objects:
            if ob.type not in ('MESH','LAMP','SPEAKER'): continue
            loc, rot, scale = ob.matrix_world.decompose()
            loc = swap(loc).to_tuple()
            x,y,z = swap( rot.to_euler() )
            rot = (x,y,z)
            x,y,z = swap( scale )
            scale = ( abs(x), abs(y), abs(z) )
            d = { p['ID']:uid(ob), p['POSITION']:loc, p['ROTATION']:rot, p['SCALE']:scale, p['TYPE']:p[ob.type] }
            msg.append( d )

            if ob.name == bpy.context.active_object.name and LOD is not None:
                d[ p['LOD'] ] = LOD

            if ob.type == 'MESH':
                arm = ob.find_armature()
                if arm and arm.animation_data and arm.animation_data.nla_tracks:
                    anim = None
                    d[ p['ANIMATIONS'] ] = state = {}    # animation-name : weight
                    for nla in arm.animation_data.nla_tracks:
                        for strip in nla.strips:
                            if strip.active: state[ strip.name ] = strip.influence
                else: pass      # armature without proper NLA setup
            elif ob.type == 'LAMP':
                d[ p['ENERGY'] ] = ob.data.energy
                d[ p['DISTANCE'] ] = ob.data.distance
            elif ob.type == 'SPEAKER':
                d[ p['VOLUME'] ] = ob.data.volume
                d[ p['MUTE'] ] = ob.data.muted

            if i >= 10: break    # max is 13 objects to stay under 2048 bytes
        return msg

    def __init__(self):
        import socket
        self.buffer = []    # cmd buffer
        self.socket = sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # UDP
        host='localhost'; port = 9420
        sock.connect((host, port))
        print('SERVER: socket connected', sock)
        self._handle = None
        self.setup_callback( bpy.context )
        import threading
        self.ready = threading._allocate_lock()
        self.ID = threading._start_new_thread(
            self.loop, (None,)
        )
        print( 'SERVER: thread started')

    def loop(self, none):
        self.active = True
        prev = time.time()
        while self.active:
            if not self.ready.locked(): time.sleep(0.001)    # not threadsafe
            else:    # threadsafe start
                now = time.time()
                if now - prev > 0.066:            # don't flood Tundra
                    actob = None
                    try: actob = bpy.context.active_object
                    except: pass
                    if not actob: continue
                    prev = now
                    sel = bpy.context.active_object
                    msg = self.sync()
                    self.ready.release()          # thread release
                    self.stream( msg )            # releases GIL?
                    if self.buffer:
                        bin = self.buffer.pop()
                        try:
                            self.socket.sendall( bin )
                        except:
                            print('SERVER: send data error')
                            time.sleep(0.5)
                            pass
                    else: print( 'SERVER: empty buffer' )
                else:
                    self.ready.release()
        print('SERVER: thread exit')

    def threadsafe( self, reg ):
        if not TundraSingleton: return
        if not self.ready.locked():
            self.ready.acquire()
            time.sleep(0.0001)
            while self.ready.locked():    # must block to be safe
                time.sleep(0.0001)            # wait for unlock
        else: pass #time.sleep(0.033) dont block

    _handle = None
    def setup_callback( self, context ):        # TODO replace with a proper frame update callback
        print('SERVER: setup frame update callback')
        if self._handle: return self._handle
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for reg in area.regions:
                    if reg.type == 'WINDOW':
                        # PRE_VIEW, POST_VIEW, POST_PIXEL
                        self._handle = reg.callback_add(self.threadsafe, (reg,), 'PRE_VIEW' )
                        self._area = area
                        self._region = reg
                        break
        if not self._handle:
            print('SERVER: FAILED to setup frame update callback')

def _create_stream_proto():
    proto = {}
    tags = 'ID NAME POSITION ROTATION SCALE DATA SELECTED TYPE MESH LAMP CAMERA SPEAKER ANIMATIONS DISTANCE ENERGY VOLUME MUTE LOD'.split()
    for i,tag in enumerate( tags ):
        proto[ tag ] = chr(i) # up to 256
    return proto

STREAM_PROTO = _create_stream_proto()
STREAM_BUFFER_SIZE = 2048

TUNDRA_SCRIPT = '''
# this file was generated by blender2ogre #
import tundra, socket, select, pickle
STREAM_BUFFER_SIZE = 2048
globals().update( %s )
E = {}    # this is just for debugging from the pyconsole

def get_entity(ID):
    scn = tundra.Scene().MainCameraScene()
    return scn.GetEntityRaw( ID )

class Client(object):
    def __init__(self):
        self.socket = sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        host='localhost'; port = 9420
        sock.bind((host, port))
        self._animated = {}    # entity ID : { anim-name : weight }

    def update(self, delay):
        global E
        sock = self.socket
        poll = select.select( [ sock ], [], [], 0.01 )
        if not poll[0]: return True
        data = sock.recv( STREAM_BUFFER_SIZE )
        assert len(data) == STREAM_BUFFER_SIZE
        if not data:
            print( 'blender crashed?' )
            return
        header = data[ : 4]
        s = data[ 4 : int(header)+4 ]
        objects = pickle.loads( s )
        scn = tundra.Scene().MainCameraScene()    # replaces GetDefaultScene()
        for ob in objects:
            e = scn.GetEntityRaw( ob[ID] )
            if not e: continue
            x,y,z = ob[POSITION]
            e.placeable.SetPosition( x,y,z )
            x,y,z = ob[SCALE]
            e.placeable.SetScale( x,y,z )
            #e.placeable.SetOrientation( ob[ROTATION] )

            if ob[TYPE] == LAMP:
                e.light.range = ob[ DISTANCE ]
                e.light.brightness = ob[ ENERGY ]
                #e.light.diffColor = !! not wrapped !!
                #e.light.specColor = !! not wrapped !!
            elif ob[TYPE] == SPEAKER:
                e.sound.soundGain = ob[VOLUME]
                #e.sound.soundInnerRadius =
                #e.sound.soundOuterRadius =
                if ob[MUTE]: e.sound.StopSound()
                else: e.sound.PlaySound()   # tundra API needs sound.IsPlaying()

            if ANIMATIONS in ob:
                self.update_animation( e, ob )

            if LOD in ob:
                #print( 'LOD', ob[LOD] )
                index = e.id + ob[LOD] + 1
                for i in range(1,9):
                    elod = get_entity( e.id + i )
                    if elod:
                        if elod.id == index and not elod.placeable.visible:
                            elod.placeable.visible = True
                        elif elod.id != index and elod.placeable.visible:
                            elod.placeable.visible = False

            if ob[ID] not in E: E[ ob[ID] ] = e

    def update_animation( self, e, ob ):
        if ob[ID] not in self._animated:
            self._animated[ ob[ID] ] = {}
        state = self._animated[ ob[ID] ]
        ac = e.animationcontroller
        for aname in ob[ ANIMATIONS ]:
            if aname not in state:      # save weight of new animation
                state[ aname ] = ob[ANIMATIONS][aname]  # weight
        for aname in state:
            if aname not in ob[ANIMATIONS] and ac.IsAnimationActive( aname ):
                ac.StopAnim( aname, '0.0' )
            elif aname in ob[ANIMATIONS]:
                weight = ob[ANIMATIONS][aname]
                if ac.HasAnimationFinished( aname ):
                    ac.PlayLoopedAnim( aname, '1.0', 'false' )      # PlayAnim(...) TODO single playback
                    ok = ac.SetAnimationWeight( aname, weight )
                    state[ aname ] = weight

                if weight != state[ aname ]:
                    ok = ac.SetAnimationWeight( aname, weight )
                    state[ aname ] = weight

client = Client()
tundra.Frame().connect( 'Updated(float)', client.update )
print('blender2ogre plugin ok')
''' %STREAM_PROTO

class TundraPipe(object):
    CONFIG_PATH = '/tmp/rex/plugins.xml'
    TUNDRA_SCRIPT_PATH = '/tmp/rex/b2ogre_plugin.py'
    CONFIG_XML = '''<?xml version="1.0"?>
<Tundra>
  <!-- plugins.xml is hardcoded to be the default configuration file to load if another file is not specified on the command line with the "config filename.xml" parameter. -->
  <plugin path="OgreRenderingModule" />
  <plugin path="EnvironmentModule" />           <!-- EnvironmentModule depends on OgreRenderingModule -->
  <plugin path="PhysicsModule" />               <!-- PhysicsModule depends on OgreRenderingModule and EnvironmentModule -->
  <plugin path="TundraProtocolModule" />        <!-- TundraProtocolModule depends on OgreRenderingModule -->
  <plugin path="JavascriptModule" />            <!-- JavascriptModule depends on TundraProtocolModule -->
  <plugin path="AssetModule" />                 <!-- AssetModule depends on TundraProtocolModule -->
  <plugin path="AvatarModule" />                <!-- AvatarModule depends on AssetModule and OgreRenderingModule -->
  <plugin path="ECEditorModule" />              <!-- ECEditorModule depends on OgreRenderingModule, TundraProtocolModule, OgreRenderingModule and AssetModule -->
  <plugin path="SkyXHydrax" />                  <!-- SkyXHydrax depends on OgreRenderingModule -->
  <plugin path="OgreAssetEditorModule" />       <!-- OgreAssetEditorModule depends on OgreRenderingModule -->
  <plugin path="DebugStatsModule" />            <!-- DebugStatsModule depends on OgreRenderingModule, EnvironmentModule and AssetModule -->
  <plugin path="SceneWidgetComponents" />       <!-- SceneWidgetComponents depends on OgreRenderingModule and TundraProtocolModule -->
  <plugin path="PythonScriptModule" />

  <!-- TODO: Currently the above <plugin> items are loaded in the order they are specified, but below, the jsplugin items are loaded in an undefined order. Use the order specified here as the load order. -->
  <!-- NOTE: The startup .js scripts are specified only by base name of the file. Don's specify a path here. Place the startup .js scripts to /bin/jsmodules/startup/. -->
  <!-- Important: The file names specified here are case sensitive even on Windows! -->
  <jsplugin path="cameraapplication.js" />
  <jsplugin path="FirstPersonMouseLook.js" />
  <jsplugin path="MenuBar.js" />

  <!-- Python plugins -->
  <!-- <pyplugin path="lib/apitests.py" /> -->          <!-- Runs framework api tests -->
  <pyplugin path="%s" />         <!-- shows qt py console. could enable by default when add to menu etc. for controls, now just shows directly when is enabled here -->

  <option name="--accept_unknown_http_sources" />
  <option name="--accept_unknown_local_sources" />
  <option name="--fpslimit" value="60" />
  <!--  AssetAPI's file system watcher currently disabled because LocalAssetProvider implements
        the same functionality for LocalAssetStorages and HTTPAssetProviders do not yet support live-update. -->
  <option name="--nofilewatcher" />

</Tundra>''' %TUNDRA_SCRIPT_PATH

    def __init__(self, context, debug=False):
        self._physics_debug = True
        self._objects = []
        self.proc = None
        exe = None
        if 'Tundra.exe' in os.listdir( CONFIG['TUNDRA_ROOT'] ):
            exe = os.path.join( CONFIG['TUNDRA_ROOT'], 'Tundra.exe' )
        elif 'Tundra' in os.listdir( CONFIG['TUNDRA_ROOT'] ):
            exe = os.path.join( CONFIG['TUNDRA_ROOT'], 'Tundra' )

        cmd = []
        if not exe:
            print('ERROR: failed to find Tundra executable')
            assert 0
        elif sys.platform.startswith('win'):
            cmd.append(exe)
        else:
            if exe.endswith('.exe'): cmd.append('wine')     # assume user has Wine
            cmd.append( exe )
        if debug:
            cmd.append('--loglevel')
            cmd.append('debug')

        if CONFIG['TUNDRA_STREAMING']:
            cmd.append( '--config' )
            cmd.append( self.CONFIG_PATH )
            with open( self.CONFIG_PATH, 'wb' ) as fp: fp.write( bytes(self.CONFIG_XML,'utf-8') )
            with open( self.TUNDRA_SCRIPT_PATH, 'wb' ) as fp: fp.write( bytes(TUNDRA_SCRIPT,'utf-8') )
            self.server = Server()

        #cmd += ['--file', '/tmp/rex/preview.txml']     # tundra2.1.2 bug loading from --file ignores entity ID's
        cmd.append( '--storage' )
        if sys.platform.startswith('win'): cmd.append( 'C:\\tmp\\rex' )
        else: cmd.append( '/tmp/rex' )
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, cwd=CONFIG['TUNDRA_ROOT'])

        self.physics = True
        if self.proc:
            time.sleep(0.1)
            self.load( context, '/tmp/rex/preview.txml' )
            self.stop()

    def deselect_previously_updated(self, context):
        r = []
        for ob in context.selected_objects:
            if ob.name in self._objects: ob.select = False; r.append( ob )
        return r

    def load( self, context, url, clear=False ):
        self._objects += [ob.name for ob in context.selected_objects]
        if clear:
            self.proc.stdin.write( b'loadscene(/tmp/rex/preview.txml,true,true)\n')
        else:
            self.proc.stdin.write( b'loadscene(/tmp/rex/preview.txml,false,true)\n')
        try:
            self.proc.stdin.flush()
        except:
            global TundraSingleton
            TundraSingleton = None

    def start( self ):
        self.physics = True
        self.proc.stdin.write( b'startphysics\n' )
        try: self.proc.stdin.flush()
        except:
            global TundraSingleton
            TundraSingleton = None

    def stop( self ):
        self.physics = False
        self.proc.stdin.write( b'stopphysics\n' )
        try: self.proc.stdin.flush()
        except:
            global TundraSingleton
            TundraSingleton = None

    def toggle_physics_debug( self ):
        self._physics_debug = not self._physics_debug
        self.proc.stdin.write( b'physicsdebug\n' )
        try: self.proc.stdin.flush()
        except:
            global TundraSingleton
            TundraSingleton = None

    def exit(self):
        self.proc.stdin.write( b'exit\n' )
        self.proc.stdin.flush()
        global TundraSingleton
        TundraSingleton = None

