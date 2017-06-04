#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function, unicode_literals)

import re
import string

space_chars = frozenset(("\t", "\n", "\u000C", " ", "\r"))
space_chars_bytes = frozenset(item.encode("ascii") for item in space_chars)
ascii_letters_bytes = frozenset(item.encode("ascii") for item in string.ascii_letters)
ascii_uppercase_bytes = frozenset(item.encode("ascii") for item in string.ascii_uppercase)
spaces_angle_brackets = space_chars_bytes | frozenset((b">", b"<"))
skip1 = space_chars_bytes | frozenset((b"/", ))
ascii_punctuation_re = re.compile(
    "[\u0009-\u000D\u0020-\u002F\u003A-\u0040\u005B-\u0060\u007B-\u007E]")


encodings = {  # {{{
    '437': 'cp437',
    '850': 'cp850',
    '852': 'cp852',
    '855': 'cp855',
    '857': 'cp857',
    '860': 'cp860',
    '861': 'cp861',
    '862': 'cp862',
    '863': 'cp863',
    '865': 'cp865',
    '866': 'cp866',
    '869': 'cp869',
    'ansix341968': 'ascii',
    'ansix341986': 'ascii',
    'arabic': 'iso8859-6',
    'ascii': 'ascii',
    'asmo708': 'iso8859-6',
    'big5': 'big5',
    'big5hkscs': 'big5hkscs',
    'chinese': 'gbk',
    'cp037': 'cp037',
    'cp1026': 'cp1026',
    'cp154': 'ptcp154',
    'cp367': 'ascii',
    'cp424': 'cp424',
    'cp437': 'cp437',
    'cp500': 'cp500',
    'cp775': 'cp775',
    'cp819': 'windows-1252',
    'cp850': 'cp850',
    'cp852': 'cp852',
    'cp855': 'cp855',
    'cp857': 'cp857',
    'cp860': 'cp860',
    'cp861': 'cp861',
    'cp862': 'cp862',
    'cp863': 'cp863',
    'cp864': 'cp864',
    'cp865': 'cp865',
    'cp866': 'cp866',
    'cp869': 'cp869',
    'cp936': 'gbk',
    'cpgr': 'cp869',
    'cpis': 'cp861',
    'csascii': 'ascii',
    'csbig5': 'big5',
    'cseuckr': 'cp949',
    'cseucpkdfmtjapanese': 'euc_jp',
    'csgb2312': 'gbk',
    'cshproman8': 'hp-roman8',
    'csibm037': 'cp037',
    'csibm1026': 'cp1026',
    'csibm424': 'cp424',
    'csibm500': 'cp500',
    'csibm855': 'cp855',
    'csibm857': 'cp857',
    'csibm860': 'cp860',
    'csibm861': 'cp861',
    'csibm863': 'cp863',
    'csibm864': 'cp864',
    'csibm865': 'cp865',
    'csibm866': 'cp866',
    'csibm869': 'cp869',
    'csiso2022jp': 'iso2022_jp',
    'csiso2022jp2': 'iso2022_jp_2',
    'csiso2022kr': 'iso2022_kr',
    'csiso58gb231280': 'gbk',
    'csisolatin1': 'windows-1252',
    'csisolatin2': 'iso8859-2',
    'csisolatin3': 'iso8859-3',
    'csisolatin4': 'iso8859-4',
    'csisolatin5': 'windows-1254',
    'csisolatin6': 'iso8859-10',
    'csisolatinarabic': 'iso8859-6',
    'csisolatincyrillic': 'iso8859-5',
    'csisolatingreek': 'iso8859-7',
    'csisolatinhebrew': 'iso8859-8',
    'cskoi8r': 'koi8-r',
    'csksc56011987': 'cp949',
    'cspc775baltic': 'cp775',
    'cspc850multilingual': 'cp850',
    'cspc862latinhebrew': 'cp862',
    'cspc8codepage437': 'cp437',
    'cspcp852': 'cp852',
    'csptcp154': 'ptcp154',
    'csshiftjis': 'shift_jis',
    'csunicode11utf7': 'utf-7',
    'cyrillic': 'iso8859-5',
    'cyrillicasian': 'ptcp154',
    'ebcdiccpbe': 'cp500',
    'ebcdiccpca': 'cp037',
    'ebcdiccpch': 'cp500',
    'ebcdiccphe': 'cp424',
    'ebcdiccpnl': 'cp037',
    'ebcdiccpus': 'cp037',
    'ebcdiccpwt': 'cp037',
    'ecma114': 'iso8859-6',
    'ecma118': 'iso8859-7',
    'elot928': 'iso8859-7',
    'eucjp': 'euc_jp',
    'euckr': 'cp949',
    'extendedunixcodepackedformatforjapanese': 'euc_jp',
    'gb18030': 'gb18030',
    'gb2312': 'gbk',
    'gb231280': 'gbk',
    'gbk': 'gbk',
    'greek': 'iso8859-7',
    'greek8': 'iso8859-7',
    'hebrew': 'iso8859-8',
    'hproman8': 'hp-roman8',
    'hzgb2312': 'hz',
    'ibm037': 'cp037',
    'ibm1026': 'cp1026',
    'ibm367': 'ascii',
    'ibm424': 'cp424',
    'ibm437': 'cp437',
    'ibm500': 'cp500',
    'ibm775': 'cp775',
    'ibm819': 'windows-1252',
    'ibm850': 'cp850',
    'ibm852': 'cp852',
    'ibm855': 'cp855',
    'ibm857': 'cp857',
    'ibm860': 'cp860',
    'ibm861': 'cp861',
    'ibm862': 'cp862',
    'ibm863': 'cp863',
    'ibm864': 'cp864',
    'ibm865': 'cp865',
    'ibm866': 'cp866',
    'ibm869': 'cp869',
    'iso2022jp': 'iso2022_jp',
    'iso2022jp2': 'iso2022_jp_2',
    'iso2022kr': 'iso2022_kr',
    'iso646irv1991': 'ascii',
    'iso646us': 'ascii',
    'iso88591': 'windows-1252',
    'iso885910': 'iso8859-10',
    'iso8859101992': 'iso8859-10',
    'iso885911987': 'windows-1252',
    'iso885913': 'iso8859-13',
    'iso885914': 'iso8859-14',
    'iso8859141998': 'iso8859-14',
    'iso885915': 'iso8859-15',
    'iso885916': 'iso8859-16',
    'iso8859162001': 'iso8859-16',
    'iso88592': 'iso8859-2',
    'iso885921987': 'iso8859-2',
    'iso88593': 'iso8859-3',
    'iso885931988': 'iso8859-3',
    'iso88594': 'iso8859-4',
    'iso885941988': 'iso8859-4',
    'iso88595': 'iso8859-5',
    'iso885951988': 'iso8859-5',
    'iso88596': 'iso8859-6',
    'iso885961987': 'iso8859-6',
    'iso88597': 'iso8859-7',
    'iso885971987': 'iso8859-7',
    'iso88598': 'iso8859-8',
    'iso885981988': 'iso8859-8',
    'iso88599': 'windows-1254',
    'iso885991989': 'windows-1254',
    'isoceltic': 'iso8859-14',
    'isoir100': 'windows-1252',
    'isoir101': 'iso8859-2',
    'isoir109': 'iso8859-3',
    'isoir110': 'iso8859-4',
    'isoir126': 'iso8859-7',
    'isoir127': 'iso8859-6',
    'isoir138': 'iso8859-8',
    'isoir144': 'iso8859-5',
    'isoir148': 'windows-1254',
    'isoir149': 'cp949',
    'isoir157': 'iso8859-10',
    'isoir199': 'iso8859-14',
    'isoir226': 'iso8859-16',
    'isoir58': 'gbk',
    'isoir6': 'ascii',
    'koi8r': 'koi8-r',
    'koi8u': 'koi8-u',
    'korean': 'cp949',
    'ksc5601': 'cp949',
    'ksc56011987': 'cp949',
    'ksc56011989': 'cp949',
    'l1': 'windows-1252',
    'l10': 'iso8859-16',
    'l2': 'iso8859-2',
    'l3': 'iso8859-3',
    'l4': 'iso8859-4',
    'l5': 'windows-1254',
    'l6': 'iso8859-10',
    'l8': 'iso8859-14',
    'latin1': 'windows-1252',
    'latin10': 'iso8859-16',
    'latin2': 'iso8859-2',
    'latin3': 'iso8859-3',
    'latin4': 'iso8859-4',
    'latin5': 'windows-1254',
    'latin6': 'iso8859-10',
    'latin8': 'iso8859-14',
    'latin9': 'iso8859-15',
    'ms936': 'gbk',
    'mskanji': 'shift_jis',
    'pt154': 'ptcp154',
    'ptcp154': 'ptcp154',
    'r8': 'hp-roman8',
    'roman8': 'hp-roman8',
    'shiftjis': 'shift_jis',
    'tis620': 'cp874',
    'unicode11utf7': 'utf-7',
    'us': 'ascii',
    'usascii': 'ascii',
    'utf16': 'utf-16',
    'utf16be': 'utf-16-be',
    'utf16le': 'utf-16-le',
    'utf8': 'utf-8',
    'windows1250': 'cp1250',
    'windows1251': 'cp1251',
    'windows1252': 'cp1252',
    'windows1253': 'cp1253',
    'windows1254': 'cp1254',
    'windows1255': 'cp1255',
    'windows1256': 'cp1256',
    'windows1257': 'cp1257',
    'windows1258': 'cp1258',
    'windows936': 'gbk',
    'x-x-big5': 'big5'}

