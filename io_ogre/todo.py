
# TODO TUNDRA def export_menu_func_realxtend(self, context):
#    op = self.layout.operator(INFO_OT_createRealxtendExport.bl_idname, text="realXtend Tundra (.txml and .mesh)")

## Blender world panel options for EC_SkyX creation
## todo: EC_SkyX has changes a bit lately, see that
## all these options are still correct and valid
## old todo (?): Move to tundra.py

#@UI
class OgreSkyPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "world"
    bl_label = "Ogre Sky Settings"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.prop( context.world, 'ogre_skyX' )
        if context.world.ogre_skyX:
            box.prop( context.world, 'ogre_skyX_time' )
            box.prop( context.world, 'ogre_skyX_wind' )
            box.prop( context.world, 'ogre_skyX_volumetric_clouds' )
            if context.world.ogre_skyX_volumetric_clouds:
                box.prop( context.world, 'ogre_skyX_cloud_density_x' )
                box.prop( context.world, 'ogre_skyX_cloud_density_y' )

#@UI
class PANEL_Object(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Object+"

    @classmethod
    def poll(cls, context):
        _USE_TUNDRA_ = False # TODO
        if _USE_TUNDRA_ and context.active_object:
            return True

    def draw(self, context):
        ob = context.active_object
        layout = self.layout
        box = layout.box()
        box.prop( ob, 'cast_shadows' )

        box.prop( ob, 'use_draw_distance' )
        if ob.use_draw_distance:
            box.prop( ob, 'draw_distance' )
        #if ob.find_armature():
        if ob.type == 'EMPTY':
            box.prop( ob, 'use_avatar' )
            box.prop( ob, 'avatar_reference' )

#@UI
class PANEL_Speaker(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_label = "Sound+"
    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type=='SPEAKER': return True
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.prop( context.active_object.data, 'play_on_load' )
        box.prop( context.active_object.data, 'loop' )
        box.prop( context.active_object.data, 'use_spatial' )

#@UI
class PANEL_MultiResLOD(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    bl_label = "Multi-Resolution LOD"
    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type=='MESH':
            ob = context.active_object
            if ob.modifiers and ob.modifiers[0].type=='MULTIRES':
                return True
    def draw(self, context):
        ob = context.active_object
        layout = self.layout
        box = layout.box()
        box.prop( ob, 'use_multires_lod' )
        if ob.use_multires_lod:
            box.prop( ob, 'multires_lod_range' )

''' todo: Update the nonsense C:\Tundra2 paths from defaul config and fix this doc.
    Additionally point to some doc how to build opengl only version on windows if that really is needed and
    remove the old Tundra 7z link. '''

@UI
class PANEL_node_editor_ui_extra( bpy.types.Panel ):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_label = "Ogre Material Advanced"
    bl_options = {'DEFAULT_CLOSED'}
    @classmethod
    def poll(self,context):
        if context.space_data.id: return True
    def draw(self, context):
        layout = self.layout
        topmat = context.space_data.id             # the top level node_tree
        mat = topmat.active_node_material        # the currently selected sub-material
        if mat:
            self.bl_label = mat.name + ' (advanced)'
            ogre_material_panel_extra( layout, mat )
        else:
            self.bl_label = topmat.name + ' (advanced)'
            ogre_material_panel_extra( layout, topmat )


@UI
class PANEL_node_editor_ui( bpy.types.Panel ):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_label = "Ogre Material"

    @classmethod
    def poll(self,context):
        if context.space_data.id:
            return True

    def draw(self, context):
        layout = self.layout
        topmat = context.space_data.id             # the top level node_tree
        mat = topmat.active_node_material        # the currently selected sub-material
        if not mat or topmat.name == mat.name:
            self.bl_label = topmat.name
            if not topmat.use_material_passes:
                layout.operator(
                    'ogre.force_setup_material_passes',
                    text="Ogre Material Layers",
                    icon='SCENE_DATA'
                )
            ogre_material_panel( layout, topmat, show_programs=False )
        elif mat:
            self.bl_label = mat.name
            ogre_material_panel( layout, mat, topmat, show_programs=False )
#@UI
class PANEL_Configure(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_label = "Ogre Configuration File"

    def draw(self, context):
        layout = self.layout
        op = layout.operator( 'ogre.save_config', text='update config file', icon='FILE' )
        for tag in _CONFIG_TAGS_:
            layout.prop( context.window_manager, tag )

#@UI
class PANEL_Textures(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "texture"
    bl_label = "Ogre Texture"

    @classmethod
    def poll(cls, context):
        if not hasattr(context, "texture_slot"):
            return False
        else: return True

    def draw(self, context):
        #if not hasattr(context, "texture_slot"):
        #    return False
        layout = self.layout
        #idblock = context_tex_datablock(context)
        slot = context.texture_slot
        if not slot or not slot.texture:
            return

        btype = slot.blend_type  # todo: fix this hack if/when slots support pyRNA
        ex = False; texop = None
        if btype in TextureUnit.colour_op:
            if btype=='MIX' and slot.use_map_alpha and not slot.use_stencil:
                if slot.diffuse_color_factor >= 1.0:
                    texop = 'alpha_blend'
                else:
                    texop = TextureUnit.colour_op_ex[ btype ]
                    ex = True
            elif btype=='MIX' and slot.use_map_alpha and slot.use_stencil:
                texop = 'blend_current_alpha'; ex=True
            elif btype=='MIX' and not slot.use_map_alpha and slot.use_stencil:
                texop = 'blend_texture_alpha'; ex=True
            else:
                texop = TextureUnit.colour_op[ btype ]
        elif btype in TextureUnit.colour_op_ex:
            texop = TextureUnit.colour_op_ex[ btype ]
            ex = True

        box = layout.box()
        row = box.row()
        if texop:
            if ex:
                row.prop(slot, "blend_type", text=texop, icon='NEW')
            else:
                row.prop(slot, "blend_type", text=texop)
        else:
            row.prop(slot, "blend_type", text='(invalid option)')

        if btype == 'MIX':
            row.prop(slot, "use_stencil", text="")
            row.prop(slot, "use_map_alpha", text="")
            if texop == 'blend_manual':
                row = box.row()
                row.label(text="Alpha:")
                row.prop(slot, "diffuse_color_factor", text="")

        if hasattr(slot.texture, 'image') and slot.texture.image:
            row = box.row()
            n = '(invalid option)'
            if slot.texture.extension in TextureUnit.tex_address_mode:
                n = TextureUnit.tex_address_mode[ slot.texture.extension ]
            row.prop(slot.texture, "extension", text=n)
            if slot.texture.extension == 'CLIP':
                row.prop(slot, "color", text="Border Color")

        row = box.row()
        if slot.texture_coords == 'UV':
            row.prop(slot, "texture_coords", text="", icon='GROUP_UVS')
            row.prop(slot, "uv_layer", text='Layer')
        elif slot.texture_coords == 'REFLECTION':
            row.prop(slot, "texture_coords", text="", icon='MOD_UVPROJECT')
            n = '(invalid option)'
            if slot.mapping in 'FLAT SPHERE'.split(): n = ''
            row.prop(slot, "mapping", text=n)
        else:
            row.prop(slot, "texture_coords", text="(invalid mapping option)")

        # Animation and offset options
        split = layout.row()
        box = split.box()
        box.prop(slot, "offset", text="XY=offset,  Z=rotation")
        box = split.box()
        box.prop(slot, "scale", text="XY=scale (Z ignored)")

        box = layout.box()
        row = box.row()
        row.label(text='scrolling animation')

        # Can't use if its enabled by default row.prop(slot, "use_map_density", text="")
        row.prop(slot, "use_map_scatter", text="")
        row = box.row()
        row.prop(slot, "density_factor", text="X")
        row.prop(slot, "emission_factor", text="Y")

        box = layout.box()
        row = box.row()
        row.label(text='rotation animation')
        row.prop(slot, "emission_color_factor", text="")
        row.prop(slot, "use_from_dupli", text="")

        ## Image magick
        if hasattr(slot.texture, 'image') and slot.texture.image:
            img = slot.texture.image
            box = layout.box()
            row = box.row()
            row.prop( img, 'use_convert_format' )
            if img.use_convert_format:
                row.prop( img, 'convert_format' )
                if img.convert_format == 'jpg':
                    box.prop( img, 'jpeg_quality' )

            row = box.row()
            row.prop( img, 'use_color_quantize', text='Reduce Colors' )
            if img.use_color_quantize:
                row.prop( img, 'use_color_quantize_dither', text='dither' )
                row.prop( img, 'color_quantize', text='colors' )

            row = box.row()
            row.prop( img, 'use_resize_half' )
            if not img.use_resize_half:
                row.prop( img, 'use_resize_absolute' )
                if img.use_resize_absolute:
                    row = box.row()
                    row.prop( img, 'resize_x' )
                    row.prop( img, 'resize_y' )

## Ogre Documentation to UI

class INFO_MT_ogre_shader_pass_attributes(bpy.types.Menu):
    bl_label = "Shader-Pass"

    def draw(self, context):
        layout = self.layout
        for cls in _OGRE_SHADER_REF_:
            layout.menu( cls.__name__ )

class INFO_MT_ogre_shader_texture_attributes(bpy.types.Menu):
    bl_label = "Shader-Texture"

    def draw(self, context):
        layout = self.layout
        for cls in _OGRE_SHADER_REF_TEX_:
            layout.menu( cls.__name__ )

class MeshMagick(object):
    ''' Usage: MeshMagick [global_options] toolname [tool_options] infile(s) -- [outfile(s)]
    Available Tools
    ===============
    info - print information about the mesh.
    meshmerge - Merge multiple submeshes into a single mesh.
    optimise - Optimise meshes and skeletons.
    rename - Rename different elements of meshes and skeletons.
    transform - Scale, rotate or otherwise transform a mesh.
    '''

    @staticmethod
    def get_merge_group( ob ):
        return get_merge_group( ob, prefix='magicmerge' )

    @staticmethod
    def merge( group, path='/tmp', force_name=None ):
        print('-'*80)
        print(' mesh magick - merge ')
        exe = CONFIG['OGRETOOLS_MESH_MAGICK']
        if not os.path.isfile( exe ):
            print( 'ERROR: can not find MeshMagick.exe' )
            print( exe )
            return

        files = []
        for ob in group.objects:
            if ob.data.users == 1:    # single users only
                files.append( os.path.join( path, ob.data.name+'.mesh' ) )
                print( files[-1] )

        opts = 'meshmerge'
        if sys.platform == 'linux2': cmd = '/usr/bin/wine %s %s' %(exe, opts)
        else: cmd = '%s %s' %(exe, opts)
        if force_name: output = force_name + '.mesh'
        else: output = '_%s_.mesh' %group.name
        cmd = cmd.split() + files + ['--', os.path.join(path,output) ]
        subprocess.call( cmd )
        print(' mesh magick - complete ')
        print('-'*80)

## Selector extras

class INFO_MT_instances(bpy.types.Menu):
    bl_label = "Instances"

    def draw(self, context):
        layout = self.layout
        inst = gather_instances()
        for data in inst:
            ob = inst[data][0]
            op = layout.operator(INFO_MT_instance.bl_idname, text=ob.name) # operator has no variable for button name?
            op.mystring = ob.name
        layout.separator()

class INFO_MT_instance(bpy.types.Operator):
    '''select instance group'''
    bl_idname = "ogre.select_instances"
    bl_label = "Select Instance Group"
    bl_options = {'REGISTER', 'UNDO'} # Options for this panel type
    mystring= StringProperty(name="MyString", description="hidden string", maxlen=1024, default="my string")

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        print( 'invoke select_instances op', event )
        select_instances( context, self.mystring )
        return {'FINISHED'}

class INFO_MT_groups(bpy.types.Menu):
    bl_label = "Groups"

    def draw(self, context):
        layout = self.layout
        for group in bpy.data.collections:
            op = layout.operator(INFO_MT_group.bl_idname, text=group.name)    # operator no variable for button name?
            op.mystring = group.name
        layout.separator()

class INFO_MT_group(bpy.types.Operator):
    '''select group'''
    bl_idname = "ogre.select_group"
    bl_label = "Select Group"
    bl_options = {'REGISTER'}                              # Options for this panel type
    mystring= StringProperty(name="MyString", description="hidden string", maxlen=1024, default="my string")

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        select_group( context, self.mystring )
        return {'FINISHED'}

## More UI

