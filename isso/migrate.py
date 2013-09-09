# -*- encoding: utf-8 -*-
#
# Copyright 2012, Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses. see isso/__init__.py
#
# TODO
#
# - export does not include website from commenters
# - Disqus includes already deleted comments

from __future__ import division

import sys
import os
import hashlib

from time import mktime, strptime
from urlparse import urlparse
from collections import defaultdict

from xml.etree import ElementTree

from isso.models import Comment


ns = '{http://disqus.com}'
dsq = '{http://disqus.com/disqus-internals}'


def insert(db, thread, comments):

    path = urlparse(thread.find('%sid' % ns).text).path
    remap = dict()

    for item in sorted(comments, key=lambda k: k['created']):

        parent = remap.get(item.get('dsq:parent'))
        comment = Comment(created=item['created'], text=item['text'],
                          author=item['author'], parent=parent,
                          hash=hashlib.md5(item["email"] or '').hexdigest())

        rv = db.add(path, comment, '127.0.0.1')
        remap[item['dsq:id']] = rv["id"]


def disqus(db, xmlfile):

    tree = ElementTree.parse(xmlfile)
    res = defaultdict(list)

    for post in tree.findall('%spost' % ns):

        item = {
            'dsq:id': post.attrib.get(dsq + 'id'),
            'text': post.find('%smessage' % ns).text,
            'author': post.find('%sauthor/%sname' % (ns, ns)).text,
            'email': post.find('%sauthor/%semail' % (ns, ns)).text,
            'created': mktime(strptime(
                post.find('%screatedAt' % ns).text, '%Y-%m-%dT%H:%M:%SZ'))
        }

        if post.find(ns + 'parent') is not None:
            item['dsq:parent'] = post.find(ns + 'parent').attrib.get(dsq + 'id')

        res[post.find('%sthread' % ns).attrib.get(dsq + 'id')].append(item)

    num = len(tree.findall('%sthread' % ns))
    cols = int(os.popen('stty size', 'r').read().split()[1])

    threads = 0
    for i, thread in enumerate(tree.findall('%sthread' % ns)):

        if int(round((i+1)/num, 2) * 100) % 13 == 0:

            sys.stdout.write("\r%s" % (" "*cols))
            sys.stdout.write("\r[%i%%]  %s" % (((i+1)/num * 100), thread.find('%sid' % ns).text))
            sys.stdout.flush()

        id = thread.attrib.get(dsq + 'id')
        if id in res:
            threads += 1
            insert(db, thread, res[id])

    sys.stdout.write("\r%s" % (" "*cols))
    sys.stdout.write("\r[100%%]  %i threads, %i comments" % (threads, len(tree.findall('%spost' % ns))))