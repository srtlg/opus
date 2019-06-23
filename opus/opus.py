"""
Structures found in the OPUS file format

Files produced with Opus up to version 5 are considered
"""
import struct
from collections import OrderedDict


class Parameter:
    """
    A parameter consists of a three letter ASCII code which is listed in [1]_

    The last code seems to be always END

    The type decoding is guesswork based on a sample of files

    012 3  4  5  6  7
    CCC 00 aa 00 bb 00

    CCC = code
    aa  = ?
    bb  = (length - 8) / 2
    """
    def __init__(self):
        self.code = None
        self.head = None
        self.tail = None
        self._length = 0

    def read_tail(self, fin):
        self.tail = fin.read(self._length)

    def read_head(self, fin):
        self.head = fin.read(8)
        self.code = self.head[0:3].decode('ASCII')
        assert self.head[3] == 0
        if self.code != 'END':  # see OPUS_NT/DATA/indi.0, there we have END 00 2E 2E 2E
            self._length = self.head[6] * 2
            assert self.head[5] == 0
            assert self.head[7] == 0
        else:
            assert self.head[4] in (0x00, 0x2E)

    @property
    def type(self):
        return self.head[4]

    def interpretation_of_tail(self):
        ret = None
        if self.code == 'END':
            pass
        elif self.type in (0, 0x10):
            assert len(self.tail) == 4
            ret = struct.unpack('<i', self.tail)[0]
        elif self.type == 1:
            assert len(self.tail) == 8
            ret = struct.unpack('<d', self.tail)[0]
        elif self.type in (2, 3, 4):  # list of values / string
            t = self.tail.find(0)
            ret = self.tail[0:t].decode('ASCII')
        else:
            raise RuntimeError('unknown type %02x: %s' % (self.type, repr(self.head)))
        return ret

    @classmethod
    def from_file(cls, fin):
        obj = cls()
        obj.read_head(fin)
        obj.read_tail(fin)
        return obj

    def __repr__(self):
        return '<Parameter code=%s %d %3d tail=%s>' % (self.code, self.type, len(self.tail), self.interpretation_of_tail())


def read_parameter_list_to_end(fin):
    parameters = []
    while True:
        p = Parameter.from_file(fin)
        parameters.append(p)
        if p.code == 'END':
            break
    return parameters


def read_parameter_list_as_dict_to_end(fin):
    return OrderedDict((p.code, p.interpretation_of_tail()) for p in read_parameter_list_to_end(fin))


class FileHeaderEntry:
    """
    An entry consists of three integers.
    tag
    length
    offset: the file offset
    """

    BINARY_TAGS = {
        0x00000405: "S Sc.R",
        0x00000406: "S Sc.I",
        0x00000407: "S Sc",
        0x00500407: "S Sc/multiple",
        0x0000040b: "R Sc",
        0x00000805: "S Ifg.R",
        0x00000806: "S Ifg.I",
        0x00000807: "S Ifg",
        0x00500807: "S Ifg/multiple",
        0x0000080b: "R Ifg",
        0x00000c07: "S PH",
        0x00000c0b: "R PH",
        0x0000100f: "AB",
        0x0050100f: "AB/multiple",
        0x0000140f: "TR",
        0x0050140f: "TR/multiple",
        0x0000280f: "RAM",
        0x0000300f: "REFL",
        0x00003c0f: "L REFL",
        0x00501c00: "Trace/multiple",
    }

    PARAMETER_TAG_MASK = 0x00000010
    MULTIPLE_TAG_MASK =  0x00500000
    PARAMETER_UNKNOWN_MASK = \
                         0x40000000

    def __init__(self):
        self.tag = None
        self._tag = None  # the key in BINARY_TAGS
        self.length = None
        self.offset = None

    def decode_entry(self, entry_binary):
        self.tag, self.length, self.offset = struct.unpack('<III', entry_binary)
        # the files I had while writing had all the bit set
        # it doesn't seem to be a data format flag
        self._tag = self.tag & (~self.PARAMETER_UNKNOWN_MASK)

    def name_binary(self):
        return self.BINARY_TAGS.get(self._tag, None)

    def is_entry_list(self):
        return self.tag == 0x00003400

    def is_history(self):
        return self.tag == 0x40680000

    def is_binary(self):
        return self._tag in self.BINARY_TAGS

    def is_multiple(self):
        return self.is_binary() and (self.tag & self.MULTIPLE_TAG_MASK)

    def parameter_list_tag(self):
        assert self.is_binary()
        return self.tag | self.PARAMETER_TAG_MASK

    @classmethod
    def from_file(cls, fin):
        obj = cls()
        obj.decode_entry(fin.read(4 * 3))
        return obj

    def __repr__(self):
        return '<Entry %08x %7d %8x>' % (self.tag, self.length, self.offset)


class FileHeader:
    """
    The File Header seems to consist of some unknown values (here called MAGIC)
    plus a list describing the entries that are contained in the file padded with NUL to offset 504.

    MAGIC . length of entry list . list of entries . NUL padding
    """
    MAGIC = b'\x0a\x0a\xfe\xfe\000\000\000\000\xFF\xFF\xFF\x41\x18\000\000\000\x28\000\000\000'
    MMASK = b'\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff'

    def __init__(self):
        self.entries = []  # type: list[FileHeaderEntry]

    @staticmethod
    def _get_difference(magic):
        diff = {}
        for offs, (a, b, m) in enumerate(zip(magic, FileHeader.MAGIC, FileHeader.MMASK)):
            if (m & a) != (m & b):
                diff[offs] = a, b
        if len(diff):
            return '\n'.join('%2i: %s' % (k, diff[k]) for k in sorted(diff.keys()))
        else:
            return None

    @classmethod
    def from_file(cls, fin):
        obj = cls()
        fin.seek(0)
        magic = fin.read(len(cls.MAGIC))
        assert len(magic) == len(cls.MAGIC), 'File %s is too short' % repr(fin)
        if FileHeader._get_difference(magic) is not None:
            raise AssertionError('MAGIC does not match at ' + FileHeader._get_difference(magic))
        number_of_entries, = struct.unpack('<I', fin.read(4))
        for i in range(number_of_entries):
            obj.entries.append(FileHeaderEntry.from_file(fin))
        return obj

    def get_binary_entry(self, entry):
        """
        returns the named binary `entry`
        see FileHeaderEntry.BINARY_TAGS for recognized entry names
        """
        e = [i for i in self.entries if i.is_binary() and i.name_binary() == entry]
        if len(e) == 0:
            raise RuntimeError('entry %s not found' % entry)
        else:
            return e[0]

    def get_parameter_list_entry(self, entry: FileHeaderEntry):
        """returns the parameter list corresponding to `entry`"""
        e = [i for i in self.entries if i.tag == entry.parameter_list_tag()]
        if len(e) == 0:
            raise RuntimeError("no parameter list for entry %s found" % repr(entry))
        else:
            return e[0]
