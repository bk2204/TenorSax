import codecs
import io
import sys
import xml.sax
import xml.sax.saxutils
import xml.sax.xmlreader

import lxml.etree

class GenericXSLTTransformer:
    def __init__(self, stylesheet):
        self.loc = stylesheet
        parsed = lxml.etree.parse(self.loc)
        self.transform = lxml.etree.XSLT(parsed)
        self.docbuf = io.StringIO()
        self.writer = xml.sax.saxutils.XMLGenerator(self.docbuf, "UTF-8")
    def _get_string(self):
        self.writer.endDocument()
        # lxml.etree refuses to read XML documents with an encoding declaration
        # from strings, so we have to convert it to bytes in order to get it to
        # parse correctly.
        sbuf = self.docbuf.getvalue()
        c = codecs.getencoder("UTF-8")
        bbuf = c(sbuf)[0]
        doc = lxml.etree.parse(io.BytesIO(bbuf))
        return str(self.transform(doc))
        print(str(result), file=sys.stderr)
        parsebuf = io.StringIO(str(result))
        self.reader.parse(parsebuf)
    def __getattr__(self, name):
        return getattr(self.writer, name)

class TextXSLTTransformer(GenericXSLTTransformer):
    def __init__(self, output, stylesheet):
        GenericXSLTTransformer.__init__(self, stylesheet)
        self.output = output
    def endDocument(self):
        self.s = self._get_string()
        if self.output is not None:
            self.output.write(self.s)
    def get_string(self):
        return self.s

class XSLTTransformer(GenericXSLTTransformer):
    def __init__(self, base, stylesheet):
        GenericXSLTTransformer.__init__(self, stylesheet)
        self.base = base
        self.reader = xml.sax.make_parser()
        self.reader.setContentHandler(self.base)
    def endDocument(self):
        s = self._get_string()
        parsebuf = io.StringIO(s)
        self.reader.parse(parsebuf)
