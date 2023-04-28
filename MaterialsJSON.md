# OGRE Next JSON Materials
Support implemented based on the Ogre Next documentation.
https://ogrecave.github.io/ogre-next/api/latest/hlmspbsdatablockref.html

Only the metallic workflow is supported at this time.

## Metallic Workflow
Metalness texture fetching expects a single image with the metal
texture in the Blue channel and the roughness texture in the Green
channel. The channels are expected to have been split via a 'Separate RGB' node
before passing to the Principled BSDF. This is in line with the glTF standard
setup.

## Specular Workflow
Unsupported.

## Unsupported features
### fresnel
This is used in the Specular workflows supported by Ogre. Right now we
only support the metallic workflow.

### blendblock
Blendblocks are used for advanced effects and don't fit into the
standard Blender workflow. One commmon use would be to have better
alpha blending on complex textures. Limit of 32 blend blocks at
runtime also means we shouldn't "just generate them anyway."
doc: https://ogrecave.github.io/ogre-next/api/latest/hlmsblendblockref.html

### macroblock
Macroblocks are used for advanced effects and don't fit into the
standard Blender workflow. One common use would be to render a skybox
behind everything else in a scene. Limit of 32 macroblocks at runtime
also means we shouldn't "just generate them anyway."
doc: https://ogrecave.github.io/ogre-next/api/latest/hlmsmacroblockref.html

### sampler
Samplerblocks are used for advanced texture handling like filtering,
addressing, LOD, etc. These settings have signifigant visual and
performance effects. Limit of 32 samplerblocks at runtime also means
we shouldn't "just generate them anyway."

### recieve_shadows
No receive shadow setting in Blender 2.8+ but was available in 2.79.
We leave this unset which defaults to true. Maybe add support in
the 2.7 branch?
See: https://docs.blender.org/manual/en/2.79/render/blender_render/materials/properties/shadows.html#shadow-receiving-object-material

### shadow_const_bias
Leave shadow const bias undefined to default. It is usually used to
fix specific self-shadowing issues and is an advanced feature.

### brdf
Leave brdf undefined to default. This setting has huge visual and
performance impacts and is for specific use cases.
doc: https://ogrecave.github.io/ogre-next/api/latest/hlmspbsdatablockref.html#dbParamBRDF

### reflection
Leave reflection undefined to default. In most cases for reflections
users will want to use generated cubemaps in-engine.

### detail_diffuse[0-3]
Layered diffuse maps for advanced effects.

### detail_normal[0-3]
Layered normal maps for advanced effects.

### detail_weight
Texture acting as a mask for the detail maps.
