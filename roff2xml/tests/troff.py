#!/usr/bin/python3

import unittest

import roff2xml.sources.troff.parse
import roff2xml.filters.xslt

class TroffToTextTestCase(unittest.TestCase):
    @staticmethod
    def t_run(inp):
        f = roff2xml.filters.xslt.TextXSLTTransformer("xslt/trim.xsl")
        p = roff2xml.sources.troff.parse.Parser(f)
        p.parse(inp)
        return f.get_string()

class StringTests(TroffToTextTestCase):
    def setUp(self):
        self.dd = ".de DD\ntx\n..\n"
        self.ee = ".de EE\ntxt\n..\n"
        self.tx = ".ds tx Text\n"
    def test_creation(self):
        self.assertEqual(self.t_run(".ds AA Text\n\*(AA\n"), "Text\n")
    def test_parse_last(self):
        self.assertEqual(self.t_run('.ds AA "Some text\n\*(AA\n'),
                "Some text\n")
    def test_parse_last_quote(self):
        self.assertEqual(self.t_run('.ds AA "Some text"\n\*(AA\n'),
                'Some text"\n')
    def test_run_as_macro(self):
        self.assertEqual(self.t_run('.ds BB abc def\n.BB\n\n'), 'abc def\n')
    def test_interpolation(self):
        self.assertEqual(self.t_run(self.dd + self.tx + "\*(\*(DD\n"), "Text\n")
    def test_parse_interpolation(self):
        self.assertEqual(self.t_run(self.ee + self.tx + "\*(\*(EE\n"), "Textt\n")

class MacroTests(TroffToTextTestCase):
    def setUp(self):
        self.aa = ".de AA\n\\\\$1\n.br\n\\\\$2\n.br\njkl\n..\n"
        self.pr = ".de PR\n.br\n\\\\$1\n.br\n..\n"
        self.an = ".de AN\n.AA abc def\njkl\n..\n"
        self.cc = ".de CC\ntext \\\\$1 here\nand here\n..\n"
        self.ff = ".de FF\n\\\\$1 \\\\$3\n..\n"
        self.gg = ".de GG\na b c\n.br d\ne f\ng h i\n..\n"
    def test_creation(self):
        self.assertEqual(self.t_run('.de AA\nSome text\n..\n.AA\n'),
                'Some text\n')
    def test_execution(self):
        self.assertEqual(self.t_run('.de AA\nSome\n.br\ntext\n..\n.AA\n'),
                'Some\ntext\n')
    def test_parse(self):
        self.assertEqual(self.t_run('.de AA\n\\\\$1\n.br\n..\n.AA Text\n'),
                'Text\n')
    def test_quote_parsing(self):
        self.assertEqual(self.t_run(self.pr + self.aa +
            '.PR "AA exec"\n.AA "abc"def ghi"\n'), "AA exec\nabc\ndef\njkl\n")
    def test_call_from_macro(self):
        self.assertEqual(self.t_run(self.aa + self.an + '.AN\n'),
                "abc\ndef\njkl jkl\n")
    def test_call_as_string(self):
        self.assertEqual(self.t_run(self.aa + self.an + '\\*(AN\n'),
                "abc\ndef\njkl jkl\n")
    def test_complex_0(self):
        self.assertEqual(self.t_run(self.ff + self.gg + '.FF \\*(GG\n'),
                "a c\ne f g h i\n")
    def test_complex_1(self):
        self.assertEqual(self.t_run(self.ff + self.gg + '.FF "\\*(GG\n'),
                "a b c\ne f g h i\n")
    @unittest.expectedFailure
    def test_complex_2(self):
        self.assertEqual(self.t_run(self.ff + self.gg + '.FF \\*(GG\n.FF "\\*(GG\n'),
                "a c\ne f g h i\na b c\ne f g h i\n")
    def test_call_with_string(self):
        self.assertEqual(self.t_run(self.aa + self.cc + '.CC \\*(AA\n'),
                "text here and here\njkl\n")
    def test_call_with_self(self):
        self.assertEqual(self.t_run(self.aa + self.cc + '.CC \\*(CC\n'),
                "text text here and here and here\n")
    def test_arguments(self):
        self.assertEqual(self.t_run(r'''.de AA
\\$2
.br
\\$1
..
.AA text Some
'''), 'Some\ntext\n')

class IgnoreTests(TroffToTextTestCase):
    def test_ignore(self):
        self.assertEqual(self.t_run('.ig\nSome text\n..\n'), '')

if __name__ == '__main__':
    unittest.main()
