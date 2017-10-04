
def on_change_parent_material(mat,context):
    print(mat,context)
    print('callback', mat.ogre_parent_material)

def get_subnodes(mat, type='TEXTURE'):
    d = {}
    for node in mat.nodes:
        if node.type==type: d[node.name] = node
    keys = list(d.keys())
    keys.sort()
    r = []
    for key in keys: r.append( d[key] )
    return r


def get_texture_subnodes( parent, submaterial=None ):
    if not submaterial: submaterial = parent.active_node_material
    d = {}
    for link in parent.node_tree.links:
        if link.from_node and link.from_node.type=='TEXTURE':
            if link.to_node and link.to_node.type == 'MATERIAL_EXT':
                if link.to_node.material:
                    if link.to_node.material.name == submaterial.name:
                        node = link.from_node
                        d[node.name] = node
    keys = list(d.keys())           # this breaks if the user renames the node - TODO improve me
    keys.sort()
    r = []
    for key in keys: r.append( d[key] )
    return r

def get_connected_input_nodes( material, node ):
    r = []
    for link in material.node_tree.links:
        if link.to_node and link.to_node.name == node.name:
            r.append( link.from_node )
        return r

def get_or_create_material_passes( mat, n=8 ):
    if not mat.node_tree:
        print('CREATING MATERIAL PASSES', n)
        create_material_passes( mat, n )

    d = {}      # funky, blender259 had this in order, now blender260 has random order
    for node in mat.node_tree.nodes:
        if node.type == 'MATERIAL_EXT' and node.name.startswith('GEN.'):
            d[node.name] = node
    keys = list(d.keys())
    keys.sort()
    r = []
    for key in keys: r.append( d[key] )
    return r

def get_or_create_texture_nodes( mat, n=6 ):    # currently not used
    assert mat.node_tree    # must call create_material_passes first
    m = []
    for node in mat.node_tree.nodes:
        if node.type == 'MATERIAL_EXT' and node.name.startswith('GEN.'):
            m.append( node )
    if not m:
        m = get_or_create_material_passes(mat)
    print(m)
    r = []
    for link in mat.node_tree.links:
        print(link, link.to_node, link.from_node)
        if link.to_node and link.to_node.name.startswith('GEN.') and link.from_node.type=='TEXTURE':
            r.append( link.from_node )
    if not r:
        print('--missing texture nodes--')
        r = create_texture_nodes( mat, n )
    return r

def create_material_passes( mat, n=8, textures=True ):
    mat.use_nodes = True
    tree = mat.node_tree    # valid pointer now

    nodes = get_subnodes( tree, 'MATERIAL' )  # assign base material
    if nodes and not nodes[0].material:
        nodes[0].material = mat

    r = []
    x = 680
    for i in range( n ):
        node = tree.nodes.new( type='ShaderNodeExtendedMaterial' )
        node.name = 'GEN.%s' %i
        node.location.x = x; node.location.y = 640
        r.append( node )
        x += 220
    #mat.use_nodes = False  # TODO set user material to default output
    if textures:
        texnodes = create_texture_nodes( mat )
        print( texnodes )
    return r

def create_texture_nodes( mat, n=6, geoms=True ):
    assert mat.node_tree    # must call create_material_passes first
    mats = get_or_create_material_passes( mat )
    r = {}; x = 400
    for i,m in enumerate(mats):
        r['material'] = m; r['textures'] = []; r['geoms'] = []
        inputs = []     # other inputs mess up material preview #
        for tag in ['Mirror', 'Ambient', 'Emit', 'SpecTra', 'Reflectivity', 'Translucency']:
            inputs.append( m.inputs[ tag ] )
        for j in range(n):
            tex = mat.node_tree.nodes.new( type='ShaderNodeTexture' )
            tex.name = 'TEX.%s.%s' %(j, m.name)
            tex.location.x = x - (j*16)
            tex.location.y = -(j*230)
            input = inputs[j]; output = tex.outputs['Color']
            link = mat.node_tree.links.new( input, output )
            r['textures'].append( tex )
            if geoms:
                geo = mat.node_tree.nodes.new( type='ShaderNodeGeometry' )
                link = mat.node_tree.links.new( tex.inputs['Vector'], geo.outputs['UV'] )
                geo.location.x = x - (j*16) - 250
                geo.location.y = -(j*250) - 1500
                r['geoms'].append( geo )
        x += 220
    return r
