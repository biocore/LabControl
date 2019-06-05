# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from os.path import join, dirname, abspath, basename, splitext, exists
from glob import glob
from functools import partial

from natsort import natsorted

from labcontrol.db import sql_connection


def patch_database(verbose):
    """Apply patches, if necessary, to the database"""
    get_support_file = partial(join, join(dirname(abspath(__file__)),
                                          'support_files'))
    patches_dir = get_support_file('patches')

    with sql_connection.TRN:
        sql_connection.TRN.add("SELECT current_patch FROM labcontrol.settings")
        try:
            current_patch = sql_connection.TRN.execute_fetchlast()
        except ValueError:
            # the system doesn't have the settings table so is unpatched
            current_patch = 'unpatched'

        current_sql_patch_fp = join(patches_dir, current_patch)
        corresponding_py_patch = partial(join, patches_dir, 'python_patches')

        sql_glob = join(patches_dir, '*.sql')
        sql_patch_files = natsorted(glob(sql_glob))

        if current_patch == 'unpatched':
            next_patch_index = 0
            sql_connection.TRN.add("""CREATE TABLE labcontrol.settings
                                      (current_patch varchar not null)""")
            sql_connection.TRN.add("""INSERT INTO labcontrol.settings
                                      (current_patch) VALUES ('unpatched')""")
            sql_connection.TRN.execute()
        elif current_sql_patch_fp not in sql_patch_files:
            raise RuntimeError("Cannot find patch file %s" % current_patch)
        else:
            next_patch_index = sql_patch_files.index(current_sql_patch_fp) + 1

    patch_update_sql = "UPDATE labcontrol.settings SET current_patch = %s"

    for sql_patch_fp in sql_patch_files[next_patch_index:]:
        sql_patch_filename = basename(sql_patch_fp)

        py_patch_fp = corresponding_py_patch(
            splitext(basename(sql_patch_fp))[0] + '.py')
        py_patch_filename = basename(py_patch_fp)

        with sql_connection.TRN:
            with open(sql_patch_fp, newline=None) as patch_file:
                if verbose:
                    print('\tApplying patch %s...' % sql_patch_filename)
                sql_connection.TRN.add(patch_file.read())
                sql_connection.TRN.add(
                    patch_update_sql, [sql_patch_filename])

            sql_connection.TRN.execute()

            if exists(py_patch_fp):
                if verbose:
                    print('\t\tApplying python patch %s...'
                          % py_patch_filename)
                with open(py_patch_fp) as py_patch:
                    exec(py_patch.read(), globals())
