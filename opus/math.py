"""
Functions requiring numpy
"""
import numpy as np

from .opus import FileHeaderEntry, read_parameter_list_as_dict_to_end


def calculate_xvalues(plist_entry: FileHeaderEntry, fin):
    fin.seek(plist_entry.offset)
    pl = read_parameter_list_as_dict_to_end(fin)
    npt = pl['NPT']
    fxv = pl['FXV']
    lxv = pl['LXV']
    return np.linspace(fxv, lxv, npt), pl['DXU']
