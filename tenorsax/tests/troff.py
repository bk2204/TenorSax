#!/usr/bin/python3

import re
import unittest

import tenorsax.sources.troff.parse
import tenorsax.filters.xslt

class TroffToTextTestCase(unittest.TestCase):
    @staticmethod
    def t_run(inp):
        f = tenorsax.filters.xslt.TextXSLTTransformer(None, "xslt/trim.xsl")
        p = tenorsax.sources.troff.parse.Parser(f)
        p.parse(inp)
        return f.get_string()

class RequestTests(TroffToTextTestCase):
    def test_rename(self):
        self.assertEqual(self.t_run(".rn br BR\nabc\n.BR\ndef\n"), "abc\ndef\n")
    def test_rename_oldname(self):
        self.assertEqual(self.t_run(".rn br BR\nabc\n.br\ndef\n"), "abc def\n")
    def test_remove(self):
        self.assertEqual(self.t_run(".rm br\nabc\n.br\ndef\n"), "abc def\n")
    def test_alias(self):
        self.assertEqual(self.t_run(".do als BR br\nabc\n.BR\ndef\n"), "abc\ndef\n")
    def test_alias_oldname(self):
        self.assertEqual(self.t_run(".do als BR br\nabc\n.br\ndef\n"), "abc\ndef\n")

class ExtendedModeTests(TroffToTextTestCase):
    def test_basic(self):
        self.assertEqual(self.t_run("abc\n.do br\ndef\n"), "abc\ndef\n")

class CopyModeTests(TroffToTextTestCase):
    def test_conditional(self):
        text = """.de AA
start
..
.de BB
end
..
.de pp
.ep
.AA
.nr pa 1
..
.de ep
.if \\\\n(pa \\{
.BB
.nr pa 0
.\\}
..
.pp
.pp
"""
        text2 = re.sub(r"([{}])", r"\\\1", text)
        self.assertEqual(self.t_run(text), self.t_run(text2))

class StringTests(TroffToTextTestCase):
    def setUp(self):
        self.dd = ".de DD\ntx\n..\n"
        self.ee = ".de EE\ntxt\n..\n"
        self.tx = ".ds tx Text\n"
        self.bb = ".ds BB \"\n.if dBB exists\n"
        self.cc = ".CC \"\n.if dCC exists\n"
    def test_creation(self):
        self.assertEqual(self.t_run(".ds AA Text\n\*(AA\n"), "Text\n")
    def test_short_empty(self):
        self.assertEqual(self.t_run(self.bb), "exists\n")
    def test_autovivification(self):
        self.assertEqual(self.t_run(self.cc), "exists\n")
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
    def test_rename(self):
        self.assertEqual(self.t_run(self.dd + self.tx + '.rn DD D2\n\\*(\\*(D2\n'),
                "Text\n")
    def test_remove(self):
        self.assertEqual(self.t_run(self.dd + self.tx + '.rm DD\n\\*(DD\n'),
                "")

class MacroTests(TroffToTextTestCase):
    def setUp(self):
        self.aa = ".de AA\n\\\\$1\n.br\n\\\\$2\n.br\njkl\n..\n"
        self.pr = ".de PR\n.br\n\\\\$1\n.br\n..\n"
        self.an = ".de AN\n.AA abc def\njkl\n..\n"
        self.cc = ".de CC\ntext \\\\$1 here\nand here\n..\n"
        self.ff = ".de FF\n\\\\$1 \\\\$3\n..\n"
        self.gg = ".de GG\na b c\n.br d\ne f\ng h i\n..\n"
        self.na = ".de NA\n\\\\$0\n..\n"
        self.co = ".de CO\n\\\\n(.$\n..\n"
    def test_count_args_1(self):
        self.assertEqual(self.t_run(self.co + '.CO 1 2 3\n'), '3\n')
    def test_count_args_2(self):
        self.assertEqual(self.t_run(self.co + '.CO 1\n'), '1\n')
    def test_count_args_3(self):
        self.assertEqual(self.t_run('\\n(.$\n'), '0\n')
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
    def test_rename(self):
        self.assertEqual(self.t_run(self.aa + self.an + '.rn AN BN\n.BN\n'),
                "abc\ndef\njkl jkl\n")
    def test_remove(self):
        self.assertEqual(self.t_run(self.aa + self.an + '.rm AN\n.AN\n'), "")
    def test_remove_within(self):
        self.assertEqual(self.t_run(self.aa + self.an + '.rm AA\n.AN\n'), "jkl\n")
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
    def test_self_name(self):
        self.assertEqual(self.t_run(self.na + '.NA arg\n'),
                "NA\n")
    def test_self_name_string(self):
        self.assertEqual(self.t_run(self.na + '\\*(NA arg\n'),
                "arg\n")
    def test_empty_macro(self):
        self.assertEqual(self.t_run(r'''.de AA
..
.de BB
..
.ie dBB success
.el failure
'''), 'success\n')
    def test_copy_mode_ending(self):
        self.assertEqual(self.t_run(r'''.de AA
..
.de BB
success.
..
.BB
'''), 'success.\n')
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

