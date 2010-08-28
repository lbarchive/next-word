#!/usr/bin/env python
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
# Creation Date : 2008-06-04T03:49:54+0800
#
# Author        : Yu-Jie Lin
# Author Website: http://thetinybit.com

__version__ = '$Revision: 17 $'
__date__ = '$Date: 2008-06-17 01:12:30 +0800 (Tue, 17 Jun 2008) $'
# $Source$


import functools
import logging
import os
import re
import time

import wsgiref.handlers
from google.appengine.api import users
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template

import nextword
from nextword import model


def get_message_box(msg, css_class='message'):
    return """<div id="message" class="%s">%s</div>""" % (css_class, msg)


def get_relative_time(t):
    return int((time.time() - t) / 60)


class MainHandler(webapp.RequestHandler):

    def get(self):
        template_values = {
            'title': 'Home',
            }
        path = os.path.join(os.path.dirname(__file__), 'template/index.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        nextword.add_word('Start')
        message = ''
        top_out = []
        top_out_ago = -1
        IP = self.request.remote_addr
        action = self.request.get('action')
        suggestion = self.request.get('suggestion')
        next = self.request.get('next')
        req_word = self.request.get('req_word')
        req = nextword.get_request(IP)
        if req and req_word:
            if req['word'].word == req_word:
                # TODO Check submission speed
                if action == 'link':
                    next_word = nextword.add_word(next)
                    # Must be enabled
                    if next_word and next_word.enabled:
                        nextword.increase_linkcount(req['word'], next_word)
                        message = get_message_box('%s -> %s added.' % (
                            req['word'].display_word, next_word.display_word))

                        top_out, top_out_ago = req['word']._get_top_out()
                        top_out_ago = get_relative_time(top_out_ago)

                        # this request is done
                        req = nextword.request_word(IP)
                        # clean up input box
                        next = ''
                    elif next == '':
                        # No input == Skip
                        req = nextword.request_word(IP)
                    else:
                        message = get_message_box(
                            '&ldquo;%s&rdquo; is not valid word!' % next,
                            'error')
                elif action == 'skip':
                    nextword.increase_word_skips(req['word'])
                    req = nextword.request_word(IP)
                else:
                    # FIXME bad people
                    logging.warning(
                       'IP %s: action = %s, agent = %s, next = %s'
                       % (IP, action, self.request.user_agent, next))
            else:
                # FIXME something wrong, or someone is bad
                # TODO Also print out the user data if available
                logging.warning('IP %s: %s != %s, agent = %s, next = %s' % (
                    IP,
                    req['word'].word,
                    req_word,
                    self.request.user_agent,
                    next,
                    ))
        else:
            req = nextword.request_word(IP)

        template_values = {
            'title': 'What Next?',
            'req': req,
            'linkline_ascii': '&nbsp;%sv' % ('&nbsp;' * len(req['word'].display_word)),
            'next': next,
            'top_out': top_out,
            'top_out_ago': top_out_ago,
            'message': message,
            }
        path = os.path.join(os.path.dirname(__file__),
            'template/index_link.html')
        self.response.out.write(template.render(path, template_values))


class AboutHandler(webapp.RequestHandler):

    def get(self):
        template_values = {
            'title': 'About',
            }
        path = os.path.join(os.path.dirname(__file__), 'template/about.html')
        self.response.out.write(template.render(path, template_values))


class StatisticsHandler(webapp.RequestHandler):

    def get(self):
        word_count, word_count_added = nextword.model.Word._get_count()
        unique_link_count, link_count, link_count_added = \
            nextword.model.Link._get_count()
        top_links, top_links_added = nextword.model.Link._get_top_links()
        new_words, new_words_added = nextword.model.Word._get_new_words()
        new_links, new_links_added = nextword.model.Link._get_new_links()

        template_values = {
            'title': 'Statistics',
            'word_count': word_count,
            'word_count_ago': get_relative_time(word_count_added),
            'unique_link_count': unique_link_count,
            'link_count': link_count,
            'link_count_ago': get_relative_time(link_count_added),
            'top_links': top_links,
            'top_links_ago': get_relative_time(top_links_added),
            'new_words': new_words,
            'new_words_ago': get_relative_time(new_words_added),
            'new_links': new_links,
            'new_links_ago': get_relative_time(new_links_added),
            }
        path = os.path.join(os.path.dirname(__file__),
            'template/statistics.html')
        self.response.out.write(template.render(path, template_values))


class DiscussionHandler(webapp.RequestHandler):

    def get(self):
        template_values = {
            'title': 'Discussion',
            }
        path = os.path.join(os.path.dirname(__file__),
            'template/discussion_page.html')
        self.response.out.write(template.render(path, template_values))


class WordHandler(webapp.RequestHandler):

    def get(self):
        word = None
        # extract the word
        m = re.compile('.*/word/(.+)$').match(self.request.uri)
        if m:
            word = nextword.get_word(m.group(1), True)
        if not word or not word.enabled:
            self.response.set_status(404)
            self.response.out.write('No such word')
            return

        top_in, top_in_ago = word._get_top_in()
        top_in_ago = get_relative_time(top_in_ago)
        top_out, top_out_ago = word._get_top_out()
        top_out_ago = get_relative_time(top_out_ago)

        template_values = {
            'title': word.display_word,
            'word': word,
            'top_in': top_in,
            'top_in_ago': top_in_ago,
            'top_out': top_out,
            'top_out_ago': top_out_ago,
            }
        path = os.path.join(os.path.dirname(__file__), 'template/word.html')
        self.response.out.write(template.render(path, template_values))


class LinkHandler(webapp.RequestHandler):

    def get(self):
        link = None
        # extract the link
        m = re.compile('.*/link/(.+)/(.+)$').match(self.request.uri)
        if m:
            link = nextword.get_link(m.group(1), m.group(2), True)
        if not link or not link.start.enabled or not link.end.enabled:
            self.response.set_status(404)
            self.response.out.write('No such link')
            return
        data, date_range, cached = link._get_month_data()
        month_chart = nextword.get_gchart_month(data, date_range)
        template_values = {
            'title': '%s -> %s' % (link.start.display_word,
                link.end.display_word),
            'link': link,
            'month_chart': month_chart,
            'month_chart_ago': int((time.time() - cached) / 60),
            }
        path = os.path.join(os.path.dirname(__file__), 'template/link.html')
        self.response.out.write(template.render(path, template_values))


def must_admin(method):

    @functools.wraps(method)
    def check(self, *args, **kwargs):
        user = users.get_current_user()

        if user:
            if users.is_current_user_admin():
                return method(self, *args, **kwargs)
            else:
                return self.redirect('/')
        else:
            self.redirect(users.create_login_url(self.request.uri))
    return check


class AdminHandler(webapp.RequestHandler):

    @must_admin
    def get(self):
        template_values = {
            'message': 'Hello Admin!',
            }
        path = os.path.join(os.path.dirname(__file__), 'template/admin.html')
        self.response.out.write(template.render(path, template_values))


class AdminWordHandler(AdminHandler):

    @must_admin
    def get(self):
        message = ''
        toggle = self.request.get('toggle')
        if toggle:
            w = nextword.get_word(toggle, True)
            w.enabled = not w.enabled
            w.put()

        sort = self.request.get('sort')
        if not sort:
            sort = 'word'
        order = self.request.get('order')
        if order == 'asc':
            order = ''
            cur_order = 'asc'
            click_order = 'dec'
        else:
            order = '-'
            cur_order = 'dec'
            click_order = 'asc'

        q = model.Word.all()
        q.order('%s%s' % (order, sort))
        words = q.fetch(100)

        base_uri = '/admin/word'
        current_uri = '%s?sort=%s&order=%s' % (base_uri, sort, cur_order)
        headlink_word = '%s?sort=word&order=%s' % (base_uri, click_order)
        headlink_added = '%s?sort=added&order=%s' % (base_uri, click_order)
        headlink_enabled = '%s?sort=enabled&order=%s' % (base_uri, click_order)

        template_values = {
            'message': message,
            'words': words,
            'current_uri': current_uri,
            'headlink_word': headlink_word,
            'headlink_added': headlink_added,
            'headlink_enabled': headlink_enabled,
            }
        path = os.path.join(os.path.dirname(__file__),
            'template/admin_word.html')
        self.response.out.write(template.render(path, template_values))


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/about', AboutHandler),
                                          ('/statistics', StatisticsHandler),
                                          ('/discussion', DiscussionHandler),
                                          ('/word/.*', WordHandler),
                                          ('/link/.*', LinkHandler),
                                          ('/admin', AdminHandler),
                                          ('/admin/word', AdminWordHandler),
                                         ],
                                         debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()

# vim: set tw=78:
