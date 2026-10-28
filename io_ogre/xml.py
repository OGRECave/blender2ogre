from xml.sax.saxutils import XMLGenerator, quoteattr

class AttributePlaceholder:
    """A fixed-width attribute value that is filled in after it was written."""

    def __init__(self, position, width):
        self.position = position
        self.width = width

class SimpleSaxWriter():
    def __init__(self, output, root_tag, root_attrs):
        self.output = output
        self.root_tag = root_tag
        self.indent=0
        output.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.start_tag(root_tag, root_attrs)

    def _out_tag(self, name, attrs, isLeaf):
        # sorted attributes -- don't want attributes output in random order, which is what the XMLGenerator class does
        self.output.write(" " * self.indent)
        self.output.write("<%s" % name)
        sortedNames = sorted( attrs.keys() )  # sorted list of attribute names
        for name in sortedNames:
            value = attrs[ name ]
            # if not of type string,
            if not isinstance(value, str):
                # turn it into a string
                value = str(value)
            self.output.write(" %s=%s" % (name, quoteattr(value)))
        if isLeaf:
            self.output.write("/")
        else:
            self.indent += 4
        self.output.write(">\n")

    def start_tag(self, name, attrs):
        self._out_tag(name, attrs, False)

    def start_tag_with_placeholder(self, name, attr, width=10):
        """
        Start an element whose numeric attribute `attr` is not known yet.

        `width` characters are reserved for the value; pass the returned
        placeholder to fill_placeholder() once the value is available. This
        avoids writing a placeholder and then rewriting the whole document.
        """
        self.output.write(" " * self.indent)
        self.output.write("<%s %s=\"" % (name, attr))
        position = self.output.tell()
        self.output.write(" " * width)
        self.output.write("\">\n")
        self.indent += 4
        return AttributePlaceholder(position, width)

    def fill_placeholder(self, placeholder, value):
        text = str(value)
        if len(text) > placeholder.width:
            raise ValueError("value %s does not fit into placeholder of width %s"
                             % (text, placeholder.width))
        # remember where we were so writing can continue afterwards
        current = self.output.tell()
        self.output.seek(placeholder.position)
        self.output.write(text.ljust(placeholder.width))
        self.output.seek(current)

    def end_tag(self, name):
        self.indent -= 4
        self.output.write(" " * self.indent)
        self.output.write("</%s>\n" % name)

    def leaf_tag(self, name, attrs):
        self._out_tag(name, attrs, True)

    def close(self):
        self.end_tag( self.root_tag )

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
        self.comments = []

    def appendChild(self, root):
        self.documentElement = root
    
    def addComment(self, text):
        self.comments.append("<!-- {} -->".format(text))
    
    def createElement(self, tag):
        e = RElement(tag)
        e.document = self
        return e

    def toprettyxml(self):
        indent = 0
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines += self.comments
        self.documentElement.toprettyxml(lines, indent)
        return '\n'.join(lines)