class NumericTests(TroffToTextTestCase):
    def test_creation(self):
        self.assertEqual(self.t_run('.nr no 5\n\\n(no\n'), '5\n')
    def test_addition(self):
        self.assertEqual(self.t_run('.nr no 5\n.nr no +3\n\\n(no\n'), '8\n')
    def test_subtraction(self):
        self.assertEqual(self.t_run('.nr no 5\n.nr no -3\n\\n(no\n'), '2\n')
    def test_creation_with_increment(self):
        self.assertEqual(self.t_run('.nr no 5 1\n\\n(no\n'), '5\n')
    def test_increment(self):
        self.assertEqual(self.t_run('.nr no 5 1\n\\n+(no \\n+(no\n'), '6 7\n')
    def test_decrement(self):
        self.assertEqual(self.t_run('.nr no 5 1\n\\n-(no \\n-(no\n'), '4 3\n')
    def test_increment_decrement(self):
        self.assertEqual(self.t_run('.nr no 5 1\n\\n+(no \\n-(no \\n-(no\n'),
                '6 5 4\n')

class NumericParsingTests(TroffToTextTestCase):
    def test_addition(self):
        self.assertEqual(self.t_run('.nr no 5+5\n\\n(no\n'), '10\n')
    def test_subtraction(self):
        self.assertEqual(self.t_run('.nr no 8-5\n\\n(no\n'), '3\n')
    def test_multiplication(self):
        self.assertEqual(self.t_run('.nr no 8*5\n\\n(no\n'), '40\n')
    def test_division(self):
        self.assertEqual(self.t_run('.nr no 36/5\n\\n(no\n'), '7\n')
    def test_modulus(self):
        self.assertEqual(self.t_run('.nr no 37%5\n\\n(no\n'), '2\n')
    def test_lessthan_true(self):
        self.assertEqual(self.t_run('.nr no 3<5\n\\n(no\n'), '1\n')
    def test_lessthan_false(self):
        self.assertEqual(self.t_run('.nr no 5<3\n\\n(no\n'), '0\n')
    def test_lessthan_equal(self):
        self.assertEqual(self.t_run('.nr no 3<3\n\\n(no\n'), '0\n')
    def test_greaterthan_true(self):
        self.assertEqual(self.t_run('.nr no 5>3\n\\n(no\n'), '1\n')
    def test_greaterthan_false(self):
        self.assertEqual(self.t_run('.nr no 3>5\n\\n(no\n'), '0\n')
    def test_greaterthan_equal(self):
        self.assertEqual(self.t_run('.nr no 3>5\n\\n(no\n'), '0\n')
    def test_lessthanequal_true(self):
        self.assertEqual(self.t_run('.nr no 3<=5\n\\n(no\n'), '1\n')
    def test_lessthanequal_false(self):
        self.assertEqual(self.t_run('.nr no 5<=3\n\\n(no\n'), '0\n')
    def test_lessthanequal_equal(self):
        self.assertEqual(self.t_run('.nr no 3<=3\n\\n(no\n'), '1\n')
    def test_greaterthan_true(self):
        self.assertEqual(self.t_run('.nr no 5>=3\n\\n(no\n'), '1\n')
    def test_greaterthan_false(self):
        self.assertEqual(self.t_run('.nr no 3>=5\n\\n(no\n'), '0\n')
    def test_greaterthan_equal(self):
        self.assertEqual(self.t_run('.nr no 3>=3\n\\n(no\n'), '1\n')
    def test_equal_true(self):
        self.assertEqual(self.t_run('.nr no 3=3\n\\n(no\n'), '1\n')
    def test_equal_less(self):
        self.assertEqual(self.t_run('.nr no 3=5\n\\n(no\n'), '0\n')
    def test_equal_greater(self):
        self.assertEqual(self.t_run('.nr no 5=3\n\\n(no\n'), '0\n')
    def test_dblequal_true(self):
        self.assertEqual(self.t_run('.nr no 3==3\n\\n(no\n'), '1\n')
    def test_dblequal_less(self):
        self.assertEqual(self.t_run('.nr no 3==5\n\\n(no\n'), '0\n')
    def test_dblequal_greater(self):
        self.assertEqual(self.t_run('.nr no 5==3\n\\n(no\n'), '0\n')
    def test_notequal_false(self):
        self.assertEqual(self.t_run('.nr no 3<>3\n\\n(no\n'), '0\n')
    def test_notequal_less(self):
        self.assertEqual(self.t_run('.nr no 3<>5\n\\n(no\n'), '1\n')
    def test_notequal_greater(self):
        self.assertEqual(self.t_run('.nr no 5<>3\n\\n(no\n'), '1\n')

