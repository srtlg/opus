"""
Plot a data block contained in an OPUS file
"""
import argparse
import numpy as np
import matplotlib.pyplot as plt

from opus import FileHeader
from opus.math import calculate_xvalues


def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('-d', '--data', default='S Ifg', help='data set to average, e.g. S Sc or S Ifg')
    p.add_argument('input_files', nargs='+')
    return p.parse_args()


def _extract_data(path, entry):
    with open(path, 'rb') as fin:
        header = FileHeader.from_file(fin)
        entry = header.get_binary_entry(entry)
        xvalues, unit = calculate_xvalues(header.get_parameter_list_entry(entry), fin)
        fin.seek(entry.offset)
        return xvalues, unit, np.fromfile(fin, np.dtype('<f4'), count=entry.length)


def main():
    args = _parse_args()
    data = None
    x = None
    xunit = None
    for i, path in enumerate(args.input_files):
        x, xunit, d = _extract_data(path, args.data)
        if data is None:
            data = np.empty([len(args.input_files), len(d)], np.float32)
        data[i, :] = d
        if len(args.input_files) > 1:
            plt.plot(x, d, linewidth=0.5, color='gray')
    plt.plot(x, np.mean(data, 0))
    if xunit == 'WN':
        plt.xlim(np.max(x), np.min(x))
        plt.xlabel('wavenumber / cm$^{-1}$')
    plt.show()


if __name__ == '__main__':
    main()