# }}}


def codec_name(encoding):
    """Return the python codec name corresponding to an encoding or None if the
    string doesn't correspond to a valid encoding."""
    if isinstance(encoding, bytes):
        try:
            encoding = encoding.decode("ascii")
        except UnicodeDecodeError:
            return None
    if encoding:
        canonical_name = ascii_punctuation_re.sub("", encoding).lower()
        return encodings.get(canonical_name, None)
    else:
        return None


class EncodingBytes(bytes):
    """String-like object with an associated position and various extra methods
    If the position is ever greater than the string length then an exception is
    raised"""

    def __new__(self, value):
        return bytes.__new__(self, value.lower())

    def __init__(self, value):
        self._position = -1

    def __iter__(self):
        return self

    def __next__(self):
        p = self._position = self._position + 1
        if p >= len(self):
            raise StopIteration
        elif p < 0:
            raise TypeError
        return self[p:p + 1]

    def next(self):
        # Py2 compat
        return self.__next__()

    def previous(self):
        p = self._position
        if p >= len(self):
            raise StopIteration
        elif p < 0:
            raise TypeError
        self._position = p = p - 1
        return self[p:p + 1]

    @property
    def position(self):
        if self._position >= len(self):
            raise StopIteration
        if self._position >= 0:
            return self._position

    @position.setter
    def position(self, position):
        if self._position >= len(self):
            raise StopIteration
        self._position = position

    @property
    def current_byte(self):
        return self[self.position:self.position + 1]

    def skip(self, chars=space_chars_bytes):
        """Skip past a list of characters"""
        p = self.position  # use property for the error-checking
        while p < len(self):
            c = self[p:p + 1]
            if c not in chars:
                self._position = p
                return c
            p += 1
        self._position = p
        return None

    def skip_until(self, chars):
        p = self.position
        while p < len(self):
            c = self[p:p + 1]
            if c in chars:
                self._position = p
                return c
            p += 1
        self._position = p
        return None

    def match_bytes(self, bytes):
        """Look for a sequence of bytes at the start of a string. If the bytes
        are found return True and advance the position to the byte after the
        match. Otherwise return False and leave the position alone"""
        p = self.position
        data = self[p:p + len(bytes)]
        rv = data.startswith(bytes)
        if rv:
            self.position += len(bytes)
        return rv

    def jump_to(self, bytes):
        """Look for the next sequence of bytes matching a given sequence. If
        a match is found advance the position to the last byte of the match"""
        new_pos = self[self.position:].find(bytes)
        if new_pos > -1:
            if self._position == -1:
                self._position = 0
            self._position += (new_pos + len(bytes) - 1)
            return True
        else:
            raise StopIteration


