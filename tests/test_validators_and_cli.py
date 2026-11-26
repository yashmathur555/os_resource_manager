import os, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from osim import bashbridge, validators
from osim.errors import BashToolError, ValidationError


def tmp(content, suffix=".csv"):
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False)
    f.write(content); f.close()
    return f.name


class TestValidators(unittest.TestCase):
    def test_valid_csv(self):
        p = tmp("# c\npid,arrival,burst\nA,0,3\nB,1,2\n")
        self.assertEqual(len(validators.load_processes(p)), 2)

    def test_missing_file(self):
        with self.assertRaises(ValidationError):
            validators.load_processes("/no/such/file.csv")

    def test_empty_file(self):
        with self.assertRaises(ValidationError):
            validators.load_processes(tmp(""))

    def test_bad_header_and_values(self):
        with self.assertRaises(ValidationError):
            validators.load_processes(tmp("a,b,c\n1,2,3\n"))
        with self.assertRaises(ValidationError):
            validators.load_processes(tmp("pid,arrival,burst\nA,x,3\n"))
        with self.assertRaises(ValidationError):
            validators.load_processes(tmp("pid,arrival,burst\nA,0,-3\n"))

    def test_reference_string_parsing(self):
        self.assertEqual(validators.parse_reference_string("1, 2 3"), [1, 2, 3])
        for bad in ("", "1 a 2", "-4"):
            with self.assertRaises(ValidationError):
                validators.parse_reference_string(bad)

    def test_bad_json(self):
        with self.assertRaises(ValidationError):
            validators.load_json(tmp("{not json", ".json"))

    def test_alloc_ops_errors(self):
        with self.assertRaises(ValidationError):
            validators.load_alloc_ops(tmp("alloc A 10\n", ".txt"))        # no memory line
        with self.assertRaises(ValidationError):
            validators.load_alloc_ops(tmp("memory 100\nbogus\n", ".txt"))

    def test_parse_int_bounds(self):
        self.assertEqual(validators.parse_int("5", "x", 5, 5), 5)
        with self.assertRaises(ValidationError):
            validators.parse_int("5.5", "x")


class TestBashIntegration(unittest.TestCase):
    def test_snapshot_keys(self):
        snap = bashbridge.system_snapshot()
        for k in ("cpus", "mem_total_kb", "page_size_bytes"):
            self.assertIn(k, snap)

    def test_generate_workload_reproducible(self):
        a, b = tempfile.mktemp(".csv"), tempfile.mktemp(".csv")
        bashbridge.generate_workload(6, 11, a); bashbridge.generate_workload(6, 11, b)
        with open(a) as fa, open(b) as fb:
            self.assertEqual(fa.read(), fb.read())
        self.assertEqual(len(validators.load_processes(a)), 6)

    def test_generate_workload_rejects_bad_args(self):
        with self.assertRaises(BashToolError):
            bashbridge.generate_workload(0, 1, tempfile.mktemp(".csv"))

    def test_missing_script(self):
        with self.assertRaises(BashToolError):
            bashbridge.run_script("does_not_exist.sh")


class TestCLI(unittest.TestCase):
    def run_main(self, text):
        return subprocess.run([sys.executable, os.path.join(ROOT, "main.py")], input=text,
                              capture_output=True, text=True, timeout=60, cwd=ROOT)

    def test_exit(self):
        r = self.run_main("0\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Goodbye", r.stdout)

    def test_invalid_option_does_not_crash(self):
        r = self.run_main("abc\n99\n0\n")
        self.assertIn("Invalid option", r.stdout)
        self.assertEqual(r.returncode, 0)

    def test_bad_file_reports_error_and_continues(self):
        r = self.run_main("1\ndata/missing.csv\n\n\n0\n")
        self.assertIn("[ERROR] File not found", r.stdout)
        self.assertIn("Goodbye", r.stdout)

    def test_eof_exits_cleanly(self):
        self.assertEqual(self.run_main("").returncode, 0)

    def test_scheduling_through_menu(self):
        r = self.run_main("1\n\nSRTF\n4\n0\n")
        self.assertIn("Avg waiting=6.5", r.stdout)


if __name__ == "__main__":
    unittest.main()
