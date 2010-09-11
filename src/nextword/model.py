# Define all datastore models for nextword
#
# Copyright 2008 Yu-Jie Lin
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
# Creation Date : 2008-06-04T03:52:12+0800
#
# Author        : Yu-Jie Lin
# Author Website: http://thetinybit.com

__version__ = '$Revision: 12 $'
__date__ = '$Date: 2008-06-11 09:17:46 +0800 (Wed, 11 Jun 2008) $'
# $Source$


import logging
import time
from datetime import datetime, timedelta

from google.appengine.api import memcache
from google.appengine.ext import db

import nextword


def get_count(q):

  r = q.fetch(1000)
  count = 0 
  while True:
    count += len(r)
    if len(r) < 1000:
      break
    q.filter('__key__ >', r[-1])
    r = q.fetch(1000)
  return count


class Word(db.Model):
    # Like ID
    word = db.StringProperty()
    # Usually upper case first letter or properly showing names
    display_word = db.StringProperty()
    # The date of this word added
    added = db.DateTimeProperty(auto_now_add=True)
    # Is this word allowed to be linked
    enabled = db.BooleanProperty(default=True)
    # How many times this word as a start word
    starts = db.IntegerProperty(default=0)
    # How many times this word as a end word
    ends = db.IntegerProperty(default=0)
    # How many times this word is skipped
    skips = db.IntegerProperty(default=0)

    def _get_top_in(self):
        """Return top 10 in links"""
        # Check memcache
        try:
            top_in = memcache.get('word_top_in_' + self.word)
        except:
            logging.info('memcache error on word_top_in_' + self.word)
            top_in = None
        if top_in:
            return top_in
        q = Link.all()
        q.filter('end =', self)
        q.order('-count')
        links = q.fetch(10)
        # Calculate percentage of link.count to word.ends
        for link in links:
            link.percent = 100.0 * link.count / self.ends

        top_in = (links, time.time())
        memcache.set('word_top_in_' + self.word, top_in, 3600)
        return top_in

    def _get_top_out(self):
        """Return top 10 out links"""
        # Check memcache
        try:
            top_out = memcache.get('word_top_out_' + self.word)
        except:
            logging.info('memcache error on word_top_out_' + self.word)
            top_out = None
        if top_out:
            return top_out
        q = Link.all()
        q.filter('start =', self)
        q.order('-count')
        links = q.fetch(10)
        # Calculate percentage of link.count to word.starts
        for link in links:
            link.percent = 100.0 * link.count / self.starts
        top_out = (links, time.time())
        memcache.set('word_top_out_' + self.word, top_out, 3600)
        return top_out

    @staticmethod
    def _get_count():
        try:
            count = memcache.get('word_count')
        except:
            logging.debug('memcache error on word_count')
            count = None
        if count:
            return count
        
        query = Word.all(keys_only=True).filter('enabled =', True).order('__key__')
        count = (get_count(query), time.time())
        memcache.set('word_count', count, 3600)
        return count

    @staticmethod
    def _get_new_words():
        try:
            new_words = memcache.get('new_words')
        except:
            logging.debug('memcache error on new_words')
            new_words = None
        if new_words:
            return new_words
        words = Word.all().order('-added').fetch(10)
        new_words = (words, time.time())
        memcache.set('new_words', new_words, 3600)
        return new_words


class WordStat(db.Model):
    # Which word
    word = db.ReferenceProperty(Word)
    # How many times this word as a start word
    starts = db.IntegerProperty(default=0)
    # How many times this word as a end word
    ends = db.IntegerProperty(default=0)
    # How many times this word is skipped
    skips = db.IntegerProperty(default=0)
    # The date of this record
    date = db.DateProperty(auto_now_add=True)


class Link(db.Model):
    # Which word is the start word
    start = db.ReferenceProperty(Word, collection_name="start_words")
    # Which word is the end word
    end = db.ReferenceProperty(Word, collection_name="end_words")
    # How many times this link is created
    count = db.IntegerProperty(default=1)
    # The date of this link added
    added = db.DateTimeProperty(auto_now_add=True)

    def _get_month_data(self):
        try:
            month_data = memcache.get('link_month_data_%s/%s' % (
                self.start.word, self.end.word))
        except:
            logging.info('memcache error on link_month_data_%s/%s' % (
                self.start.word, self.end.word))
            month_data = None
        if month_data:
            return month_data
        q = LinkCount.all()
        q.filter('link =', self)
        q.order('-date')
        rows = q.fetch(30)
        today = datetime.utcnow().date()
        data = [0]*30
        for row in rows:
            days = (today - row.date).days
            if days < 30:
                data[days] = row.count
        data.reverse()
        date_range = (today + timedelta(days=-29), today)
        month_data = (data, date_range, time.time())
        memcache.set('link_month_data_%s/%s' % (self.start.word,
            self.end.word), month_data, 3600)
        return month_data

    @staticmethod
    def _get_top_links():
        try:
            top_links = memcache.get('top_links')
        except:
            logging.info('memcache error on top_links')
            top_links = None
        if top_links and top_links[1] > time.time() - 3600:
            return top_links

        links = Link.all().order('-count').fetch(10)
        max_count = sum([link.count for link in links])
        for link in links:
            link.percent = 100.0 * link.count / max_count
        links_data = (links, time.time())
        memcache.set('top_links', links_data, 3600)
        return links_data

    @staticmethod
    def _get_count():
        try:
            count = memcache.get('link_count')
        except:
            logging.info('memcache error on link_count')
            count = None
        if count:
            return count
        
        link_count = unique_link_count = get_count(
            Link.all(keys_only=True).filter('count =', 1).order('__key__'))

        query = Link.all().filter('count >', 1)
        offset = 0
        links = query.fetch(1000, offset)
        while links:
            link_count += sum([link.count for link in links])
            if len(links) < 1000:
                break
            offset += 1000
            links = query.fetch(1000, offset)

        count = (unique_link_count, link_count, time.time())
        memcache.set('link_count', count, 3600)
        return count

    @staticmethod
    def _get_new_links():
        try:
            new_links = memcache.get('new_links')
        except:
            logging.debug('memcache error on new_links')
            new_links = None
        if new_links:
            return new_links
        links = Link.all().order('-added').fetch(10)
        new_links = (links, time.time())
        memcache.set('new_links', new_links, 3600)
        return new_links


class LinkCount(db.Model):
    """Use for recording daily counts of links"""
    link = db.ReferenceProperty(Link)
    count = db.IntegerProperty(default=1)
    # The count for which date
    date = db.DateProperty(auto_now_add=True)
