import sys
import xml.sax.handler

class SAXGenerator(xml.sax.handler.ContentHandler):
    def __init__(self, output=None):
        if output is None:
            output = sys.stdout
        self._output = output
        self._write = lambda x: self._output.write((self._indent * "  ") +x)
        self._indent = 0
    def startDocument(self):
        self._write("startDocument\n")
        self._indent += 1
    def endDocument(self):
        self._indent -= 1
        self._write("endDocument\n")
    def startPrefixMapping(self, prefix, uri):
        self._write("startPrefixMapping %r %r\n" % (prefix, uri))
        self._indent += 1
    def endPrefixMapping(self, prefix):
        self._indent -= 1
        self._write("endPrefixMapping %r\n" % prefix)
    def startElementNS(self, name, eqname, attrs):
        self._write("startElementNS %r %r %r\n" % (name[0], name[1], eqname))
        self._indent += 1
        for qname in attrs.getQNames():
            name = attrs.getNameByQName(qname)
            value = attrs.getValueByQName(qname)
            self._write("attr %r %r %r %r\n" % (name[0], name[1], qname, value))
    def endElementNS(self, name, qname):
        self._indent -= 1
        self._write("endElementNS %r %r %r\n" % (name[0], name[1], qname))
    def characters(self, content):
        self._write("characters %r\n" % content)
    def ignorableWhitespace(self, whitespace):
        self._write("ignorableWhitespace %r\n" % whitespace)
