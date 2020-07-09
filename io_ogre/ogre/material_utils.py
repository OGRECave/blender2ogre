from mathutils import Color, Vector

def rgba_to_rgb(rgba):
    return Color((rgba[0], rgba[1], rgba[2]))

class ShaderType(object):
    """
    Type of shader node, provides uniform access to input sockets via keys.
    """
    def __init__(self, name, normal=False, roughness=False, base="Color", volume=False, exts=None):
        self.name = "ShaderNode" + name
        self.__sockets = {}
        if base:
            self.__sockets["base"] = base
        if normal:
            self.__sockets["normal"] = "Normal"
        if roughness:
            self.__sockets["roughness"] = "Roughness"
        if volume:
            self.__sockets["density"] = "Density"
        if exts:
            for key,val in exts.items():
                self.__sockets[key] = val
    
    def _get_socket(self, key):
        return self.__sockets.get(key)
    
    def _set_socket(self, key, value):
        self.__sockets[key] = value
    
    def __str__(self):
        return self.__class__.__name__ + "[" + self.name + "]"

# All managed shader types.        
SHADER_TYPES = {}

for shader_type in [
    # Color/Roughness/Normal
    ShaderType("BsdfDiffuse", True, True),
    
    # Color/Strength
    ShaderType("Emission"),
    
    # Color/Roughness/IOR/Normal
    ShaderType("BsdfGlass", True, True, exts={"ior": "IOR"}),
    
    # Color/Roughness/Normal
    ShaderType("BsdfGlossy", True, True),
    
    # Color/Roughness/IOR/Normal
    ShaderType("BsdfRefraction", True, True, exts={"ior": "IOR"}),
    
    # Base Color/Specular/Roughness/Emissive Color
    # Transparency/Normal
    # Clear Coat/Clear Coat Roughness/Clear Coat Normal
    # Ambient Occlusion
    ShaderType("EeveeSpecular", True, True, base="Base Color", exts={
        "specular": "Specular",
        "emission": "Emissive Color"
    }),
    
    # Color/Scale/Radius/Texture Blur/Normal
    # > BSSRDF
    ShaderType("SubsurfaceScattering", True),
    
    # Color/Normal
    ShaderType("BsdfTranslucent", True),
    
    # Color
    ShaderType("BsdfTransparent"),
    
    # Color/Density
    ShaderType("VolumeAbsorption", volume=True),
    
    # Color/Density/Anisotropy
    ShaderType("VolumeScatter", volume=True, exts={"anisotropy": "Anisotropy"}),
    
    # Base Color
    # Subsurface/Subsurface Radius/Subsurface Color
    # Metallic/Specular/Specular Tint
    # Roughness/Anisotropic/Anisotropic Rotation
    # Sheen/Sheen Tint
    # Clearcoat/Clearcoat Roughness
    # IOR
    # Transmission/Transmission Roughness
    # Emission (color)/Alpha
    # Normal/Clearcoat Normal/Tangent
    ShaderType("BsdfPrincipled", True, True, base="Base Color", exts={
        "specular": "Specular",
        "metallic": "Metallic",
        "emission": "Emission",
        "alpha": "Alpha",
        "ior": "IOR"
    }),
    
    # Color
    # Density/Density Attribute (str)
    # Anisotropy/Absorption Color
    # Emission Strength/Emission Color
    # Blackbody Intensity/Blackbody Tint
    # Temperature/Temperature Attribute (str)
    ShaderType("VolumePrincipled", volume=True, exts={
        "anisotropy": "Anisotropy",
        "emission": "Emission Color"
    })

]:  SHADER_TYPES[shader_type.name] = shader_type

# Material shader texture keys
TEXTURE_KEYS = [
    "base",
    "specular",
    "roughness",
    "normal",   # Texture connected to the normal input socket via a Normal Map node
    "metallic",
    "emission",
    "alpha",
    "ior",
    "anisotropy",
    "density"
]