class ContentAttrParser(object):

    def __init__(self, data):
        self.data = data

    def parse(self):
        try:
            # Check if the attr name is charset
            # otherwise return
            self.data.jump_to(b"charset")
            self.data.position += 1
            self.data.skip()
            if not self.data.current_byte == b"=":
                # If there is no = sign keep looking for attrs
                return None
            self.data.position += 1
            self.data.skip()
            # Look for an encoding between matching quote marks
            if self.data.current_byte in (b'"', b"'"):
                quote_mark = self.data.current_byte
                self.data.position += 1
                old_pos = self.data.position
                if self.data.jump_to(quote_mark):
                    return self.data[old_pos:self.data.position]
                else:
                    return None
            else:
                # Unquoted value
                old_pos = self.data.position
                try:
                    self.data.skip_until(space_chars_bytes)
                    return self.data[old_pos:self.data.position]
                except StopIteration:
                    # Return the whole remaining value
                    return self.data[old_pos:]
        except StopIteration:
            return None


class EncodingParser(object):
    """Mini parser for detecting character encoding from meta elements"""

    def __init__(self, data):
        """string - the data to work on for encoding detection"""
        self.data = EncodingBytes(data)
        self.encoding = None

    def __call__(self):
        dispatch = ((b"<!--", self.handle_comment), (b"<meta", self.handle_meta),
                    (b"</", self.handle_possible_end_tag), (b"<!", self.handle_other),
                    (b"<?", self.handle_other), (b"<", self.handle_possible_start_tag))
        for byte in self.data:
            keep_parsing = True
            for key, method in dispatch:
                if self.data.match_bytes(key):
                    try:
                        keep_parsing = method()
                        break
                    except StopIteration:
                        keep_parsing = False
                        break
            if not keep_parsing:
                break

        return self.encoding

    def handle_comment(self):
        """Skip over comments"""
        return self.data.jump_to(b"-->")

    def handle_meta(self):
        if self.data.current_byte not in space_chars_bytes:
            # if we have <meta not followed by a space so just keep going
            return True
        # We have a valid meta element we want to search for attributes
        has_pragma = False
        pending_encoding = None
        while True:
            # Try to find the next attribute after the current position
            attr = self.get_attribute()
            if attr is None:
                return True
            if attr[0] == b"http-equiv":
                has_pragma = attr[1] == b"content-type"
                if has_pragma and pending_encoding is not None:
                    self.encoding = pending_encoding
                    return False
            elif attr[0] == b"charset":
                tentative_encoding = attr[1]
                codec = codec_name(tentative_encoding)
                if codec is not None:
                    self.encoding = codec
                    return False
            elif attr[0] == b"content":
                cap = ContentAttrParser(EncodingBytes(attr[1]))
                tentative_encoding = cap.parse()
                if tentative_encoding is not None:
                    codec = codec_name(tentative_encoding)
                    if codec is not None:
                        if has_pragma:
                            self.encoding = codec
                            return False
                        else:
                            pending_encoding = codec

    def handle_possible_start_tag(self):
        return self.handle_possible_tag(False)

    def handle_possible_end_tag(self):
        next(self.data)
        return self.handle_possible_tag(True)

    def handle_possible_tag(self, end_tag):
        data = self.data
        if data.current_byte not in ascii_letters_bytes:
            # If the next byte is not an ascii letter either ignore this
            # fragment (possible start tag case) or treat it according to
            # handle_other
            if end_tag:
                data.previous()
                self.handle_other()
            return True

        c = data.skip_until(spaces_angle_brackets)
        if c == b"<":
            # return to the first step in the overall "two step" algorithm
            # reprocessing the < byte
            data.previous()
        else:
            # Read all attributes
            attr = self.get_attribute()
            while attr is not None:
                attr = self.get_attribute()
        return True

    def handle_other(self):
        return self.data.jump_to(b">")

    def get_attribute(self):
        """Return a name,value pair for the next attribute in the stream,
        if one is found, or None"""
        data = self.data
        # Step 1 (skip chars)
        c = data.skip(skip1)
        assert c is None or len(c) == 1
        # Step 2
        if c in (b">", None):
            return None
        # Step 3
        attr_name = []
        attr_value = []
        # Step 4 attribute name
        while True:
            if c == b"=" and attr_name:
                break
            elif c in space_chars_bytes:
                # Step 6!
                c = data.skip()
                break
            elif c in (b"/", b">"):
                return b"".join(attr_name), b""
            elif c in ascii_uppercase_bytes:
                attr_name.append(c.lower())
            elif c is None:
                return None
            else:
                attr_name.append(c)
            # Step 5
            c = next(data)
        # Step 7
        if c != b"=":
            data.previous()
            return b"".join(attr_name), b""
        # Step 8
        next(data)
        # Step 9
        c = data.skip()
        # Step 10
        if c in (b"'", b'"'):
            # 10.1
            quoteChar = c
            while True:
                # 10.2
                c = next(data)
                # 10.3
                if c == quoteChar:
                    next(data)
                    return b"".join(attr_name), b"".join(attr_value)
                # 10.4
                elif c in ascii_uppercase_bytes:
                    attr_value.append(c.lower())
                # 10.5
                else:
                    attr_value.append(c)
        elif c == b">":
            return b"".join(attr_name), b""
        elif c in ascii_uppercase_bytes:
            attr_value.append(c.lower())
        elif c is None:
            return None
        else:
            attr_value.append(c)
        # Step 11
        while True:
            c = next(data)
            if c in spaces_angle_brackets:
                return b"".join(attr_name), b"".join(attr_value)
            elif c in ascii_uppercase_bytes:
                attr_value.append(c.lower())
            elif c is None:
                return None
            else:
                attr_value.append(c)
