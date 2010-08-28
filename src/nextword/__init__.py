#
# Copyright 2008, 2010 Yu-Jie Lin
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Website       : http://nextword.thetinybit.com
# Creation Date : 2008-06-04T04:20:18+0800
#
# Author        : Yu-Jie Lin
# Author Website: http://thetinybit.com

__version__ = '$Revision: 15 $'
__date__ = '$Date: 2008-06-14 13:14:17 +0800 (Sat, 14 Jun 2008) $'
# $Source$


import logging
import random
import re
import time
from datetime import datetime, timedelta

from google.appengine.api import memcache
from google.appengine.ext import db

import model


def get_word_ids(with_time=False):
    try:
        word_data = memcache.get('word_data')
    except:
        logging.info('memcache error on word_data')
        word_ids = None
    if word_data:
        if with_time:
            return word_data
        else:
            return word_data[0]

    query = model.Word.all()
    query.filter('enabled =', True)
    word_ids = []
    offset = 0
    words = query.fetch(1000, offset)
    while words:
        for word in words:
            # word_ids += will not work since 'long' type is not iterable
            word_ids.append(word.key().id())
        if len(words) < 1000:
            break
        offset += 1000
        words = query.fetch(1000, offset)
    word_data = (word_ids, time.time())
    memcache.set('word_data', word_data, 3600)
    if with_time:
        return word_data
    else:
        return word_ids


def get_random_word():
    word_ids = get_word_ids()
    word = None
    if word_ids:
        word = model.Word.get_by_id(word_ids[random.randrange(len(word_ids))])
    return word


def get_request(IP):
    """Find the request from the IP"""
    try:
        req = memcache.get('req_%s' % IP)
    except:
        logging.info('memcache error on req_' + IP)
        req = None
    return req


def remove_request(IP):
    reqs = memcache.get('requests')
    if IP in reqs:
        del reqs[IP]
    memcache.set('requests', reqs)


def add_request(IP, word):
    req = {
        'IP': IP,
        'word': word,
        'added': datetime.utcnow(),
        }
    if memcache.set('req_%s' % IP, req, 3600):
        return req
    else:
        return None


def request_word(IP):
    word = get_random_word()
    if word:
        return add_request(IP, word)
    else:
        return None


def check_word(word, loose=False):
    """Check word see if only contains valid letters"""
    if loose:
        word = word.replace('_', ' ')
    if re.compile('^[ \-a-zA-Z]{1,100}$').match(word):
        # Must have letters
        if re.compile('[a-zA-Z]+').match(word):
            return True
    return False


def normalize_display_word(word):
    # No continuous spaces or dashes
    word = re.compile(' {2,}').sub(' ', word)
    word = re.compile('-{2,}').sub('-', word)
    # No space before or after the string
    return word.strip()


def normalize_word(word):
    return word.replace(' ', '_').lower()


def get_word(word, loose=False):
    if not check_word(word, loose):
        return None
    word = normalize_word(normalize_display_word(word))
    query = model.Word.all()
    query.filter('word =', word)
    return query.get()


def add_word(word):
    """Add a new word

    Returns the Word object
    """
    if not check_word(word):
        return None
    # Already has this word?
    w = get_word(word)
    if w:
        return w
    # Insert the word
    logging.debug('inserting new word: %s' % word)
    w = model.Word()
    w.display_word = normalize_display_word(word)
    w.word = normalize_word(w.display_word)
    w.put()
    return w


def get_link(start, end, loose=False):
    if isinstance(start, str):
        start = get_word(start, loose)
    if isinstance(end, str):
        end = get_word(end, loose)
    q = model.Link.all()
    q.filter('start =', start)
    q.filter('end =', end)
    return q.get()


def get_linkcount(link, date):
    q = model.LinkCount.all()
    q.filter('link =', link)
    q.filter('date =', date)
    return q.get()


def get_today():
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)


def get_today_linkcount(link):
    return get_linkcount(link, get_today())


def increase_linkcount(start, end):
    """Increases link count

    start and end are Word objects
    Returns Link object
    """
    # FIXME would have races here?
    link = get_link(start, end)
    if link:
        # Increast the count
        link.count = link.count + 1
    else:
        # Inset the link
        link = model.Link()
        link.start = start
        link.end = end
    link.put()

    increase_word_starts(start)
    increase_word_ends(end)

    linkcount = get_today_linkcount(link)
    if linkcount:
        linkcount.count = linkcount.count + 1
    else:
        # Insert link count
        linkcount = model.LinkCount()
        linkcount.link = link
    linkcount.put()

    return link, linkcount


def get_wordstat(word, date):
    q = model.WordStat.all()
    q.filter('word =', word)
    q.filter('date =', date)
    return q.get()


def get_today_wordstat(word):
    return get_wordstat(word, get_today())


def increase_word_starts(word):
    word.starts = word.starts + 1
    word.put()

    wordstat = get_today_wordstat(word)
    if wordstat:
        wordstat.starts = wordstat.starts + 1
    else:
        wordstat = model.WordStat()
        wordstat.word = word
        wordstat.starts = 1
    wordstat.put()


def increase_word_ends(word):
    word.ends = word.ends + 1
    word.put()

    wordstat = get_today_wordstat(word)
    if wordstat:
        wordstat.ends = wordstat.ends + 1
    else:
        wordstat = model.WordStat()
        wordstat.word = word
        wordstat.ends = 1
    wordstat.put()


def increase_word_skips(word):
    word.skips = word.skips + 1
    word.put()

    wordstat = get_today_wordstat(word)
    if wordstat:
        wordstat.skips = wordstat.skips + 1
    else:
        wordstat = model.WordStat()
        wordstat.word = word
        wordstat.skips = 1
    wordstat.put()


def add_report(IP, word, suggestion):
    report = model.Report()
    report.word = word
    report.suggestion = suggestion
    report.IP = IP
    report.put()


def get_gchart_month(data, date_range):
    c = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    # Normalize data
    max_value = max(data) or 1
    norm_data = "".join([c[int(61.0 * count / max_value)] for count in data])
    # FIXME max_value = 1
    return "http://chart.apis.google.com/chart?cht=lc&amp;chs=200x125&amp;\
chd=s:%s&amp;chco=224499&amp;chxt=x,y&amp;chxl=0:|%s|%s|1:||%d|%d&amp;\
chm=B,76A4FB,0,0,0" \
    % (norm_data, date_range[0].strftime('%b %d'),
        date_range[1].strftime('%b %d'), max_value / 2, max_value)

# vim: set tw=78:
