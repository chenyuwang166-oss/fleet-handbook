from pathlib import Path
import re
import subprocess
import sys
from temp_support import temporary_directory
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DispatchExampleTests(unittest.TestCase):
    def test_documented_runner_success_failure_and_timeout(self):
        for entry, timeout_text in (('SKILL.md', 'timed out'), ('SKILL.zh.md', '超时')):
            with self.subTest(entry=entry):
                self.check_runner(entry, timeout_text)

    def check_runner(self, entry, timeout_text):
        text = (ROOT / 'skills/fleet-dispatch' / entry).read_text(encoding='utf-8')
        block = re.search(r"```bash\npython -X utf8 - <<'PY'\n(.*?)\nPY\n```", text, re.S)[1]
        scenarios = [('success', "print('完成'); print('看到的：本地桩输出')", 0),
                     ('failure', 'import sys; sys.exit(3)', 3),
                     ('timeout', 'import time; time.sleep(2)', 2)]
        for name, stub, expected in scenarios:
            with self.subTest(name=name), temporary_directory() as directory:
                base = Path(directory)
                briefs = 'fleet/task-briefs' if entry == 'SKILL.md' else 'fleet/任务书'
                deliveries = 'fleet/deliveries' if entry == 'SKILL.md' else 'fleet/交付'
                (base / briefs).mkdir(parents=True)
                (base / briefs / '01.md').write_text('本地桩任务', encoding='utf-8')
                command = [sys.executable, '-X', 'utf8', '-c', stub]
                code = re.sub(r'^command = .*$', lambda m: 'command = ' + repr(command), block, flags=re.M)
                code = re.sub(r'^timeout_seconds = .*$',
                              'timeout_seconds = ' + ('0.2' if name == 'timeout' else '5'), code, flags=re.M)
                run = subprocess.run([sys.executable, '-X', 'utf8', '-c', code], cwd=base,
                                     capture_output=True, timeout=10)
                self.assertEqual(run.returncode, expected, run.stderr.decode('utf-8'))
                if name == 'success':
                    self.assertTrue((base / deliveries / '01.md').read_text(encoding='utf-8').startswith('完成'))
                if name == 'timeout':
                    self.assertIn(timeout_text, (base / deliveries / '01.log').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
