from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from temp_support import temporary_directory
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = ('SKILL.md', 'SKILL.zh.md')
API_MODEL = 'local-model-under-test'
API_KEY = 'local-test-secret-do-not-save'
PROMPT = '本地任务书全文\n请保留中英文内容。Return the supplied text.\n'
ANSWER = '完成\r\n本地接口原样交付。\n保留空格：  end  \r\n'
API_VARIABLES = ('FLEET_API_BASE', 'FLEET_API_MODEL', 'FLEET_API_KEY')


@contextmanager
def local_api(status=200, body=None, delay=0, drop=None):
    """Serve one configurable response on loopback without contacting a provider.

    drop='before_response' closes the connection without a status line;
    drop='mid_body' closes it after half of the promised body.
    """
    if body is None:
        body = {'choices': [{'message': {'content': ANSWER}}]}
    response = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode('utf-8')

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            self.server.requests.append({
                'path': self.path,
                'headers': dict(self.headers),
                'body': raw,
            })
            if delay:
                time.sleep(delay)
            if drop == 'before_response':
                return  # HTTP/1.0 handler: the server closes the socket after this.
            sent = response[:len(response) // 2] if drop == 'mid_body' else response
            try:
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(sent)
            except ConnectionError:
                # A timed-out subprocess has already closed its connection.
                pass

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = False  # server_close waits for slow response handlers.
    server.requests = []
    server.api_base = 'http://127.0.0.1:{}/v1'.format(server.server_address[1])
    worker = threading.Thread(target=server.serve_forever,
                              kwargs={'poll_interval': 0.01}, daemon=True)
    worker.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


class DispatchAPITests(unittest.TestCase):
    def api_runner(self, entry, timeout_seconds):
        text = (ROOT / 'skills/fleet-dispatch' / entry).read_text(encoding='utf-8')
        blocks = re.findall(r"```bash\npython -X utf8 - <<'PY'\n(.*?)\nPY\n```", text, re.S)
        blocks = [block for block in blocks if 'FLEET_API_BASE' in block]
        self.assertEqual(len(blocks), 1, entry + ': expected one documented API runner')
        code, count = re.subn(r'^timeout_seconds = .*$',
                              'timeout_seconds = ' + str(timeout_seconds),
                              blocks[0], flags=re.M)
        self.assertEqual(count, 1, entry + ': expected one editable timeout')
        return code

    def run_runner(self, entry, api_base, missing=(), timeout_seconds=2, existing=None,
                   api_format=None, reasoning=None):
        # Inherit OS essentials only: real credentials and proxy settings never enter
        # the child environment. NO_PROXY also avoids platform proxy discovery.
        essentials = ('SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP',
                      'HOME', 'USERPROFILE', 'LANG', 'LC_ALL')
        environment = {name: os.environ[name] for name in essentials if name in os.environ}
        environment.update({
            'NO_PROXY': '127.0.0.1,localhost',
            'FLEET_API_BASE': api_base,
            'FLEET_API_MODEL': API_MODEL,
            'FLEET_API_KEY': API_KEY,
        })
        if api_format is not None:
            environment['FLEET_API_FORMAT'] = api_format
        if reasoning is not None:
            environment['FLEET_API_REASONING'] = reasoning
        for name in missing:
            environment.pop(name, None)
        with temporary_directory(prefix='fleet-api-') as directory:
            base = Path(directory)
            briefs = base / ('fleet/task-briefs' if entry == 'SKILL.md' else 'fleet/任务书')
            deliveries = base / ('fleet/deliveries' if entry == 'SKILL.md' else 'fleet/交付')
            briefs.mkdir(parents=True)
            (briefs / '02.md').write_text(PROMPT, encoding='utf-8')
            if existing:
                deliveries.mkdir(parents=True)
                for name, content in existing.items():
                    (deliveries / name).write_text(content, encoding='utf-8')
            run = subprocess.run(
                [sys.executable, '-I', '-X', 'utf8', '-B', '-c',
                 self.api_runner(entry, timeout_seconds)],
                cwd=base, env=environment, capture_output=True,
                text=True, encoding='utf-8', timeout=10,
            )
            files = {path.name: path.read_bytes().decode('utf-8')
                     for path in deliveries.iterdir() if path.is_file()}
            for content in (run.stdout, run.stderr, *files.values()):
                self.assertNotIn(API_KEY, content, 'the API key escaped into output')
            return run, files

    def test_success_posts_full_brief_and_preserves_response(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry), local_api() as server:
                run, files = self.run_runner(entry, server.api_base)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(set(files), {'02.md', '02.log'})
                self.assertEqual(files['02.md'], ANSWER)
                self.assertIn('200', files['02.log'])
                self.assertEqual(len(server.requests), 1)
                request = server.requests[0]
                self.assertEqual(request['path'], '/v1/chat/completions')
                self.assertEqual(request['headers'].get('Authorization'), 'Bearer ' + API_KEY)
                self.assertEqual(request['headers'].get('Content-Type'), 'application/json')
                self.assertEqual(json.loads(request['body']), {
                    'model': API_MODEL,
                    'messages': [{'role': 'user', 'content': PROMPT}],
                })

    def test_reasoning_level_is_sent_and_logged_as_requested(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry), local_api() as server:
                run, files = self.run_runner(entry, server.api_base, reasoning=' \t high ')
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(files['02.md'], ANSWER)
                self.assertEqual(len(server.requests), 1)
                self.assertEqual(json.loads(server.requests[0]['body']), {
                    'model': API_MODEL,
                    'messages': [{'role': 'user', 'content': PROMPT}],
                    'reasoning_effort': 'high',
                })
                self.assertIn('high', files['02.log'])
                self.assertIn('server use unverified' if entry == 'SKILL.md'
                              else '服务端采用情况未核实', files['02.log'])

    def test_blank_reasoning_preserves_default_request_for_both_formats(self):
        for entry in ENTRIES:
            for api_format in (None, 'anthropic'):
                body = ({'content': [{'type': 'text', 'text': ANSWER}]}
                        if api_format == 'anthropic' else None)
                with self.subTest(entry=entry, api_format=api_format), local_api(body=body) as server:
                    run, files = self.run_runner(entry, server.api_base, api_format=api_format)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    default_request = server.requests[0]
                    for reasoning in ('', ' \t '):
                        with self.subTest(reasoning=reasoning):
                            run, files = self.run_runner(entry, server.api_base,
                                                         api_format=api_format, reasoning=reasoning)
                            self.assertEqual(run.returncode, 0, run.stderr)
                            self.assertEqual(files['02.md'], ANSWER)
                            self.assertEqual(server.requests[-1], default_request)

    def test_anthropic_reasoning_is_blocked_before_request(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry), local_api() as server:
                run, files = self.run_runner(entry, server.api_base,
                                             api_format='anthropic', reasoning='high')
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(files['02.md'], '')
                self.assertIn('Blocked:', files['02.log'])
                self.assertIn('FLEET_API_REASONING', files['02.log'])
                self.assertEqual(server.requests, [])

    def test_http_error_exits_one_and_redacts_key_in_error_body(self):
        body = {'error': {'message': 'refused credential ' + API_KEY}}
        for entry in ENTRIES:
            with self.subTest(entry=entry), local_api(status=500, body=body) as server:
                run, files = self.run_runner(entry, server.api_base)
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(files['02.md'], '')
                self.assertIn('500', files['02.log'])
                self.assertIn('refused credential ***', files['02.log'])

    def test_empty_response_exits_one_with_localized_error(self):
        errors = {
            'SKILL.md': 'the response is empty; reasoning may have used up the output limit',
            'SKILL.zh.md': '回答是空的；可能是思考用完了输出上限',
        }
        for entry in ENTRIES:
            for content in ('', ' \t\r\n '):
                body = {'choices': [{'finish_reason': 'length', 'message': {'content': content}}]}
                with self.subTest(entry=entry, content=content), local_api(body=body) as server:
                    run, files = self.run_runner(entry, server.api_base)
                    self.assertEqual(run.returncode, 1, run.stderr)
                    self.assertEqual(files['02.md'], '')
                    self.assertIn(errors[entry], files['02.log'])
                    self.assertIn('finish_reason: length', files['02.log'])

    def test_success_logs_finish_reason_or_none_when_missing(self):
        for entry in ENTRIES:
            for reason in ('stop', None):
                choice = {'message': {'content': ANSWER}}
                if reason is not None:
                    choice['finish_reason'] = reason
                body = {'choices': [choice]}
                with self.subTest(entry=entry, reason=reason), local_api(body=body) as server:
                    run, files = self.run_runner(entry, server.api_base)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(files['02.md'], ANSWER)
                    self.assertIn('finish_reason: ' + str(reason), files['02.log'])

    def test_timeout_is_blocked_with_localized_message(self):
        for entry, timeout_text in (('SKILL.md', 'timed out'), ('SKILL.zh.md', '超时')):
            with self.subTest(entry=entry), local_api(delay=0.5) as server:
                run, files = self.run_runner(entry, server.api_base, timeout_seconds=0.1)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(files['02.md'], '')
                self.assertIn('Blocked:', files['02.log'])
                self.assertIn(timeout_text, files['02.log'])

    def test_missing_environment_reports_names_without_values(self):
        for entry in ENTRIES:
            for missing in API_VARIABLES:
                with self.subTest(entry=entry, missing=missing), local_api() as server:
                    run, files = self.run_runner(entry, server.api_base, missing=(missing,))
                    self.assertEqual(run.returncode, 2, run.stderr)
                    self.assertEqual(files['02.md'], '')
                    log = files['02.log']
                    self.assertIn('Blocked:', log)
                    self.assertIn(missing, log)
                    for present in set(API_VARIABLES) - {missing}:
                        self.assertNotIn(present, log)
                    for value in (server.api_base, API_MODEL, API_KEY):
                        self.assertNotIn(value, log)
                    self.assertEqual(server.requests, [])

    def test_invalid_json_and_response_shapes_exit_one(self):
        invalid = (
            ('invalid-json', b'{"choices":'),
            ('missing-choice', {'choices': []}),
            ('non-object-choice', {'choices': [None]}),
            ('non-text-content', {'choices': [{'message': {'content': ['not text']}}]}),
        )
        for entry in ENTRIES:
            for name, body in invalid:
                with self.subTest(entry=entry, response=name), local_api(body=body) as server:
                    run, files = self.run_runner(entry, server.api_base)
                    self.assertEqual(run.returncode, 1, run.stderr)
                    self.assertEqual(files['02.md'], '')
                    self.assertIn('200', files['02.log'])
                    self.assertTrue(files['02.log'].strip())

    def test_unreachable_api_is_blocked(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry), socket.socket() as reserved:
                # Reserve an unused loopback port without listening, avoiding a
                # close-and-rebind race while the subprocess checks connection failure.
                reserved.bind(('127.0.0.1', 0))
                api_base = 'http://127.0.0.1:{}/v1'.format(reserved.getsockname()[1])
                run, files = self.run_runner(entry, api_base)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(files['02.md'], '')
                self.assertIn('Blocked:', files['02.log'])

    def test_dropped_connection_is_blocked_without_traceback(self):
        drops = (('before_response', 'RemoteDisconnected'), ('mid_body', 'IncompleteRead'))
        for entry in ENTRIES:
            for drop, error_name in drops:
                with self.subTest(entry=entry, drop=drop), local_api(drop=drop) as server:
                    run, files = self.run_runner(entry, server.api_base)
                    self.assertEqual(run.returncode, 2, run.stderr)
                    self.assertNotIn('Traceback', run.stderr)
                    self.assertEqual(files['02.md'], '')
                    self.assertIn('Blocked:', files['02.log'])
                    self.assertIn(error_name, files['02.log'])

    def test_existing_delivery_and_log_are_never_overwritten(self):
        for entry in ENTRIES:
            for name in ('02.md', '02.log'):
                with self.subTest(entry=entry, existing=name), local_api() as server:
                    original = 'Existing accepted file: ' + name
                    run, files = self.run_runner(entry, server.api_base, existing={name: original})
                    self.assertNotEqual(run.returncode, 0)
                    self.assertEqual(files[name], original)
                    self.assertEqual(server.requests, [])

    def test_key_echoed_in_successful_response_is_not_saved(self):
        body = {'choices': [{'message': {'content': 'echoed credential ' + API_KEY}}]}
        for entry in ENTRIES:
            with self.subTest(entry=entry), local_api(body=body) as server:
                run, files = self.run_runner(entry, server.api_base)
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(files['02.md'], '')
                self.assertTrue(files['02.log'].strip())

    def test_anthropic_success_posts_full_brief_and_joins_text_blocks(self):
        midpoint = len(ANSWER) // 2
        body = {
            'content': [
                {'type': 'thinking', 'thinking': ''},
                {'type': 'text', 'text': ANSWER[:midpoint]},
                {'type': 'text', 'text': ANSWER[midpoint:]},
            ],
            'stop_reason': 'end_turn',
        }
        for entry in ENTRIES:
            for api_format in ('anthropic', ' \tAnThRoPiC '):
                with self.subTest(entry=entry, api_format=api_format), local_api(body=body) as server:
                    run, files = self.run_runner(entry, server.api_base, api_format=api_format)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(set(files), {'02.md', '02.log'})
                    self.assertEqual(files['02.md'].encode('utf-8'), ANSWER.encode('utf-8'))
                    self.assertIn('HTTP 200', files['02.log'])
                    self.assertIn('stop_reason: end_turn', files['02.log'])
                    self.assertEqual(len(server.requests), 1)
                    request = server.requests[0]
                    self.assertEqual(request['path'], '/v1/messages')
                    headers = {name.lower(): value for name, value in request['headers'].items()}
                    self.assertEqual(headers.get('x-api-key'), API_KEY)
                    self.assertEqual(headers.get('anthropic-version'), '2023-06-01')
                    self.assertEqual(headers.get('content-type'), 'application/json')
                    self.assertNotIn('authorization', headers)
                    payload = json.loads(request['body'])
                    self.assertEqual(payload['model'], API_MODEL)
                    self.assertEqual(payload['messages'], [{'role': 'user', 'content': PROMPT}])
                    self.assertIs(type(payload['max_tokens']), int)
                    self.assertGreater(payload['max_tokens'], 0)
                    self.assertEqual(set(payload), {'model', 'max_tokens', 'messages'})

    def test_anthropic_empty_response_exits_one_with_localized_error(self):
        errors = {
            'SKILL.md': 'the response is empty; reasoning may have used up the output limit',
            'SKILL.zh.md': '回答是空的；可能是思考用完了输出上限',
        }
        responses = (
            ('thinking-only', [{'type': 'thinking', 'thinking': ''}]),
            ('no-blocks', []),
            ('empty-text', [{'type': 'text', 'text': ''}]),
            ('whitespace-text', [{'type': 'text', 'text': ' \t\r\n '}]),
        )
        for entry in ENTRIES:
            for name, content in responses:
                body = {'content': content, 'stop_reason': 'max_tokens'}
                with self.subTest(entry=entry, response=name), local_api(body=body) as server:
                    run, files = self.run_runner(entry, server.api_base, api_format='anthropic')
                    self.assertEqual(run.returncode, 1, run.stderr)
                    self.assertEqual(files['02.md'], '')
                    self.assertIn(errors[entry], files['02.log'])
                    self.assertIn('stop_reason: max_tokens', files['02.log'])

    def test_anthropic_invalid_response_shapes_exit_one(self):
        invalid = (
            ('non-list-content', {'content': {}}),
            ('non-object-block', {'content': [None]}),
            ('non-text-value', {'content': [{'type': 'text', 'text': 42}]}),
            ('missing-text', {'content': [{'type': 'text'}]}),
        )
        for entry in ENTRIES:
            for name, body in invalid:
                with self.subTest(entry=entry, response=name), local_api(body=body) as server:
                    run, files = self.run_runner(entry, server.api_base, api_format='anthropic')
                    self.assertEqual(run.returncode, 1, run.stderr)
                    self.assertEqual(files['02.md'], '')
                    self.assertIn('HTTP 200', files['02.log'])
                    self.assertIn('Error:' if entry == 'SKILL.md' else '错误：', files['02.log'])
                    self.assertNotIn('Traceback', run.stderr)

    def test_invalid_api_format_is_blocked_before_request(self):
        errors = {
            'SKILL.md': 'Blocked: FLEET_API_FORMAT must be openai or anthropic',
            'SKILL.zh.md': 'Blocked: FLEET_API_FORMAT 只能是 openai 或 anthropic',
        }
        for entry in ENTRIES:
            for api_format in ('gemini', ' \tGeMiNi '):
                with self.subTest(entry=entry, api_format=api_format), local_api() as server:
                    run, files = self.run_runner(entry, server.api_base, api_format=api_format)
                    self.assertEqual(run.returncode, 2, run.stderr)
                    self.assertEqual(files['02.md'], '')
                    self.assertIn(errors[entry], files['02.log'])
                    self.assertEqual(server.requests, [])

    def test_explicit_openai_and_empty_format_preserve_default_request(self):
        for entry in ENTRIES:
            with local_api() as server:
                default_run, default_files = self.run_runner(entry, server.api_base)
                self.assertEqual(default_run.returncode, 0, default_run.stderr)
                self.assertEqual(default_files['02.md'], ANSWER)
                default_request = server.requests[0]
                for api_format in ('openai', '', ' \t ', ' \tOpEnAi '):
                    with self.subTest(entry=entry, api_format=api_format):
                        run, files = self.run_runner(entry, server.api_base, api_format=api_format)
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(files['02.md'], ANSWER)
                        request = server.requests[-1]
                        self.assertEqual(request['path'], '/v1/chat/completions')
                        self.assertEqual(request, default_request)

    def test_anthropic_http_error_and_invalid_json_reuse_error_handling(self):
        responses = (
            ('http-error', 500, {'error': {'message': 'refused credential ' + API_KEY}}),
            ('invalid-json', 200, b'{"content":'),
        )
        for entry in ENTRIES:
            for name, status, body in responses:
                with self.subTest(entry=entry, response=name), local_api(status=status, body=body) as server:
                    run, files = self.run_runner(entry, server.api_base, api_format='anthropic')
                    self.assertEqual(run.returncode, 1, run.stderr)
                    self.assertEqual(files['02.md'], '')
                    self.assertIn('HTTP ' + str(status), files['02.log'])
                    self.assertIn('Error:' if entry == 'SKILL.md' else '错误：', files['02.log'])
                    if name == 'http-error':
                        self.assertIn('refused credential ***', files['02.log'])

    def test_anthropic_timeout_and_dropped_connection_are_blocked(self):
        cases = (
            ('timeout', {'delay': 0.5}, 0.1),
            ('before-response', {'drop': 'before_response'}, 2),
            ('mid-body', {'drop': 'mid_body'}, 2),
        )
        for entry in ENTRIES:
            for name, options, timeout_seconds in cases:
                with self.subTest(entry=entry, failure=name), local_api(**options) as server:
                    run, files = self.run_runner(entry, server.api_base,
                                                 timeout_seconds=timeout_seconds,
                                                 api_format='anthropic')
                    self.assertEqual(run.returncode, 2, run.stderr)
                    self.assertEqual(files['02.md'], '')
                    self.assertIn('Blocked:', files['02.log'])
                    self.assertNotIn('Traceback', run.stderr)

    def test_anthropic_unreachable_api_is_blocked(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry), socket.socket() as reserved:
                reserved.bind(('127.0.0.1', 0))
                api_base = 'http://127.0.0.1:{}/v1'.format(reserved.getsockname()[1])
                run, files = self.run_runner(entry, api_base, api_format='anthropic')
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(files['02.md'], '')
                self.assertIn('Blocked:', files['02.log'])

    def test_anthropic_existing_delivery_and_log_are_never_overwritten(self):
        for entry in ENTRIES:
            for name in ('02.md', '02.log'):
                with self.subTest(entry=entry, existing=name), local_api() as server:
                    original = 'Existing accepted file: ' + name
                    run, files = self.run_runner(entry, server.api_base,
                                                 existing={name: original}, api_format='anthropic')
                    self.assertNotEqual(run.returncode, 0)
                    self.assertEqual(files[name], original)
                    self.assertEqual(server.requests, [])

    def test_anthropic_key_split_between_text_blocks_is_not_saved(self):
        midpoint = len(API_KEY) // 2
        body = {'content': [
            {'type': 'text', 'text': 'echoed credential ' + API_KEY[:midpoint]},
            {'type': 'text', 'text': API_KEY[midpoint:]},
        ]}
        for entry in ENTRIES:
            with self.subTest(entry=entry), local_api(body=body) as server:
                run, files = self.run_runner(entry, server.api_base, api_format='anthropic')
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(files['02.md'], '')
                self.assertIn('Error:' if entry == 'SKILL.md' else '错误：', files['02.log'])


if __name__ == '__main__':
    unittest.main()
