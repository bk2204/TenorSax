PYTHON3		= python3
ENVVARS		= PYTHONPATH=.
SCRIPT		= tenorsax/tests/troff.py

DOCS		= quick-test
ifneq ($(FANCY),)
XSLT_STYLE	= base
XSLT		= http://www.crustytoothpaste.net/rsrc/dct-xslt/docbook/fo/style/$(XSLT_STYLE)/cvt.xsl
FOP_ARGS	= -c /etc/fop/fop.xconf
else
XSLT		= http://docbook.sourceforge.net/release/xsl-ns/current/fo/docbook.xsl
endif

test check:
	$(ENVVARS) $(PYTHON3) $(SCRIPT)

vtest vcheck test-v:
	$(ENVVARS) $(PYTHON3) $(SCRIPT) -v

clean:
	$(RM) doc/*.pdf doc/*.fo doc/*.xml

doc docs: $(patsubst %,doc/%.pdf,$(DOCS))

%.pdf: %.fo
	fop $(FOP_ARGS) -fo $< -pdf $@

%.fo: %.xml
	xsltproc -o $@ $(XSLT) $<

%.xml: %.mxd
	./troff -mxd -Txml $< > $@
