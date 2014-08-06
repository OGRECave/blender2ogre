from xml.sax.saxutils import XMLGenerator, quoteattr

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

    def end_tag(self, name):
        self.indent -= 4
        self.output.write(" " * self.indent)
        self.output.write("</%s>\n" % name)

    def leaf_tag(self, name, attrs):
        self._out_tag(name, attrs, True)

    def close(self):
        self.end_tag( self.root_tag )
