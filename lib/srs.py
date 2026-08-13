"""Spaced-repetition session logic aligned with vocabulary_trainer_multilist."""
import random
from datetime import date, datetime, timedelta

from lib import srs_store

LEVEL_INTERVALS = [0, 1, 2, 4, 7, 14, 30, 60]
DAY_RESET_HOUR = 4


def study_today(now=None):
    """Study-day date. Rolls over at 04:00 local time instead of midnight."""
    now = now or datetime.now()
    return (now - timedelta(hours=DAY_RESET_HOUR)).date()


def parse_list_words(en_list, zh_list, sen_list=None, sm=False):
    words = []
    for i, word in enumerate(en_list):
        item = {
            'word': word,
            'meaning': zh_list[i] if i < len(zh_list) else '',
            'example': '',
        }
        if sm and sen_list is not None and i < len(sen_list):
            item['example'] = sen_list[i]
        words.append(item)
    return words


def ensure_today_task(username, list_id, words, today=None):
    """Ensure progress rows and a pinned daily target for today."""
    today = today or study_today()
    today_iso = today.isoformat()
    progress = srs_store.ensure_progress_rows(username, list_id, words, today_iso)
    daily = srs_store.fetch_daily(username, list_id, today_iso)
    valid = {item['word'] for item in words}

    if daily is None:
        due = []
        for item in words:
            record = progress[item['word']]
            try:
                next_review = date.fromisoformat(record['next_review'])
            except (ValueError, TypeError):
                next_review = today
            if next_review <= today:
                due.append(item['word'])
        daily = {'target': due, 'done': [], 'retry': []}
        srs_store.save_daily(username, list_id, today_iso, daily)
    else:
        daily['target'] = [w for w in daily.get('target', []) if w in valid]
        daily['done'] = [w for w in daily.get('done', []) if w in valid]
        daily['retry'] = [w for w in daily.get('retry', []) if w in valid]
        srs_store.save_daily(username, list_id, today_iso, daily)

    return progress, daily


def remaining_names(daily):
    done = set(daily.get('done') or [])
    retry = set(daily.get('retry') or [])
    return [
        word for word in (daily.get('target') or [])
        if word not in done or word in retry
    ]


def remaining_words(words, daily):
    by_word = {item['word']: item for item in words}
    return [by_word[w] for w in remaining_names(daily) if w in by_word]


def choose_word(words, progress, daily, current_word=None):
    pool = remaining_words(words, daily)
    if not pool:
        return None

    retry = set(daily.get('retry') or [])
    weights = []
    for item in pool:
        record = progress.get(item['word']) or srs_store.default_record(study_today().isoformat())
        level = int(record.get('level', 0))
        wrong = int(record.get('wrong', 0))
        bonus = 6 if item['word'] in retry else 0
        weights.append(max(1, 9 - level + wrong * 0.5 + bonus))

    choice = random.choices(pool, weights=weights, k=1)[0]
    if current_word and len(pool) > 1:
        for _ in range(5):
            if choice['word'] != current_word:
                break
            choice = random.choices(pool, weights=weights, k=1)[0]
    return choice


def apply_rating(record, daily, rating, today=None):
    """Mutate progress record and daily state for know/dont. Returns updated record."""
    today = today or study_today()
    word = record.get('_word')  # optional; caller passes word separately for daily
    level = int(record.get('level', 0))
    record['seen'] = int(record.get('seen', 0)) + 1

    if rating == 'dont':
        record['level'] = 0
        record['next_review'] = today.isoformat()
        record['wrong'] = int(record.get('wrong', 0)) + 1
        if word:
            if word in daily['done']:
                daily['done'].remove(word)
            if word not in daily['retry']:
                daily['retry'].append(word)
    else:
        level = min(level + 1, len(LEVEL_INTERVALS) - 1)
        interval = LEVEL_INTERVALS[level]
        record['level'] = level
        record['next_review'] = (today + timedelta(days=interval)).isoformat()
        record['correct'] = int(record.get('correct', 0)) + 1
        if word:
            if word not in daily['done']:
                daily['done'].append(word)
            if word in daily['retry']:
                daily['retry'].remove(word)
    return record


def rate_word(username, list_id, words, word, rating, today=None):
    today = today or study_today()
    today_iso = today.isoformat()
    progress, daily = ensure_today_task(username, list_id, words, today)
    if word not in progress:
        progress[word] = srs_store.default_record(today_iso)

    record = dict(progress[word])
    record['_word'] = word
    apply_rating(record, daily, rating, today)
    record.pop('_word', None)

    srs_store.save_progress(username, list_id, word, record)
    srs_store.save_daily(username, list_id, today_iso, daily)
    progress[word] = record
    return progress, daily


def list_statistics(words, progress, daily):
    target = len(daily.get('target') or [])
    done = len(set(daily.get('done') or []) & set(daily.get('target') or []))
    retry = len(set(daily.get('retry') or []))
    mastered = sum(
        1 for item in words
        if int((progress.get(item['word']) or {}).get('level', 0)) >= 5
    )
    remaining = len(remaining_names(daily))
    return {
        'total': len(words),
        'target': target,
        'done': done,
        'retry': retry,
        'mastered': mastered,
        'remaining': remaining,
        'finished': remaining == 0,
    }


def card_payload(item, sm=False):
    if item is None:
        return None
    payload = {
        'word': item['word'],
        'meaning': item['meaning'],
        'example': item.get('example') or '',
    }
    return payload


def restart_today(username, list_id, words, today=None):
    today = today or study_today()
    today_iso = today.isoformat()
    progress = srs_store.ensure_progress_rows(username, list_id, words, today_iso)
    daily = {
        'target': [item['word'] for item in words],
        'done': [],
        'retry': [],
    }
    srs_store.save_daily(username, list_id, today_iso, daily)
    return progress, daily


def review_wrong(username, list_id, words, today=None):
    today = today or study_today()
    today_iso = today.isoformat()
    progress = srs_store.ensure_progress_rows(username, list_id, words, today_iso)
    wrong_words = [
        item['word'] for item in words
        if int((progress.get(item['word']) or {}).get('wrong', 0)) > 0
    ]
    if not wrong_words:
        return progress, None
    daily = {
        'target': list(dict.fromkeys(wrong_words)),
        'done': [],
        'retry': [],
    }
    srs_store.save_daily(username, list_id, today_iso, daily)
    return progress, daily


def session_bootstrap(username, list_id, words, current_word=None, today=None):
    progress, daily = ensure_today_task(username, list_id, words, today)
    choice = choose_word(words, progress, daily, current_word)
    stats = list_statistics(words, progress, daily)
    return {
        'card': card_payload(choice),
        'stats': stats,
        'daily': daily,
    }
