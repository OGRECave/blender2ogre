import bpy
from .. import config
from ..report import Report
from . import material
from . import export
from . import helper
from ..meshy import OGREMESH_OT_preview

def add_preview_button(self, context):
    layout = self.layout
    op = layout.operator( 'ogremesh.preview', text='', icon='VIEWZOOM' )
    if op is not None:
        op.mesh = True

def auto_register(register):
    yield HT_toggle_ogre
    yield OP_interface_toggle
    yield MT_mini_report
    yield OGREMESH_OT_preview

    bpy.types.VIEW3D_PT_tools_active.append(add_preview_button)

    yield from export.auto_register(register)
    yield from helper.auto_register(register)

    if register and config.get('interface_toggle'):
        OP_interface_toggle.toggle(True)

"""
General purpose ui elements
"""

# FILE | RENDER | ... | OGRE |x| <-- check box
class OP_interface_toggle(bpy.types.Operator):
    '''Toggle Ogre UI'''
    bl_idname = "ogre.toggle_interface"
    bl_label = "Ogre UI"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        show = config.get('interface_toggle')
        print("toggle invoked:", show)
        print(dir(event))
        self.toggle(not show)
        config.update(interface_toggle=not show)
        return {'FINISHED'}

    @classmethod
    def toggle(self, show):
        class_func = bpy.utils.register_class
        if not show:
            class_func = bpy.utils.unregister_class

        class_func(HT_info_header)

        for clazz in material.ogre_register(show):
            class_func(clazz)

class HT_toggle_ogre(bpy.types.Header):
    bl_space_type = 'INFO'

    def draw(self, context):
        layout = self.layout
        show = config.get('interface_toggle')
        icon = 'CHECKBOX_DEHLT'
        if show:
            icon = 'CHECKBOX_HLT'
        op = layout.operator('ogre.toggle_interface', text='Ogre', icon=icon)

class MT_mini_report(bpy.types.Menu):
    bl_label = "Mini-Report | (see console for full report)"
    def draw(self, context):
        layout = self.layout
        txt = Report.report()
        for line in txt.splitlines():
            layout.label(text=line)

class HT_info_header(bpy.types.Header):
    bl_space_type = 'INFO'
    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        window = context.window
        scene = context.scene
        rd = scene.render
        ob = context.active_object
        screen = context.screen

        #layout.separator()

        #if _USE_JMONKEY_:
        #    row = layout.row(align=True)
        #    op = row.operator( 'jmonkey.preview', text='', icon='MONKEY' )

        # TODO
        #if _USE_TUNDRA_:
        #    row = layout.row(align=True)
        #    op = row.operator( 'tundra.preview', text='', icon='WORLD' )
        #    if TundraSingleton:
        #        op = row.operator( 'tundra.preview', text='', icon='META_CUBE' )
        #        op.EX_SCENE = False
        #        if not TundraSingleton.physics:
        #            op = row.operator( 'tundra.start_physics', text='', icon='PLAY' )
        #        else:
        #            op = row.operator( 'tundra.stop_physics', text='', icon='PAUSE' )
        #        op = row.operator( 'tundra.toggle_physics_debug', text='', icon='MOD_PHYSICS' )
        #        op = row.operator( 'tundra.exit', text='', icon='CANCEL' )

        add_preview_button(self, context)

        #row = layout.row(align=True)
        #sub = row.row(align=True)
        #sub.menu("INFO_MT_file")
        #sub.menu("INFO_MT_add")
        # TODO GAME if rd.use_game_engine: sub.menu("INFO_MT_game")
        # TODO GAME else: sub.menu("INFO_MT_render")

        row = layout.row(align=False); row.scale_x = 1.25
        #row.menu("INFO_MT_instances", icon='NODETREE', text='')
        #row.menu("INFO_MT_groups", icon='GROUP', text='')

        #layout.template_header()
        if not context.area.show_menus:
            if window.screen.show_fullscreen: 
                layout.operator("screen.back_to_previous", icon='SCREEN_BACK', text="Back to Previous")
            else:
                layout.template_ID(context.window, "screen", new="screen.new", unlink="screen.delete")
            layout.template_ID(context.screen, "scene", new="scene.new", unlink="scene.delete")

            #layout.separator()
            #layout.template_running_jobs()
            #layout.template_reports_banner()
            #layout.separator()
            if rd.has_multiple_engines: layout.prop(rd, "engine", text="")

            #layout.label(text=scene.statistics())
            layout.menu( "INFO_MT_help" )
        else:
            #layout.template_ID(context.window, "screen", new="screen.new", unlink="screen.delete")

            if ob:
                row = layout.row(align=True)
                row.prop( ob, 'name', text='' )
                row.prop( ob, 'draw_type', text='' )
                row.prop( ob, 'show_x_ray', text='' )
                row = layout.row()
                row.scale_y = 0.75; row.scale_x = 0.9
                row.prop( ob, 'layers', text='' )

            layout.separator()
            row = layout.row(align=True); row.scale_x = 1.1
            row.prop(scene.game_settings, 'material_mode', text='')
            row.prop(scene, 'camera', text='')

            layout.menu( 'MT_preview_material_text', icon='TEXT', text='' )

            layout.menu( "MT_ogre_docs" )
            layout.operator("wm.window_fullscreen_toggle", icon='FULLSCREEN_ENTER', text="")