class FloatTests(TroffToTextTestCase):
    def test_creation_integer(self):
        self.assertEqual(self.t_run('.do nrf no 5\n\\n(no\n'), '5.0\n')
    def test_creation_float(self):
        self.assertEqual(self.t_run('.do nrf no 5.2\n\\n(no\n'), '5.2\n')
    def test_addition_integer(self):
        self.assertEqual(self.t_run('.do nrf no 5\n.do nrf no +3\n\\n(no\n'),
                '8.0\n')
    def test_addition_float(self):
        self.assertEqual(self.t_run('.do nrf no 5.2\n.do nrf no +3.6\n\\n(no\n'), '8.8\n')
    def test_subtraction_integer(self):
        self.assertEqual(self.t_run('.do nrf no 5\n.do nrf no -3\n\\n(no\n'),
                '2.0\n')
    def test_subtraction_float(self):
        self.assertEqual(self.t_run('.do nrf no 5.2\n.do nrf no -3.6\n\\n(no\n'), '1.6\n')
    def test_creation_with_increment_integer(self):
        self.assertEqual(self.t_run('.do nrf no 5 1\n\\n(no\n'), '5.0\n')
    def test_creation_with_increment_float(self):
        self.assertEqual(self.t_run('.do nrf no 5.2 1.3\n\\n(no\n'), '5.2\n')
    def test_increment_integer(self):
        self.assertEqual(self.t_run('.do nrf no 5 1\n\\n+(no \\n+(no\n'),
                '6.0 7.0\n')
    def test_increment_float(self):
        self.assertEqual(self.t_run('.do nrf no 5.2 1.3\n\\n+(no \\n+(no\n'),
                '6.5 7.8\n')
    def test_decrement_integer(self):
        self.assertEqual(self.t_run('.do nrf no 5 1\n\\n-(no \\n-(no\n'),
                '4.0 3.0\n')
    def test_decrement_float(self):
        self.assertEqual(self.t_run('.do nrf no 5.2 1.3\n\\n-(no \\n-(no\n'),
                '3.9 2.6\n')
    def test_increment_decrement_integer(self):
        self.assertEqual(self.t_run('.do nrf no 5 1\n\\n+(no \\n-(no \\n-(no\n'),
                '6.0 5.0 4.0\n')
    def test_increment_decrement_float(self):
        self.assertEqual(self.t_run('.do nrf no 5.2 1.3\n\\n+(no \\n-(no \\n-(no\n'),
                '6.5 5.2 3.9\n')

