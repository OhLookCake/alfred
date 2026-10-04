import contextlib
import io
import json
import unittest
from unittest.mock import patch
import videos


def page(cards, chip='Latest'):
    return {'contents': {'twoColumnBrowseResultsRenderer': {'tabs': [
        {'tabRenderer': {'title': 'Home', 'content': {}}},
        {'tabRenderer': {'selected': True, 'title': 'Videos', 'content': {'richGridRenderer': {
            'header': {'chipBarViewModel': {'chips': [{'chipViewModel': {'text': chip, 'selected': True}}]}},
            'contents': [{'richItemRenderer': {'content': card}} for card in cards]}}}}]}}}


def card(number):
    return {'lockupViewModel': {'contentId': 'video%06d' % number, 'contentType': 'LOCKUP_CONTENT_TYPE_VIDEO',
        'metadata': {'lockupMetadataViewModel': {'title': {'content': 'Video %d' % number}}}}}


class VideoTests(unittest.TestCase):
    def test_newest_ten_in_order(self):
        items = videos.video_items(page([card(i) for i in range(15)]))
        self.assertEqual([i['title'] for i in items], ['Video %d' % i for i in range(10)])
        self.assertEqual(items[0]['arg'], 'https://www.youtube.com/watch?v=video000000')
        self.assertTrue(all(i['valid'] for i in items))

    def test_duplicates_and_nonvideo_cards_excluded(self):
        playlist = card(2)
        playlist['lockupViewModel']['contentType'] = 'LOCKUP_CONTENT_TYPE_PLAYLIST'
        items = videos.video_items(page([card(0), card(0), playlist, card(1)]))
        self.assertEqual(len(items), 2)

    def test_legacy_renderer(self):
        items = videos.video_items(page([{'videoRenderer': {'videoId': 'abcdefghijk',
            'title': {'runs': [{'text': 'Legacy title'}]}, 'publishedTimeText': {'simpleText': '1 day ago'}}}]))
        self.assertEqual(items[0]['title'], 'Legacy title')
        self.assertEqual(items[0]['subtitle'], '1 day ago')

    def test_wrong_order_and_empty_page_fail(self):
        for data in (page([card(0)], 'Popular'), page([])):
            with self.assertRaises(ValueError):
                videos.video_items(data)

    def test_embedded_data_and_consent_page(self):
        data = page([card(0)])
        self.assertEqual(videos.initial_data('<script>var ytInitialData = ' + json.dumps(data) + ';</script>'), data)
        with self.assertRaises(ValueError):
            videos.initial_data('<html>Consent required</html>')

    def test_failure_offers_channel(self):
        with patch.object(videos, 'fetch_items', side_effect=OSError('offline')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                videos.main()
        self.assertEqual(json.loads(output.getvalue())['items'][0]['arg'], videos.CHANNEL)


if __name__ == '__main__':
    unittest.main()
