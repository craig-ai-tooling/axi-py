"""The output contract, pinned byte for byte. Four tools vendor this; a change to any
expected string here is a change to what every one of them prints."""
import contextlib
import io
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import axi  # noqa: E402
import vendor  # noqa: E402


class ExitCodes(unittest.TestCase):
    def test_the_table_in_axi_contract_md(self):
        self.assertEqual((axi.E_OK, axi.E_ERR, axi.E_USAGE, axi.E_NOTFOUND, axi.E_REFUSED, axi.E_PARTIAL),
                         (0, 1, 2, 3, 4, 5))


class Scalar(unittest.TestCase):
    def test_none_and_false_are_different_facts(self):
        self.assertEqual(axi._tv(None), "")
        self.assertEqual(axi._tv(False), "false")
        self.assertEqual(axi._tv(True), "true")

    def test_zero_is_a_value_not_unknown(self):
        self.assertEqual(axi._tv(0), "0")
        self.assertEqual(axi._tv(0.5), "0.5")

    def test_plain_text_is_unquoted(self):
        self.assertEqual(axi._tv("plain text"), "plain text")

    def test_comma_quote_and_newline_are_quoted(self):
        self.assertEqual(axi._tv("a,b"), '"a,b"')
        self.assertEqual(axi._tv('say "hi"'), '"say ""hi"""')
        self.assertEqual(axi._tv("one\ntwo"), '"one\\ntwo"')

    def test_carriage_returns_are_dropped(self):
        self.assertEqual(axi._tv("one\r\ntwo"), '"one\\ntwo"')
        self.assertEqual(axi._tv("x\r"), "x")


class Block(unittest.TestCase):
    def test_rows(self):
        rows = [{"id": 1, "name": "a,b", "ok": False}, {"id": 2, "name": "c", "ok": None}]
        self.assertEqual(axi.toon("items", ["id", "name", "ok"], rows),
                         'items[2]{id,name,ok}:\n  1,"a,b",false\n  2,c,')

    def test_empty_is_definitive(self):
        self.assertEqual(axi.toon("items", ["id"], []), "items[0]{id}: (none)")

    def test_missing_field_is_unknown(self):
        self.assertEqual(axi.toon("t", ["a", "b"], [{"a": 1}]), "t[1]{a,b}:\n  1,")

    def test_indent(self):
        self.assertEqual(axi.toon("t", ["a"], [{"a": 1}], indent="    "), "t[1]{a}:\n    1")


class Helpers(unittest.TestCase):
    def test_nxt(self):
        self.assertEqual(axi.nxt(), "")
        self.assertEqual(axi.nxt("x doctor", "x list"), "\nnext: x doctor | x list")

    def test_emit_skips_empty_parts(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            axi.emit("a", "", None, "b")
        self.assertEqual(out.getvalue(), "a\nb\n")

    def test_die_prints_to_stderr_and_exits_with_the_code(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            axi.die("nope", axi.E_NOTFOUND)
        self.assertEqual(cm.exception.code, 3)
        self.assertEqual(err.getvalue(), "error: nope\n")

    def test_die_defaults_to_e_err(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            axi.die("nope")
        self.assertEqual(cm.exception.code, 1)

    def test_size_hint(self):
        self.assertEqual(axi.size_hint("abcdef", "abc"), "  [+3B truncated, --full]")
        self.assertEqual(axi.size_hint("abc", "abc"), "")


class Vendoring(unittest.TestCase):
    """vendor.py writes a copy plus a test; that test must pass on the copy and fail on an edit."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "tool_axi").mkdir()
        (self.tmp / "tool_axi" / "__init__.py").write_text("")
        self.ref = f"v{axi.__version__}"

    def run_generated_test(self):
        r = subprocess.run([sys.executable, "-m", "unittest", "tests.test_axi_vendored"],
                           cwd=self.tmp, capture_output=True, text=True)
        return r.returncode, r.stderr

    def test_the_copy_is_the_source_byte_for_byte_after_two_header_lines(self):
        mod, _ = vendor.vendor(self.tmp, "tool_axi", self.ref)
        self.assertEqual(mod.read_bytes().split(b"\n", 2)[2], (ROOT / "axi.py").read_bytes())

    def test_generated_test_passes_on_a_fresh_copy(self):
        vendor.vendor(self.tmp, "tool_axi", self.ref)
        rc, err = self.run_generated_test()
        self.assertEqual(rc, 0, err)

    def test_generated_test_fails_on_an_edit(self):
        mod, _ = vendor.vendor(self.tmp, "tool_axi", self.ref)
        mod.write_bytes(mod.read_bytes().replace(b"(none)", b"(empty)"))
        rc, err = self.run_generated_test()
        self.assertNotEqual(rc, 0)
        self.assertIn("edited in place", err)

    def test_generated_test_fails_on_a_dev_header(self):
        vendor.vendor(self.tmp, "tool_axi", self.ref + "-dev")
        rc, err = self.run_generated_test()
        self.assertNotEqual(rc, 0)
        self.assertIn("no release header", err)

    def test_generated_test_fails_when_header_and_body_versions_disagree(self):
        vendor.vendor(self.tmp, "tool_axi", "v9.9.9")
        rc, _ = self.run_generated_test()
        self.assertNotEqual(rc, 0)

    def test_the_vendored_module_imports(self):
        vendor.vendor(self.tmp, "tool_axi", self.ref)
        r = subprocess.run([sys.executable, "-c", "from tool_axi.axi import toon; print(toon('t', ['a'], []))"],
                           cwd=self.tmp, capture_output=True, text=True)
        self.assertEqual(r.stdout, "t[0]{a}: (none)\n", r.stderr)

    def test_refuses_to_vendor_into_a_non_package(self):
        with self.assertRaises(SystemExit):
            vendor.vendor(self.tmp, "missing_pkg", self.ref)


class RefusesAnUntaggedCheckout(unittest.TestCase):
    def test_outside_a_git_checkout_there_is_no_ref(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(vendor.checkout_ref(pathlib.Path(d)))

    def test_main_refuses_without_the_matching_tag(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "p").mkdir()
            (pathlib.Path(d) / "p" / "__init__.py").write_text("")
            real = vendor.checkout_ref
            vendor.checkout_ref = lambda repo=None: None
            try:
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    rc = vendor.main([d, "p"])
            finally:
                vendor.checkout_ref = real
            self.assertEqual(rc, 1)
            self.assertIn("refusing to vendor", err.getvalue())
            self.assertFalse((pathlib.Path(d) / "p" / "axi.py").exists())


if __name__ == "__main__":
    unittest.main()
