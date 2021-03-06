#!/usr/bin/env python
# -*- coding: utf-8 -*-

state_index={'all': 0, 'downloading': 1, 'paused': 2, 'finished': 3, 'invalid': 4}
state_name=['all', 'downloading', 'paused', 'finished', 'invalid']

class YoutubeDLWebUI(Exception):
    """Base exception for YoutubeDL errors."""
    pass


class TaskError(YoutubeDLWebUI):
    """Error related to download tasks."""
    def __init__(self, msg, tid=None):
        if tid:
            msg += ' tid={}'.format(tid)

        super(TaskError, self).__init__(msg)
        self.msg = msg

    def __str__(self):
        return repr(self.msg)

class TaskPausedError(TaskError):
    def __init__(self, msg, tid=None, url=None, state=None):
        msg = 'Task running error'
        if tid:
            msg += ' tid={}'.format(tid)
        if url:
            msg += ' url={}'.format(url)
        if state:
            msg += ' state={}'.format(state)

        super(TaskPausedError, self).__init__(msg)
        self.msg = msg


class TaskRunningError(TaskError):
    def __init__(self, msg, tid=None, url=None, state=None):
        msg = 'Task running error'
        if tid:
            msg += ' tid={}'.format(tid)
        if url:
            msg += ' url={}'.format(url)
        if state:
            msg += ' state={}'.format(state)

        super(TaskRunningError, self).__init__(msg)
        self.msg = msg


class TaskFinishedError(TaskError):
    def __init__(self, msg, tid=None, url=None, state=None):
        msg = 'Task already finished'
        if tid:
            msg += ' tid={}'.format(tid)
        if url:
            msg += ' url={}'.format(url)
        if state:
            msg += ' state={}'.format(state)

        super(TaskFinishedError, self).__init__(msg)
        self.msg = msg


class TaskInexistenceError(TaskError):
    def __init__(self, msg, tid=None, url=None, state=None):
        msg = 'Task does not exist'
        if tid:
            msg += ' tid={}'.format(tid)
        if url:
            msg += ' url={}'.format(url)
        if state:
            msg += ' state={}'.format(state)

        super(TaskInexistenceError, self).__init__(msg)
        self.msg = msg


class TaskExistenceError(TaskError):
    def __init__(self, msg, tid=None, url=None, state=None):
        msg = 'Task already exists'
        if tid:
            msg += ' tid={}'.format(tid)
        if url:
            msg += ' url={}'.format(url)
        if state:
            msg += ' state={}'.format(state)

        super(TaskExistenceError, self).__init__(msg)
        self.msg = msg


class YDLManagerError(YoutubeDLWebUI):
    """Error related to youtube-dl manager."""
    def __init__(self, msg, tid=None, url=None, state=None):
        if tid:
            msg += ' tid={}'.format(tid)
        if url:
            msg += ' url={}'.format(url)
        if state:
            msg += ' state={}'.format(state)

        super(YDLManagerError, self).__init__(msg)
        self.tid = tid
        self.url = url
        self.state = state
        self.msg = msg

    def __str__(self):
        return repr(self.msg)
