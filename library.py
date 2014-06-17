# -*- coding: utf-8 -*-
# SQL ALchemy

import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, reconstructor
from pyvfs.objectfs import MetaExport
from threading import Thread
from Queue import Queue

engine = create_engine('postgresql://peet:secret@localhost:5432/library')
Session = sessionmaker(bind=engine)
Base = declarative_base()

__exit__ = False
__queue__ = Queue(maxsize=4)

class Book(Base):
    __tablename__ = 'books'

    identifier = Column(String, primary_key=True)
    item_type = Column(String)
    author = Column(String)
    editor = Column(String)
    title = Column(String)
    book_title = Column(String)
    serie_title = Column(String)
    journal = Column(String)
    volume = Column(String)
    part = Column(String)
    chapter = Column(String)
    number = Column(String)
    pages = Column(String)
    year = Column(String)
    month = Column(String)
    publisher = Column(String)
    organization = Column(String)
    city = Column(String)
    edition = Column(String)
    annotation = Column(String)
    isbn = Column(String)
    url = Column(String)
    address = Column(String)
    translator = Column(String)

    @reconstructor
    #export(set_hook=True)
    def hook(self):
        pass

    def __repr__(self):
        ret = '%s "%s", %s, %s' % (self.author,
                                        self.title,
                                        self.address,
                                        self.year)
        return ret.encode('utf-8')


def short(line):
    if isinstance(line, basestring):
        return line if len(line) < 50 else "%s..." % line[:50]
    else:
        return line


class Description(object):

    def __init__(self, item, uid):
        self.item = item
        self.uid = uid
        self.articles = []
        if item.item_type == 'collection':
            self.author = u'Сборник'
        else:
            self.author = item.author
       
    def get(self, key, template='%s', source=None):
        source = source or self.item
        item = getattr(source, key, None)
        if item is None:
            return ''
        else:
            return template % item

    def short_description(self):

        return u'''<div id="s%s" class="%s" onclick="sw('s%s', 'l%s');">
            <span class="author">%s</span>
            <span class="title">%s</span>.
            <span class="city">%s</span>
            <span class="publisher">%s</span>
            <span class="year">%s</span>.
            <span class="volume">%s</span>
            </div>
            ''' % (self.uid,
                   self.item.item_type,
                   self.uid, self.uid,
                   short(self.get('author', '%s.', source=self)),
                   short(self.item.title),
                   self.get('city', '%s:'),
                   self.get('publisher', '%s,'),
                   self.item.year,
                   self.get('volume', 'volume %s'))


    def full_description(self, style='%s full', onclick=True):

        try:
            style = style % self.item.item_type
        except TypeError:
            pass

        if onclick:
            onclick = '''onclick="sw('l%s', 's%s');"''' % (self.uid, self.uid)
        else:
            onclick = ''

        result = u'''<div id="l%s" class="%s" %s>
            <span class="author">%s</span>
            <span class="title">%s</span>.
            <span class="city">%s</span>
            <span class="publisher">%s</span>
            <span class="year">%s</span>.
            <span class="volume">%s</span>
            <span class="translator">%s</span>
            <span class="editor">%s</span>
            ''' % (self.uid, style, onclick,
                   self.get('author', '%s.', source=self),
                   self.item.title,
                   self.get('city', '%s:'),
                   self.get('publisher', '%s,'),
                   self.item.year,
                   self.get('volume', 'volume %s'),
                   self.get('translator', '(%s)'),
                   self.get('editor', '(%s)'))

        for item in self.articles:
            result += item.full_description(style='article', onclick=False)

        result += u'</div>'
        return result

    def dump(self):
        result = u''
        result += self.short_description()
        result += self.full_description()
        return result

    def add_article(self, article):
        self.articles.append(article)


def update_index():
    global __exit__
    global __queue__
    session = Session()
    header = u'''<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>Library index</title>
        <link rel="stylesheet" type="text/css" href="./css/main.css">
        <script type="text/javascript" src="./js/main.js"></script>
    </head>
    <body>
    '''
    tail = u'</body></html>'
    while not __exit__:
        page = header
        books = []
        collections = {}

        for item in session.query(Book).\
                order_by(Book.author).\
                order_by(Book.title).\
                order_by(Book.volume):

            book = Description(item, str(uuid.uuid4())) 
            if item.item_type == 'article':
                if item.book_title not in collections:
                    collections[item.book_title] = [None, []]
                collections[item.book_title][1].append(book)
            else:
                books.append(book)
                if item.title not in collections:
                    collections[item.title] = [book, []]
                collections[item.title][0] = book

        for item in collections:
            for article in collections[item][1]:
                if collections[item][0] is not None:
                    collections[item][0].add_article(article)

        for item in books:
            page += item.dump()

        page += tail
        __queue__.put(page)


class StaticFile(object):

    __metaclass__ = MetaExport
    __inode__ = {'is_file': True,
                 'basedir': '@basedir',
                 'name': '@file_name',
                 'mode': 0o644,
                 'on_commit': 'commit'}

    def __init__(self, basedir, name):
        self.file_name = name
        self.basedir = "/".join(basedir.split("/")[1:])
        self.path = "/".join((basedir, name))
        self.content = open(self.path, "r").read()

    def commit(self, data):
        self.content = data

    def __repr__(self):
        return self.content


class Library(object):

    __metaclass__ = MetaExport
    __inode__ = {'is_file': True,
                 'name': '@file_name',
                 'mode': 0o644}

    def __init__(self):
        self.file_name = 'library.html'

    def __repr__(self):
        global __queue__
        return __queue__.get(60).encode('utf-8')


Thread(target=update_index).start()

static_files = []
for (sdir, dirs, sfiles) in os.walk('static'):
    for sfile in sfiles:
        try:
            static_files.append(StaticFile(sdir, sfile))
        except OSError:
            pass

library = Library()
raw_input("exit >> ")
__exit__ = True
