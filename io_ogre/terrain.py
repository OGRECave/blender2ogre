import bpy

def _get_proxy_decimate_mod( ob ):
    proxy = None
    for child in ob.children:
        if child.subcollision and child.name.startswith('DECIMATED'):
            for mod in child.modifiers:
                if mod.type == 'DECIMATE':
                    return mod

def bake_terrain( ob, normalize=True ):
    assert ob.collision_mode == 'TERRAIN'
    terrain = None
    for child in ob.children:
        if child.subcollision and child.name.startswith('TERRAIN'):
            terrain = child
            break
    assert terrain
    data = terrain.to_mesh(bpy.context.scene, True, "PREVIEW")
    raw = [ v.co.z for v in data.vertices ]
    Zmin = min( raw )
    Zmax = max( raw )
    depth = Zmax-Zmin
    m = 1.0 / depth

    rows = []
    i = 0
    for x in range( ob.collision_terrain_x_steps ):
        row = []
        for y in range( ob.collision_terrain_y_steps ):
            v = data.vertices[ i ]
            if normalize:
                z = (v.co.z - Zmin) * m
            else:
                z = v.co.z
            row.append( z )
            i += 1
        if x%2:
            row.reverse() # blender grid prim zig-zags
        rows.append( row )
    return {'data':rows, 'min':Zmin, 'max':Zmax, 'depth':depth}

def save_terrain_as_NTF( path, ob ): # Tundra format - hardcoded 16x16 patch format
    info = bake_terrain( ob )
    url = os.path.join( path, '%s.ntf' % clean_object_name(ob.data.name) )
    f = open(url, "wb")
    # Header
    buf = array.array("I")
    xs = ob.collision_terrain_x_steps
    ys = ob.collision_terrain_y_steps
    xpatches = int(xs/16)
    ypatches = int(ys/16)
    header = [ xpatches, ypatches ]
    buf.fromlist( header )
    buf.tofile(f)
    # Body
    rows = info['data']
    for x in range( xpatches ):
        for y in range( ypatches ):
            patch = []
            for i in range(16):
                for j in range(16):
                    v = rows[ (x*16)+i ][ (y*16)+j ]
                    patch.append( v )
            buf = array.array("f")
            buf.fromlist( patch )
            buf.tofile(f)
    f.close()
    path,name = os.path.split(url)
    R = {
        'url':url, 'min':info['min'], 'max':info['max'], 'path':path, 'name':name,
        'xpatches': xpatches, 'ypatches': ypatches,
        'depth':info['depth'],
    }
    return R

class OgreCollisionOp(bpy.types.Operator):
    '''Ogre Collision'''
    bl_idname = "ogre.set_collision"
    bl_label = "modify collision"
    bl_options = {'REGISTER'}
    MODE = StringProperty(name="toggle mode", maxlen=32, default="disable")

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type == 'MESH':
            return True

    def get_subcollisions( self, ob, create=True ):
        r = get_subcollisions( ob )
        if not r and create:
            method = getattr(self, 'create_%s'%ob.collision_mode)
            p = method(ob)
            p.name = '%s.%s' %(ob.collision_mode, ob.name)
            p.subcollision = True
            r.append( p )
        return r

    def create_DECIMATED(self, ob):
        child = ob.copy()
        bpy.context.scene.collection.objects.link( child )
        child.matrix_local = mathutils.Matrix()
        child.parent = ob
        child.hide_select = True
        child.draw_type = 'WIRE'
        #child.select = False
        child.lock_location = [True]*3
        child.lock_rotation = [True]*3
        child.lock_scale = [True]*3
        decmod = child.modifiers.new('proxy', type='DECIMATE')
        decmod.ratio = 0.5
        return child

    def create_TERRAIN(self, ob):
        x = ob.collision_terrain_x_steps
        y = ob.collision_terrain_y_steps
        #################################
        #pos = ob.matrix_world.to_translation()
        bpy.ops.mesh.primitive_grid_add(
            x_subdivisions=x,
            y_subdivisions=y,
            size=1.0 )      #, location=pos )
        grid = bpy.context.active_object
        assert grid.name.startswith('Grid')
        grid.collision_terrain_x_steps = x
        grid.collision_terrain_y_steps = y
        #############################
        x,y,z = ob.dimensions
        sx,sy,sz = ob.scale
        x *= 1.0/sx
        y *= 1.0/sy
        z *= 1.0/sz
        grid.scale.x = x/2
        grid.scale.y = y/2
        grid.location.z -= z/2
        grid.data.show_all_edges = True
        grid.draw_type = 'WIRE'
        grid.hide_select = True
        #grid.select = False
        grid.lock_location = [True]*3
        grid.lock_rotation = [True]*3
        grid.lock_scale = [True]*3
        grid.parent = ob
        bpy.context.scene.objects.active = ob
        mod = grid.modifiers.new(name='temp', type='SHRINKWRAP')
        mod.wrap_method = 'PROJECT'
        mod.use_project_z = True
        mod.target = ob
        mod.cull_face = 'FRONT'
        return grid

    def invoke(self, context, event):
        ob = context.active_object
        game = ob.game
        subtype = None

        if ':' in self.MODE:
            mode, subtype = self.MODE.split(':')
            ##BLENDERBUG##ob.game.collision_bounds_type = subtype   # BUG this can not come before
            if subtype in 'BOX SPHERE CYLINDER CONE CAPSULE'.split():
                ob.draw_bounds_type = subtype
            else:
                ob.draw_bounds_type = 'POLYHEDRON'
            ob.game.collision_bounds_type = subtype  # BLENDERBUG - this must come after draw_bounds_type assignment
        else:
            mode = self.MODE
        ob.collision_mode = mode

        if ob.data.show_all_edges:
            ob.data.show_all_edges = False
        if ob.show_texture_space:
            ob.show_texture_space = False
        if ob.show_bounds:
            ob.show_bounds = False
        if ob.show_wire:
            ob.show_wire = False
        for child in ob.children:
            if child.subcollision and not child.hide_viewport:
                child.hide_viewport = True

        if mode == 'NONE':
            game.use_ghost = True
            game.use_collision_bounds = False
        elif mode == 'PRIMITIVE':
            game.use_ghost = False
            game.use_collision_bounds = True
            ob.show_bounds = True
        elif mode == 'MESH':
            game.use_ghost = False
            game.use_collision_bounds = True
            ob.show_wire = True
            if game.collision_bounds_type == 'CONVEX_HULL':
                ob.show_texture_space = True
            else:
                ob.data.show_all_edges = True
        elif mode == 'DECIMATED':
            game.use_ghost = True
            game.use_collision_bounds = False
            game.use_collision_compound = True
            proxy = self.get_subcollisions(ob)[0]
            if proxy.hide_viewport: proxy.hide_viewport = False
            ob.game.use_collision_compound = True  # proxy
            mod = _get_proxy_decimate_mod( ob )
            mod.show_viewport = True
            if not proxy.select:    # ugly (but works)
                proxy.hide_select = False
                proxy.select = True
                proxy.hide_select = True
            if game.collision_bounds_type == 'CONVEX_HULL':
                ob.show_texture_space = True
        elif mode == 'TERRAIN':
            game.use_ghost = True
            game.use_collision_bounds = False
            game.use_collision_compound = True
            proxy = self.get_subcollisions(ob)[0]
            if proxy.hide_viewport:
                proxy.hide_viewport = False
        elif mode == 'COMPOUND':
            game.use_ghost = True
            game.use_collision_bounds = False
            game.use_collision_compound = True
        else:
            assert 0 # unknown mode

        return {'FINISHED'}

