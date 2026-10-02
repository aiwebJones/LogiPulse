import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import run
from src import analyzer, collector, reporter


class ReportingTests(unittest.TestCase):
    def test_missing_key_stops_before_collection_or_publication(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['run.py']), \
                patch.object(run, 'collect_all', new_callable=AsyncMock) as collect, \
                patch.object(run, 'save_reports') as save:
            with self.assertRaises(SystemExit) as result:
                asyncio.run(run.main())
            self.assertEqual(result.exception.code, 1)
            collect.assert_not_called()
            save.assert_not_called()

    def test_empty_collection_does_not_call_model_or_publish(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}), \
                patch('sys.argv', ['run.py']), \
                patch.object(run, 'collect_all', new_callable=AsyncMock, return_value=[]), \
                patch.object(run, 'save_raw'), patch.object(run, 'analyze_items') as analyze, \
                patch.object(run, 'save_reports') as save:
            with self.assertRaises(SystemExit):
                asyncio.run(run.main())
            analyze.assert_not_called()
            save.assert_not_called()

    def test_source_count_is_distinct_sources_not_items(self):
        published = datetime.now(timezone.utc).isoformat()
        items = [{'source': source, 'published': published} for source in ['A', 'A', 'B']]
        items.append({'source': 'Undated web', 'published': None})
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}), \
                patch('sys.argv', ['run.py']), \
                patch.object(run, 'collect_all', new_callable=AsyncMock, return_value=items), \
                patch.object(run, 'save_raw'), \
                patch.object(run, 'analyze_items', return_value=run.DEMO_ANALYSIS), \
                patch.object(run, 'save_reports', return_value=('zh', 'en')) as save:
            asyncio.run(run.main())
            save.assert_called_once_with(run.DEMO_ANALYSIS, 'reports', source_count=2)

    def test_undated_or_stale_collection_does_not_call_model_or_publish(self):
        old = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        items = [{'source': 'Web', 'published': None}, {'source': 'RSS', 'published': old}]
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}), \
                patch('sys.argv', ['run.py']), \
                patch.object(run, 'collect_all', new_callable=AsyncMock, return_value=items), \
                patch.object(run, 'save_raw') as raw, \
                patch.object(run, 'analyze_items') as analyze, patch.object(run, 'save_reports') as save:
            with self.assertRaises(SystemExit):
                asyncio.run(run.main())
            raw.assert_called_once_with(items)
            analyze.assert_not_called()
            save.assert_not_called()

    def test_collect_only_preserves_undated_raw_items(self):
        items = [{'source': 'Web', 'published': None}]
        with patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['run.py', '--collect-only']), \
                patch.object(run, 'collect_all', new_callable=AsyncMock, return_value=items), \
                patch.object(run, 'save_raw') as raw, patch.object(run, 'filter_recent_items') as recent, \
                patch.object(run, 'analyze_items') as analyze:
            asyncio.run(run.main())
            raw.assert_called_once_with(items)
            recent.assert_not_called()
            analyze.assert_not_called()

    def test_recent_filter_handles_offsets_and_excludes_unknown_stale_and_future(self):
        now = datetime(2026, 10, 2, 8, tzinfo=timezone.utc)
        items = [
            {'published': '2026-10-02T15:00:00+08:00'},
            {'published': '2026-09-30T08:00:00Z'},
            {'published': '2026-10-02T07:00:00'},
            {'published': None, 'updated': now.isoformat()},
            {'published': 'invalid'},
            {'published': '2026-09-30T07:59:59Z'},
            {'published': '2026-10-02T08:00:01Z'},
        ]
        with patch.object(collector, 'datetime', wraps=datetime) as clock:
            clock.now.return_value = now
            self.assertEqual(collector.filter_recent_items(items), items[:3])
        self.assertEqual(len(items), 7)

    def test_rss_updated_time_is_not_promoted_to_publication_time(self):
        updated = datetime.now(timezone.utc).isoformat()
        feed = f'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Test</title>
            <entry><id>https://example.com/old</id><title>Updated old article</title>
            <updated>{updated}</updated><link href="https://example.com/old"/></entry></feed>'''
        with patch.object(collector, 'fetch_url', new_callable=AsyncMock, return_value=feed):
            items = asyncio.run(collector.collect_rss(None, {'name': 'Test', 'url': 'https://example.com/feed'}))
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0]['published'])
        self.assertIsNotNone(items[0]['updated'])
        self.assertEqual(collector.filter_recent_items(items), [])

    def test_dry_run_uses_separate_directory(self):
        with patch('sys.argv', ['run.py', '--dry-run']), \
                patch.object(run, 'collect_all', new_callable=AsyncMock) as collect, \
                patch.object(run, 'save_reports', return_value=('zh', 'en')) as save:
            asyncio.run(run.main())
            save.assert_called_once_with(run.DEMO_ANALYSIS, 'demo-reports', source_count=0, demo=True)
            collect.assert_not_called()

    def test_demo_files_are_labeled(self):
        with tempfile.TemporaryDirectory() as directory:
            zh, en = reporter.save_reports(run.DEMO_ANALYSIS, directory, source_count=0, demo=True)
            self.assertIn('示例报告', zh.read_text())
            self.assertIn('DEMO:', en.read_text())
            self.assertNotIn('120+', zh.read_text())

    def test_shanghai_date_and_time(self):
        utc = datetime(2026, 10, 1, 20, 30, tzinfo=timezone.utc)
        with patch.object(reporter, 'datetime') as clock:
            clock.now.side_effect = lambda tz: utc.astimezone(tz)
            text = reporter.render_zh(run.DEMO_ANALYSIS, source_count=2)
        self.assertIn('2026-10-02', text)
        self.assertIn('04:30', text)
        self.assertIn('信息源 2 个', text)

    def test_model_and_text_blocks(self):
        response = SimpleNamespace(content=[SimpleNamespace(type='thinking'),
            SimpleNamespace(type='text', text='{"date":"2026-10-02"}')], stop_reason='end_turn')
        with patch.dict(os.environ, {'ANTHROPIC_MODEL': 'configured-model'}), \
                patch.object(analyzer, 'create_client') as client:
            client.return_value.messages.create.return_value = response
            result = analyzer.analyze_items.__wrapped__([{'source': 'A', 'published': '2026-10-01T12:00:00+00:00'}])
            self.assertEqual(result['date'], '2026-10-02')
            self.assertEqual(client.return_value.messages.create.call_args.kwargs['model'], 'configured-model')
            prompt = client.return_value.messages.create.call_args.kwargs['messages'][0]['content']
            self.assertIn('"published": "2026-10-01T12:00:00+00:00"', prompt)

    def test_truncated_model_result_is_rejected(self):
        response = SimpleNamespace(content=[SimpleNamespace(type='text', text='{}')], stop_reason='max_tokens')
        with patch.object(analyzer, 'create_client') as client:
            client.return_value.messages.create.return_value = response
            with self.assertRaisesRegex(ValueError, 'truncated'):
                analyzer.analyze_items.__wrapped__([{'source': 'A'}])


if __name__ == '__main__':
    unittest.main()
