#!/usr/bin/env python
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
# Author        : Yu-Jie Lin


import functools
import os

import wsgiref.handlers
from google.appengine.api import users
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template

import nextword
from nextword import model


class AdminHandler(webapp.RequestHandler):

    def get(self):
        template_values = {
            'message': 'Hello Admin!',
            }
        path = os.path.join(os.path.dirname(__file__), 'template/admin.html')
        self.response.out.write(template.render(path, template_values))


class AdminWordHandler(AdminHandler):

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
    application = webapp.WSGIApplication([
        ('/admin', AdminHandler),
        ('/admin/word', AdminWordHandler),
        ],
        debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