class MaterialShader():
    """
    Most important data of a material.
    Finds the main shader (the one connected to the 'Surface' socket of
    the material output), and finds nodes and textures according to its type.
    """
    
    def __init__(self, material):
        self.material = material
        self.use_nodes = self.material.use_nodes
        self.update()
    
    def update(self):
        self._textures = {}
        self.normal_node = None
        
        if not self.use_nodes:
            return

        main_node = None
        shader_type = None
        for n in self.material.node_tree.nodes:
            if n.bl_idname == 'ShaderNodeOutputMaterial' and n.inputs[0].is_linked:
                main_node = n.inputs[0].links[0].from_node
                if main_node:
                    shader_type = SHADER_TYPES.get(main_node.bl_idname)
                    if shader_type:
                        break
            main_node = shader_type = None
        self.main_node = main_node
        self.type = shader_type

        socket = self._get_socket("normal")
        if socket and socket.is_linked:
            normal_node = socket.links[0].from_node
            if normal_node.bl_idname == 'ShaderNodeNormalMap':
                self.normal_node = normal_node
    
    ##################################################
    # Access
            
    def _get_socket(self, key):
        if not self.use_nodes or self.main_node is None:
            return None
        
        socket = self.type._get_socket(key)
        return None if socket is None else self.main_node.inputs[socket]
    
    def _get_socket_value(self, key):
        socket = self._get_socket(key)
        return None if socket is None else socket.default_value
    
    def get_texture(self, key):
        """
        Gets the texture associated to that key.
        key: Enum ["base", "specular", "roughness", "alpha", "normal", "metallic", "emission", "ior", "anisotropy", "density"]
        """
        texture = self._textures.get(key)
        if texture:
            return texture
        socket = self._get_socket(key)
        if socket:
            texture = MaterialTexture(self, self.main_node, socket)
            self._textures[key] = texture
        return texture
    
    def get_textures(self, keys=TEXTURE_KEYS):
        """
        Returns a dictionary of all available textures by keys.
        keys: texture keys to select, all by default (including normal).
            Enum ["base", "specular", "roughness", "alpha", "normal", "metallic", "emission", "ior", "anisotropy", "density"]
        """
        textures = {}
        for key in keys:
            if key == "normal":
                tex = self.normal_texture
            else:
                tex = self.get_texture(key)
            if tex:
                textures[key] = tex
        return textures
    
    ##################################################
    # Properties

    def get_normal_texture(self):
        if self.normal_node:
            socket = self._get_socket("normal")
            if socket:
                return MaterialTexture(
                    self, self.normal_node,
                    self.normal_node.inputs["Color"]
                )
        return None
    
    normal_texture = property(get_normal_texture)
    
    def get_base_color(self):
        value = self._get_socket_value("base")
        return rgba_to_rgb(value) if value else self.material.diffuse_color
    
    base_color = property(get_base_color)

    def get_base_texture(self):
        return self.get_texture("base")
    
    base_texture = property(get_base_texture)

class MaterialTexture():
    """
    Texture of a MaterialShader.
    Contains image node, image, transformations (from mapping node).
    """
    def __init__(self, material_shader: MaterialShader, dst_node, dst_socket):
        self.material_shader = material_shader
        self.dst_node = dst_node
        self.dst_socket = dst_socket
        
        self.use_alpha = False
        self.image_node = None
        self.image = None
        self.mapping = None
        self.coordinates = 'UV'

        if dst_socket.is_linked:
            from_node = dst_socket.links[0].from_node
            if from_node.bl_idname == 'ShaderNodeTexImage':
                self.image_node = from_node
                self.image = from_node.image
                self.use_alpha = dst_socket.links[0].from_socket.name == 'Alpha'

        if self.image_node:
            socket = self.image_node.inputs["Vector"]
            if socket.is_linked:
                from_node = socket.links[0].from_node
                if from_node.bl_idname == 'ShaderNodeMapping':
                    self.mapping = from_node
                else:
                    self.coordinates = socket.links[0].from_socket.name
        
        if self.mapping:
            socket = self.mapping.inputs["Vector"]
            if socket.is_linked:
                self.coordinates = socket.links[0].from_socket.name
                    
    ##################################################
    # Properties

    def get_projection(self):
        return self.image_node.projection if self.image_node is not None else 'FLAT'
    projection = property(get_projection)


    def get_extension(self):
        return self.image_node.extension if self.image_node is not None else 'REPEAT'
    extension = property(get_extension)


    def get_translation(self):
        if self.mapping is None:
            return Vector((0.0, 0.0, 0.0))
        return self.mapping.inputs['Location'].default_value
    translation = property(get_translation)


    def get_rotation(self):
        if self.mapping is None:
            return Vector((0.0, 0.0, 0.0))
        return self.mapping.inputs['Rotation'].default_value
    rotation = property(get_rotation)


    def get_scale(self):
        if self.mapping is None:
            return Vector((1.0, 1.0, 1.0))
        return self.mapping.inputs['Scale'].default_value

    scale = property(get_scale)
