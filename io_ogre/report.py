import bpy, logging

logger = logging.getLogger('report')

class ReportSingleton(object):
    def __init__(self):
        self.reset()

    def show(self):
        if not bpy.app.background:
            bpy.ops.wm.call_menu( name='OGRE_MT_mini_report' )

    def reset(self):
        self.materials = []
        self.meshes = []
        self.lights = []
        self.cameras = []
        self.armatures = []
        self.armature_animations = []
        self.shape_keys = []
        self.shape_animations = []
        self.textures = []
        self.vertices = 0
        self.orig_vertices = 0
        self.faces = 0
        self.triangles = 0
        self.warnings = []
        self.errors = []
        self.messages = []
        self.paths = []
        self.importing = False

    def report(self):
        r = ['Report:']
        ex = ['\nExtended Report:']
        if self.errors:
            r.append( '  ERRORS:' )
            for a in self.errors: r.append( '    - %s' %a )

        #if not bpy.context.selected_objects:
        #    self.warnings.append('YOU DID NOT SELECT ANYTHING TO EXPORT')
        if self.warnings:
            r.append( '  WARNINGS:' )
            for a in self.warnings: r.append( '    - %s' %a )

        if self.messages:
            r.append( '  MESSAGES:' )
            for a in self.messages: r.append( '    - %s' %a )
        if self.paths:
            r.append( '  PATHS:' )
            for a in self.paths: r.append( '    - %s' %a )

        if self.vertices:
            action_name = "Exported"
            if self.importing:
                action_name = "Imported"

            r.append( '  Original Vertices: %s' % self.orig_vertices )
            r.append( '  %s Vertices: %s' % (action_name, self.vertices) )
            r.append( '  Original Faces: %s' % self.faces )
            r.append( '  %s Triangles: %s' % (action_name, self.triangles) )
        
        ## TODO report file sizes, meshes and textures

        for tag in 'meshes lights cameras armatures armature_animations shape_keys shape_animations materials textures'.split():
            attr = getattr(self, tag)
            if attr:
                name = tag.replace('_',' ').upper()
                r.append( '  %s: %s' %(name, len(attr)) )
                if attr:
                    ex.append( '  %s:' %name )
                    for a in attr: ex.append( '    . %s' %a )

        txt = '\n'.join( r )
        ex = '\n'.join( ex )        # console only - extended report
        print('_' * 80)
        print(txt)
        print(ex)
        print('_' * 80)
        return txt

Report = ReportSingleton()
