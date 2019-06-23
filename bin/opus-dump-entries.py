"""
Decodes the File Header of an OPUS file
"""
import sys

from opus import FileHeader, Parameter, read_parameter_list_to_end


def main(path):
    with open(path, 'rb') as fin:
        header = FileHeader.from_file(fin)
        for entry in header.entries:
            fin.seek(entry.offset)
            try:
                p = Parameter.from_file(fin)
                tail = repr(p)
                assert not entry.is_binary()
                assert not entry.is_history()
                assert not entry.is_entry_list()
                fin.seek(entry.offset)
                pl = read_parameter_list_to_end(fin)
                tail = '|'.join('%s=%s' % (i.code, i.interpretation_of_tail()) for i in pl)
            except (AssertionError, UnicodeDecodeError, IndexError, RuntimeError):
                tail = '\033[41m NOT DEFINED \033[0m'
            if entry.is_binary():
                tail = '{%s}' % entry.name_binary()
            if entry.is_history():
                tail = '<HISTORY>'
            if entry.is_entry_list():
                tail = '<ENTRY LIST>'
            print(entry, tail)


if __name__ == '__main__':
    main(sys.argv[1])
