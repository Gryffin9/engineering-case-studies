"""Original synthetic geometry fixture. No private assets or detector rules."""
from itertools import combinations


def scenes():
    broken = [
        dict(id='slot-a', label='Aster · Slot A', x=-12, y=35, w=165, h=52),
        dict(id='slot-b', label='Birch · Slot B', x=130, y=70, w=165, h=52),
        dict(id='slot-c', label='Cedar · Slot C', x=245, y=146, w=145, h=52),
        dict(id='caption', label='Each task gets one slot', x=45, y=178, w=310, h=34),
    ]
    fixed = [
        dict(id='slot-a', label='Aster · Slot A', x=28, y=34, w=160, h=46),
        dict(id='slot-b', label='Birch · Slot B', x=212, y=34, w=160, h=46),
        dict(id='slot-c', label='Cedar · Slot C', x=120, y=102, w=160, h=46),
        dict(id='caption', label='Each task gets one slot', x=45, y=180, w=310, h=32),
    ]
    return broken, fixed


def findings(items):
    result = []
    for item in items:
        x, y, w, h = (item[k] for k in ('x', 'y', 'w', 'h'))
        if x < 0 or y < 0 or x + w > 400 or y + h > 240:
            result.append(dict(kind='off-canvas', ids=[item['id']]))
        if x < 20 or y < 20 or x + w > 380 or y + h > 220:
            result.append(dict(kind='safe-zone', ids=[item['id']]))
    for a, b in combinations(items, 2):
        if a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']:
            kind = 'caption-collision' if 'caption' in (a['id'], b['id']) else 'overlap'
            result.append(dict(kind=kind, ids=[a['id'], b['id']]))
    return result