class ExtensionTests(TroffToTextTestCase):
    def setUp(self):
        self.a = ".de AA\ndisabled\n.br\n.BB\n..\n.do de AAA\nenabled\n.br\n.BB\n..\n"
        self.b = ".de BB\n.do tenorsax get-ext ex\n\\\\n(ex\n.br\n..\n"
        self.aa = self.a + self.b
    def test_default(self):
        self.assertEqual(self.t_run(self.aa + ".AAA\n"), "disabled\n0\n")
    def test_enable(self):
        self.assertEqual(self.t_run(self.aa + ".do tenorsax ext 1\n.AAA\n"),
                "enabled\n1\n")
    def test_disabled(self):
        self.assertEqual(self.t_run(self.aa + ".do tenorsax ext 0\n.AAA\n"),
                "disabled\n0\n")
    def test_disable(self):
        self.assertEqual(self.t_run(self.aa + ".do tenorsax ext 1\n.do tenorsax ext 0\n.AAA\n"), "disabled\n0\n")
    def test_implementation(self):
        self.assertEqual(self.t_run(".do tenorsax get-implementation im\n\\n(im\n"), "6450531\n")

class ConditionalTests(TroffToTextTestCase):
    def setUp(self):
        self.tc0 = ".if \\n(no branch\n"
        self.tc1 = ".ie \\n(no first branch\n.el second branch\n"
        self.tc2 = ".if \\n(no \{\nbranch\n.\}\n"
        self.tc3 = ".ie \\n(no \{\nfirst branch\n.\}\n.el \{\nsecond branch\n.\}\n"
        self.tc4 = ".ds on text\n.if '\\*(no'\\*(on' branch\n"
        self.tc5 = ".ds on text\n.ie '\\*(no'\\*(on' first branch\n.el second branch\n"
        self.tc6 = ".ds on text\n.if '\\*(no'\\*(on' \{\nbranch\n.\}\n"
        self.tc7 = ".ds on text\n.ie '\\*(no'\\*(on' \{\nfirst branch\n.\}\n.el \{\nsecond branch\n.\}\n"
        self.tc8 = ".if !\\n(no branch\n"
        self.tc9 = ".ie !\\n(no first branch\n.el second branch\n"
        self.tca = ".if !\\n(no \{\nbranch\n.\}\n"
        self.tcb = ".ie !\\n(no \{\nfirst branch\n.\}\n.el \{\nsecond branch\n.\}\n"
        self.tcc = ".ds on text\n.if !'\\*(no'\\*(on' branch\n"
        self.tcd = ".ds on text\n.ie !'\\*(no'\\*(on' first branch\n.el second branch\n"
        self.tce = ".ds on text\n.if !'\\*(no'\\*(on' \{\nbranch\n.\}\n"
        self.tcf = ".ds on text\n.ie !'\\*(no'\\*(on' \{\nfirst branch\n.\}\n.el \{\nsecond branch\n.\}\n"
        self.td0 = ".de AA\n.ie \\\\n(no=5 \\\\$1 true\n.el \\\\$1 false\n..\n.AA branch\n"
        self.td1 = ".de AA\n.ie dBB \\\\$1 true\n.el \\\\$1 false\n..\n.AA branch\n"
    def test_short_if_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.tc0), "")
    def test_short_if_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.tc0), "branch\n")
    def test_short_if_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.tc0), "")
    def test_short_ie_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.tc1), "second branch\n")
    def test_short_ie_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.tc1), "first branch\n")
    def test_short_ie_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.tc1), "second branch\n")
    def test_long_if_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.tc2), "")
    def test_long_if_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.tc2), "branch\n")
    def test_long_if_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.tc2), "")
    def test_long_ie_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.tc3), "second branch\n")
    def test_long_ie_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.tc3), "first branch\n")
    def test_long_ie_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.tc3), "second branch\n")
    def test_short_if_unequal(self):
        self.assertEqual(self.t_run(".ds no not\n" + self.tc4), "")
    def test_short_if_equal(self):
        self.assertEqual(self.t_run(".ds no text\n" + self.tc4), "branch\n")
    def test_short_ie_unequal(self):
        self.assertEqual(self.t_run(".ds no not\n" + self.tc5), "second branch\n")
    def test_short_ie_equal(self):
        self.assertEqual(self.t_run(".ds no text\n" + self.tc5), "first branch\n")
    def test_long_if_unequal(self):
        self.assertEqual(self.t_run(".ds no not\n" + self.tc6), "")
    def test_long_if_equal(self):
        self.assertEqual(self.t_run(".ds no text\n" + self.tc6), "branch\n")
    def test_long_ie_unequal(self):
        self.assertEqual(self.t_run(".ds no not\n" + self.tc7), "second branch\n")
    def test_long_ie_equal(self):
        self.assertEqual(self.t_run(".ds no text\n" + self.tc7), "first branch\n")
    def test_neg_short_if_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.tc8), "branch\n")
    def test_neg_short_if_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.tc8), "")
    def test_neg_short_if_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.tc8), "branch\n")
    def test_neg_short_ie_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.tc9), "first branch\n")
    def test_neg_short_ie_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.tc9), "second branch\n")
    def test_neg_short_ie_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.tc9), "first branch\n")
    def test_neg_long_if_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.tca), "branch\n")
    def test_neg_long_if_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.tca), "")
    def test_neg_long_if_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.tca), "branch\n")
    def test_neg_long_ie_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.tcb), "first branch\n")
    def test_neg_long_ie_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.tcb), "second branch\n")
    def test_neg_long_ie_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.tcb), "first branch\n")
    def test_neg_short_if_unequal(self):
        self.assertEqual(self.t_run(".ds no not\n" + self.tcc), "branch\n")
    def test_neg_short_if_equal(self):
        self.assertEqual(self.t_run(".ds no text\n" + self.tcc), "")
    def test_neg_short_ie_unequal(self):
        self.assertEqual(self.t_run(".ds no not\n" + self.tcd), "first branch\n")
    def test_neg_short_ie_equal(self):
        self.assertEqual(self.t_run(".ds no text\n" + self.tcd), "second branch\n")
    def test_neg_long_if_unequal(self):
        self.assertEqual(self.t_run(".ds no not\n" + self.tce), "branch\n")
    def test_neg_long_if_equal(self):
        self.assertEqual(self.t_run(".ds no text\n" + self.tce), "")
    def test_neg_long_ie_unequal(self):
        self.assertEqual(self.t_run(".ds no not\n" + self.tcf), "first branch\n")
    def test_neg_long_ie_equal(self):
        self.assertEqual(self.t_run(".ds no text\n" + self.tcf), "second branch\n")
    def test_short2_ie_false(self):
        self.assertEqual(self.t_run(".nr no 0\n" + self.td0), "branch false\n")
    def test_short2_ie_true(self):
        self.assertEqual(self.t_run(".nr no 5\n" + self.td0), "branch true\n")
    def test_short2_ie_negative(self):
        self.assertEqual(self.t_run(".nr no -2\n" + self.td0), "branch false\n")
    def test_cond_reg_true(self):
        self.assertEqual(self.t_run(".ds BB \"abc\n" + self.td1), "branch true\n")
    def test_cond_reg_false(self):
        self.assertEqual(self.t_run(self.td1), "branch false\n")

class CommentTests(TroffToTextTestCase):
    def test_default(self):
        self.assertEqual(self.t_run("""This is\\" a comment
some text.  This is\\# also a comment
some more text.
"""), "This is some text. This issome more text.\n")

class BugTests(TroffToTextTestCase):
    def test_quoted_escapes(self):
        self.assertEqual(self.t_run(""".de AA
.if !'\\\\$1'' branch
..
.de BB
.AA "\\\\$1"
..
.BB abc def
"""), "branch\n")
    def test_quoted_spacing(self):
        self.assertEqual(self.t_run(""".de LU
.ds \\\\$2 \\\\$1
..
.de IT
.if !'\\\\$1'' \\\\{
.LU "\\\\$1" ST
.\\\\}
..
.IT text
"""), "")
    def test_conditional_argument_expansion(self):
        self.assertEqual(self.t_run(""".de PR
\\\\$1
\\\\$2
\\\\$3
.br
..
.de SE
.ie ''\\\\$2' .PR "d\\\\$1" alone
.el .PR "d\\\\$1" with "ch\\\\$2"
..
.de PO
.SE ip "\\\\$1"
..
.PO
.PO eese
"""), "dip alone\ndip with cheese\n")

if __name__ == '__main__':
    unittest.main()
