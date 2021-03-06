#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sqlite3

from hashlib import sha1
from time import time

from .utils import state_index, state_name
from .utils import TaskExistenceError
from .utils import TaskInexistenceError
from .utils import TaskPausedError
from .utils import TaskRunningError

class DataBase(object):
    def __init__(self, db_path):
        if os.path.exists(db_path) and not os.path.isfile(db_path):
            print('[ERROR] The db_path: {} is not a regular file'.format(db_path))
            raise Exception('The db_path is not valid')

        if os.path.exists(db_path) and not os.access(db_path, os.W_OK):
            print('[ERROR] The db_path: {} is not writable'.format(db_path))
            raise Exception('The db_path is not valid')

        # first time to create db
        if not os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            #  conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            db = conn.cursor()
            db_path = os.path.dirname(os.path.abspath(__file__))
            db_file = db_path + '/schema.sql'
            with open(db_file, mode='r') as f:
                conn.executescript(f.read())
        else:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            db = conn.cursor()

        self.db = db
        self.conn = conn


    def get_unfinished(self):
        self.db.execute('SELECT tid FROM task_status WHERE state not in (?,?)',
                (state_index['finished'], state_index['invalid']))
        rows = self.db.fetchall()

        ret = []
        for row in rows:
            ret.append(row['tid'])

        return ret

    def get_param(self, tid):
        self.db.execute('SELECT * FROM task_param WHERE tid=(?) and state not in (?,?)',
                (tid, state_index['finished'], state_index['invalid']))
        row = self.db.fetchone()

        if row is None:
            raise TaskInexistenceError('task does not exist')

        return {'tid': row['tid'], 'url': row['url']}


    def get_opts(self, tid):
        self.db.execute('SELECT opt FROM task_ydl_opt WHERE tid=(?) and state not in (?,?)',
                (tid, state_index['finished'], state_index['invalid']))
        row = self.db.fetchone()

        if row is None:
            raise TaskInexistenceError('task does not exist')

        return json.loads(row['opt'])


    def get_ydl_opts(self, tid):
        self.db.execute('SELECT opt FROM task_ydl_opt WHERE tid=(?)', (tid, ))


    def create_task(self, param, ydl_opts):
        url = param['url']
        tid = sha1(url.encode()).hexdigest()

        self.db.execute('SELECT * FROM task_status WHERE tid=(?)', (tid, ))
        if self.db.fetchone() is not None:
            raise TaskExistenceError('Task exists')

        self.db.execute('INSERT INTO task_status (tid) VALUES (?)', (tid, ))
        self.db.execute('INSERT INTO task_param (tid, url) VALUES (?, ?)', (tid, url))
        self.db.execute('INSERT INTO task_info (tid, url, create_time) VALUES (?, ?, ?)',
                        (tid, url, time()))
        ydl_opt_str = json.dumps(ydl_opts)
        self.db.execute('INSERT INTO task_ydl_opt (tid, opt) VALUES (?, ?)', (tid, ydl_opt_str))
        self.conn.commit()

        return tid


    def set_state(self, tid, state):
        if state not in state_index:
            raise KeyError

        self.db.execute('UPDATE task_status SET state=? WHERE tid=(?)', (state_index[state], tid))
        self.db.execute('UPDATE task_param SET state=? WHERE tid=(?)', (state_index[state], tid))
        self.db.execute('UPDATE task_info SET state=? WHERE tid=(?)', (state_index[state], tid))
        self.db.execute('UPDATE task_ydl_opt SET state=? WHERE tid=(?)', (state_index[state], tid))
        self.conn.commit()


    def cancel_task(self,tid, log=None):
        self.db.execute('SELECT * FROM task_status WHERE tid=(?)', (tid, ))
        row = self.db.fetchone()
        if row is None:
            raise TaskInexistenceError('')

        if row['state'] == state_index['paused']:
            raise TaskPausedError('')

        cur_time = time()
        elapsed = row['elapsed']
        start_time = row['start_time']
        elapsed += (cur_time - start_time);

        state = state_index['paused']
        self.db.execute('UPDATE task_status SET state=?, pause_time=?, elapsed=? WHERE tid=(?)',
                        (state,  cur_time, elapsed, tid))
        self.db.execute('UPDATE task_param SET state=? WHERE tid=(?)', (state, tid))
        self.db.execute('UPDATE task_info SET state=? WHERE tid=(?)', (state, tid))
        self.db.execute('UPDATE task_ydl_opt SET state=? WHERE tid=(?)', (state, tid))
        self.conn.commit()

        self.update_log(tid, log)


    def start_task(self, tid, ignore_state=False):
        self.db.execute('SELECT * FROM task_status WHERE tid=(?)', (tid, ))
        row = self.db.fetchone()
        if row is None:
            raise TaskInexistenceError('')

        if row['state'] == state_index['downloading'] and ignore_state is False:
            raise TaskRunningError('')

        state = state_index['downloading']
        self.db.execute('UPDATE task_status SET state=?, start_time=? WHERE tid=(?)', (state, time(), tid))
        self.db.execute('UPDATE task_param SET state=? WHERE tid=(?)', (state, tid))
        self.db.execute('UPDATE task_info SET state=? WHERE tid=(?)', (state, tid))
        self.db.execute('UPDATE task_ydl_opt SET state=? WHERE tid=(?)', (state, tid))
        self.conn.commit()

        return json.loads(row['log'])


    def delete_task(self, tid):
        self.db.execute('SELECT * FROM task_status WHERE tid=(?)', (tid, ))
        row = self.db.fetchone()
        if row is None:
            raise TaskInexistenceError('')

        self.db.execute('DELETE FROM task_status WHERE tid=(?)', (tid, ))
        self.db.execute('DELETE FROM task_info WHERE tid=(?)', (tid, ))
        self.db.execute('DELETE FROM task_param WHERE tid=(?)', (tid, ))
        self.db.execute('DELETE FROM task_ydl_opt WHERE tid=(?)', (tid, ))
        self.conn.commit()


    def query_task(self, tid):
        self.db.execute('SELECT * FROM task_status, task_info WHERE task_status.tid=(?) and task_info.tid=(?)', (tid, tid))
        row = self.db.fetchone()
        if row is None:
            raise TaskInexistenceError('')

        ret = {}
        for key in row.keys():
            if key == 'state':
                ret[key] = state_name[row[key]]
            elif key == 'log':
                ret['log'] = json.loads(row['log'])
            else:
                ret[key] = row[key]

        return ret

    def list_task(self, qstate):
        self.db.execute('SELECT * FROM task_status, task_info WHERE task_status.tid=task_info.tid')
        rows = self.db.fetchall()

        ret = []
        state_counter = {'downloading': 0, 'paused': 0, 'finished': 0, 'invalid': 0}
        if len(rows) == 0:
            return ret, state_counter

        keys = set(rows[0].keys())
        for row in rows:
            t = {}
            for key in keys:
                if key == 'state':
                    state = row[key]
                    t[key] = state_name[state]
                    state_counter[state_name[state]] += 1
                elif key == 'log':
                    t['log'] = json.loads(row['log'])
                else:
                    t[key] = row[key]

            if qstate == 'all' or qstate == t['state']:
                ret.append(t)

        return ret, state_counter

    def list_state(self):
        state_counter = {'downloading': 0, 'paused': 0, 'finished': 0, 'invalid': 0}

        self.db.execute('SELECT state, count(*) as NUM FROM task_status GROUP BY state')
        rows = self.db.fetchall()

        for r in rows:
            state_counter[state_name[r['state']]] = r['NUM']

        return state_counter


    def update_from_info_dict(self, tid, info_dict):
        if info_dict['like_count'] is None:
            info_dict['like_count'] = 0 
        if info_dict['dislike_count'] is None:
            info_dict['dislike_count'] = 0 

        self.db.execute('UPDATE task_info SET title=(?), format=(?), ext=(?), thumbnail=(?), duration=(?), view_count=(?), like_count=(?), dislike_count=(?), average_rating=(?), description=(?) WHERE tid=(?)',
                        (info_dict['title'], info_dict['format'], info_dict['ext'], info_dict['thumbnail'], info_dict['duration'], info_dict['view_count'], info_dict['like_count'], info_dict['dislike_count'], info_dict['average_rating'], info_dict['description'], tid))
        self.conn.commit()


    def update_log(self, tid, log):
        self.db.execute('SELECT * FROM task_status WHERE tid=(?)', (tid, ))
        row = self.db.fetchone()
        if row is None:
            raise TaskInexistenceError('')

        log_str = json.dumps([l for l in log])
        self.db.execute('UPDATE task_status SET log = (?) WHERE tid=(?)', (log_str, tid))
        self.conn.commit()


    def progress_update(self, tid, d):
        self.db.execute('SELECT * FROM task_status WHERE tid=(?)', (tid, ))
        row = self.db.fetchone()
        if row is None:
            raise TaskInexistenceError('')

        elapsed = row['elapsed'] + d['elapsed']

        if 'total_bytes' in d:
            d['total_bytes_estmt'] = d['total_bytes']
        else:
            d['total_bytes'] = '0'

        self.db.execute("UPDATE task_status SET "
                "percent=:percent,            filename=:filename, "
                "tmpfilename=:tmpfilename,    downloaded_bytes=:downloaded_bytes, "
                "total_bytes=:total_bytes,    total_bytes_estmt=:total_bytes_estmt, "
                "speed=:speed, eta=:eta,      elapsed=:elapsed WHERE tid=:tid",
                { "percent":     d['_percent_str'], "filename":          d['filename'],             \
                  "tmpfilename": d['tmpfilename'],  "downloaded_bytes":  d['downloaded_bytes'],     \
                  "total_bytes": d['total_bytes'],  "total_bytes_estmt": d['total_bytes_estimate'], \
                  "speed":       d['speed'],        "eta":               d['eta'],                  \
                  "elapsed":     elapsed,           "tid":               tid
                })

        self.db.execute('UPDATE task_info SET finish_time=? WHERE tid=(?)', (time(), tid))
        self.conn.commit()

