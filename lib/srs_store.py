"""MySQL helpers for Reciter spaced-repetition tables."""
import json

import mysql.connector

from lib.dbConnecter import connect_to_db


def _run(sql, params=None, fetch=False, dictionary=False):
    connection = connect_to_db()
    cursor = connection.cursor(dictionary=dictionary)
    try:
        cursor.execute(sql, params or ())
        if fetch:
            return cursor.fetchall()
        connection.commit()
        return cursor.rowcount
    except mysql.connector.Error as err:
        print('srs_store Error: %s' % err)
        raise
    finally:
        cursor.close()
        connection.close()


def default_record(today_iso):
    return {
        'level': 0,
        'next_review': today_iso,
        'seen': 0,
        'correct': 0,
        'wrong': 0,
    }


def fetch_progress_map(username, list_id):
    rows = _run(
        'SELECT word, level, next_review, seen, correct, wrong '
        'FROM word_progress WHERE username = %s AND list_id = %s;',
        (username, list_id),
        fetch=True,
        dictionary=True,
    ) or []
    out = {}
    for row in rows:
        next_review = row['next_review']
        if hasattr(next_review, 'isoformat'):
            next_review = next_review.isoformat()
        out[row['word']] = {
            'level': int(row['level'] or 0),
            'next_review': next_review,
            'seen': int(row['seen'] or 0),
            'correct': int(row['correct'] or 0),
            'wrong': int(row['wrong'] or 0),
        }
    return out


def ensure_progress_rows(username, list_id, words, today_iso):
    """Insert missing progress rows for every English word in the list."""
    existing = fetch_progress_map(username, list_id)
    for item in words:
        word = item['word']
        if word in existing:
            continue
        rec = default_record(today_iso)
        _run(
            'INSERT INTO word_progress '
            '(username, list_id, word, level, next_review, seen, correct, wrong) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s);',
            (username, list_id, word, rec['level'], rec['next_review'],
             rec['seen'], rec['correct'], rec['wrong']),
        )
        existing[word] = rec
    return existing


def save_progress(username, list_id, word, record):
    _run(
        'UPDATE word_progress SET level = %s, next_review = %s, seen = %s, '
        'correct = %s, wrong = %s '
        'WHERE username = %s AND list_id = %s AND word = %s;',
        (int(record['level']), record['next_review'], int(record['seen']),
         int(record['correct']), int(record['wrong']),
         username, list_id, word),
    )


def fetch_daily(username, list_id, day_iso):
    rows = _run(
        'SELECT target_json, done_json, retry_json FROM daily_task '
        'WHERE username = %s AND list_id = %s AND day = %s;',
        (username, list_id, day_iso),
        fetch=True,
        dictionary=True,
    )
    if not rows:
        return None
    row = rows[0]
    return {
        'target': json.loads(row['target_json'] or '[]'),
        'done': json.loads(row['done_json'] or '[]'),
        'retry': json.loads(row['retry_json'] or '[]'),
    }


def save_daily(username, list_id, day_iso, state):
    target = json.dumps(state.get('target') or [], ensure_ascii=False)
    done = json.dumps(state.get('done') or [], ensure_ascii=False)
    retry = json.dumps(state.get('retry') or [], ensure_ascii=False)
    existing = fetch_daily(username, list_id, day_iso)
    if existing is None:
        _run(
            'INSERT INTO daily_task '
            '(username, list_id, day, target_json, done_json, retry_json) '
            'VALUES (%s, %s, %s, %s, %s, %s);',
            (username, list_id, day_iso, target, done, retry),
        )
    else:
        _run(
            'UPDATE daily_task SET target_json = %s, done_json = %s, retry_json = %s '
            'WHERE username = %s AND list_id = %s AND day = %s;',
            (target, done, retry, username, list_id, day_iso),
        )


def delete_list_progress(list_id):
    _run('DELETE FROM word_progress WHERE list_id = %s;', (list_id,))
    _run('DELETE FROM daily_task WHERE list_id = %s;', (list_id,))
