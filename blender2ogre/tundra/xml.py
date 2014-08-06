class RElement(object):
    def appendChild( self, child ):
        self.childNodes.append( child )

    def setAttribute( self, name, value ):
        self.attributes[name]=value

    def __init__(self, tag):
        self.tagName = tag
        self.childNodes = []
        self.attributes = {}

    def toprettyxml(self, lines, indent ):
        s = '<%s ' % self.tagName
        sortedNames = sorted( self.attributes.keys() )
        for name in sortedNames:
            value = self.attributes[name]
            if not isinstance(value, str):
                value = str(value)
            s += '%s=%s ' % (name, quoteattr(value))
        if not self.childNodes:
            s += '/>'; lines.append( ('  '*indent)+s )
        else:
            s += '>'; lines.append( ('  '*indent)+s )
            indent += 1
            for child in self.childNodes:
                child.toprettyxml( lines, indent )
            indent -= 1
            lines.append(('  '*indent) + '</%s>' % self.tagName )

class RDocument(object):
    def __init__(self):
        self.documentElement = None

    def appendChild(self, root):
        self.documentElement = root

    def createElement(self, tag):
        e = RElement(tag)
        e.document = self
        return e

    def toprettyxml(self):
        indent = 0
        lines = []
        self.documentElement.toprettyxml(lines, indent)
        return '\n'.join(lines)

