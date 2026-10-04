#!/usr/bin/env python3
"""List the newest Pickleballtv uploads as Alfred Script Filter JSON."""
import json
import re
import sys
import urllib.error
import urllib.request

CHANNEL = 'https://www.youtube.com/@Pickleballtv/videos'


def text(value):
    if isinstance(value, str):
        return value
    return value.get('content') or value.get('simpleText') or ''.join(r.get('text', '') for r in value.get('runs', []))


def initial_data(html):
    match = re.search(r'(?:var\s+ytInitialData\s*=|window\["ytInitialData"\]\s*=|ytInitialData\s*=)\s*', html)
    if not match:
        raise ValueError('YouTube did not return its video list. Try again shortly.')
    return json.JSONDecoder().raw_decode(html[match.end():])[0]


def video_items(data):
    tabs = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
    selected = next((tab['tabRenderer'] for tab in tabs if tab.get('tabRenderer', {}).get('selected')), {})
    if selected.get('title') != 'Videos':
        raise ValueError('YouTube did not return the Videos tab.')
    grid = selected.get('content', {}).get('richGridRenderer', {})
    header = grid.get('header', {})
    chips = header.get('chipBarViewModel', {}).get('chips', [])
    if any(c.get('chipViewModel', {}).get('selected') and c['chipViewModel'].get('text') != 'Latest' for c in chips):
        raise ValueError('YouTube did not return the latest upload order.')
    items, seen = [], set()
    # Inspect only the selected tab's top-level video cards; exclude recommendations.
    for entry in grid.get('contents', []):
        content = entry.get('richItemRenderer', {}).get('content', {})
        if 'lockupViewModel' in content:
            video = content['lockupViewModel']
            if video.get('contentType') != 'LOCKUP_CONTENT_TYPE_VIDEO':
                continue
            video_id = video.get('contentId', '')
            metadata = video.get('metadata', {}).get('lockupMetadataViewModel', {})
            title = text(metadata.get('title', {}))
            rows = metadata.get('metadata', {}).get('contentMetadataViewModel', {}).get('metadataRows', [])
            subtitle = ' · '.join(text(part.get('text', {})) for row in rows for part in row.get('metadataParts', []))
        elif 'videoRenderer' in content:
            video = content['videoRenderer']
            video_id = video.get('videoId', '')
            title = text(video.get('title', {}))
            subtitle = ' · '.join(filter(None, [text(video.get('publishedTimeText', {})),
                                                 text(video.get('lengthText', {})), text(video.get('viewCountText', {}))]))
        else:
            continue
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id) or not title or video_id in seen:
            continue
        seen.add(video_id)
        url = 'https://www.youtube.com/watch?v=' + video_id
        items.append({'title': title, 'subtitle': subtitle or 'Open in your default browser',
                      'arg': url, 'valid': True, 'quicklookurl': url})
        if len(items) == 10:
            break
    if not items:
        raise ValueError('YouTube returned no uploads. Try again shortly.')
    return items


def fetch_items():
    request = urllib.request.Request(CHANNEL + '?hl=en&sort=dd', headers={
        'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'})
    with urllib.request.urlopen(request, timeout=12) as response:
        html = response.read().decode('utf-8')
    return video_items(initial_data(html))


def main():
    try:
        items = fetch_items()
    except (ValueError, KeyError, urllib.error.URLError, OSError) as error:
        print('Pickleballtv: %s' % error, file=sys.stderr)
        items = [{'title': 'Could not load Pickleballtv uploads',
                  'subtitle': 'Press Return to open the channel, or try pb again.',
                  'arg': CHANNEL, 'valid': True}]
    print(json.dumps({'items': items}, ensure_ascii=False))


if __name__ == '__main__':
    main()
