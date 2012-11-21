# -*- coding: utf-8 -*-
'''
Copyright (c) 2005,20012
@author: Marat Khayrullin <xmm.dev@gmail.com>
'''

import locale
import string
locale.setlocale(locale.LC_ALL, '')


class translateMeta(type):
    __registry = {}
    __transTables = {}  # {'srcCoding dstCoding': table)}

    def __init__(cls, name, base, dict):
        #super(translateMeta, cls).__init__(name, base, dict)
        if name == 'transTable':
            return
        assert hasattr(cls, 'aliases')
        assert hasattr(cls, 'table')
        assert isinstance(cls.aliases[0], str)
        assert isinstance(cls.table, str) and len(cls.table) == 76
        assert not name in cls.__registry
        cls.__registry[name] = cls

    def getTableByAlias(cls, name):
        for tbl in cls.__registry.values():
            for alias in tbl.aliases:
                if alias == name:
                    return tbl
        return None

    def createTransTable(cls, src, dst):
        trans = string.maketrans(src.table, dst.table)
        cls.__transTables[src.__name__ + ' ' + dst.__name__] = trans
        return trans

    def getTransTable(cls, src, dst):
        try:
            return cls.__transTables[src.__name__ + ' ' + dst.__name__]
        except KeyError:
            return cls.createTransTable(src, dst)

    def translate(cls, txt, src, dst):
        if not txt:
            return ''
        dst = cls.getTableByAlias(dst)
        src = cls.getTableByAlias(src)
        assert dst or src
        if src == dst or not dst or not src:
            return txt
        else:
            return string.translate(txt, cls.getTransTable(src, dst))

    def translateFrom(cls, txt, src=None):
        if not src:
            src = locale.getlocale()[1]
            assert src
        return cls.translate(txt, src, cls.__name__)

    def translateTo(cls, txt, dst=None):
        if not dst:
            dst = locale.getlocale()[1]
            assert dst
        return cls.translate(txt, cls.__name__, dst)


#transTable = object
class transTable(object):
    __metaclass__ = translateMeta


class koi8r(transTable):
    aliases = ('koi8-r', 'KOI8-R', 'koi', 'KOI', 'koi8', 'KOI8', 'koi8r', 'KOI8R')
    table = '''
\xF0\xF1\xF2\xF3\xF4\xF5\xF6\xF7\xF8\xF9\xFA\xFB
\xFC\xFD\xFE\xFF\x0A\xE0\xE1\xE2\xE3\xE4\xE5\xE6
\xE7\xE8\xE9\xEA\xEB\xEC\xED\xEE\xEF\xB3\x0A\xC0
\xC1\xC2\xC3\xC4\xC5\xC6\xC7\xC8\xC9\xCA\xCB\xCC
\xCD\xCE\xCF\x0A\xD0\xD1\xD2\xD3\xD4\xD5\xD6\xD7
\xD8\xD9\xDA\xDB\xDC\xDD\xDE\xDF\xA3\x0A'''


class cp1251(transTable):
    aliases = ('1251', 'cp1251', 'CP1251', 'windows-1251', 'WINDOWS-1251', 'win', 'WIN', 'mswin', 'MSWIN')
    table = '''
\xCF\xDF\xD0\xD1\xD2\xD3\xC6\xC2\xDC\xDB\xC7\xD8
\xDD\xD9\xD7\xDA\x0A\xDE\xC0\xC1\xD6\xC4\xC5\xD4
\xC3\xD5\xC8\xC9\xCA\xCB\xCC\xCD\xCE\xA8\x0A\xFE
\xE0\xE1\xF6\xE4\xE5\xF4\xE3\xF5\xE8\xE9\xEA\xEB
\xEC\xED\xEE\x0A\xEF\xFF\xF0\xF1\xF2\xF3\xE6\xE2
\xFC\xFB\xE7\xF8\xFD\xF9\xF7\xFA\xB8\x0A'''


class cp866(transTable):
    aliases = ('866', 'cp866', 'CP866', 'dos', 'DOS', 'ibm866', 'IBM866')
    table = '''
\x8F\x9F\x90\x91\x92\x93\x86\x82\x9C\x9B\x87\x98
\x9D\x99\x97\x9A\x0A\x9E\x80\x81\x96\x84\x85\x94
\x83\x95\x88\x89\x8A\x8B\x8C\x8D\x8E\xF0\x0A\xEE
\xA0\xA1\xE6\xA4\xA5\xE4\xA3\xE5\xA8\xA9\xAA\xAB
\xAC\xAD\xAE\x0A\xAF\xEF\xE0\xE1\xE2\xE3\xA6\xA2
\xEC\xEB\xA7\xE8\xED\xE9\xE7\xEA\xF1\x0A'''
