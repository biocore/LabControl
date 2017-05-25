# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from os.path import join, dirname, abspath, basename, splitext, exists
from functools import partial
from glob import glob

from natsort import natsorted

from labman.db.sql_connection import SQLConnectionHandler, TRN
from labman.db.settings import labman_settings


get_support_file = partial(join, join(dirname(abspath(__file__)),
                                      'support_files'))

LAYOUT_FP = get_support_file('lab_manager.sql')
PATCHES_DIR = get_support_file('patches')


def _check_db_exists(db, conn_handler):
    r"""Checks if the database db exists on the postgres server

    Parameters
    ----------
    db : str
        The database
    conn_handler : SQLConnectionHandler
        The connection to the database
    """
    dbs = [x[0] for x in
           conn_handler.execute_fetchall('SELECT datname FROM pg_database')]

    return db in dbs


def create_layout_and_patch(test=False, verbose=False):
    r"""Builds the SQL layout and applies all the patches

    Parameters
    ----------
    verbose : bool, optional
        If true, print the current step. Default: False.
    """
    with TRN:
        if verbose:
            print('Building SQL layout')
        # Create the schema
        with open(LAYOUT_FP, 'U') as f:
            TRN.add(f.read())
        TRN.execute()

        # Insert the settings values to the database
        print('Inserting database metadata')
        sql = """INSERT INTO settings (test) VALUES (%s)"""
        TRN.add(sql, [test])
        TRN.execute()

        if verbose:
            print('Patching Database...')
        patch(verbose=verbose, test=test)


def make_environment():
    r"""Creates the new environment specified in the configuration

    Raises
    ------
    IOError
        If `download_reference` is true but one of the files cannot be
        retrieved
    QiitaEnvironmentError
        If the environment already exists
    """
    # Connect to the postgres server
    admin_conn = SQLConnectionHandler(admin='admin_without_database')

    # Check that it does not already exists
    if _check_db_exists(labman_settings.database, admin_conn):
        raise RuntimeError(
            "Database {0} already present on the system. You can drop it "
            "by running 'labman destroy_environment'".format(
                labman_settings.database))

    # Create the database
    print('Creating database')
    admin_conn.autocommit = True
    admin_conn.execute('CREATE DATABASE %s' % labman_settings.database)
    admin_conn.autocommit = False

    del admin_conn
    SQLConnectionHandler.close()

    with TRN:
        create_layout_and_patch(test=labman_settings.test_environment,
                                verbose=True)

        if labman_settings.test_environment:
            print('Test environment successfully created')
        else:
            print('Production environment successfully created')


def patch(patches_dir=PATCHES_DIR, verbose=False, test=False):
    """Patches the database schema based on the SETTINGS table

    Pulls the current patch from the settings table and applies all subsequent
    patches found in the patches directory.
    """
    with TRN:
        TRN.add("SELECT current_patch FROM settings")
        current_patch = TRN.execute_fetchlast()
        current_sql_patch_fp = join(patches_dir, current_patch)
        corresponding_py_patch = partial(join, patches_dir, 'python_patches')

        sql_glob = join(patches_dir, '*.sql')
        sql_patch_files = natsorted(glob(sql_glob))

        if current_patch == 'unpatched':
            next_patch_index = 0
        elif current_sql_patch_fp not in sql_patch_files:
            raise RuntimeError("Cannot find patch file %s" % current_patch)
        else:
            next_patch_index = sql_patch_files.index(current_sql_patch_fp) + 1

        patch_update_sql = "UPDATE settings SET current_patch = %s"

        for sql_patch_fp in sql_patch_files[next_patch_index:]:
            sql_patch_filename = basename(sql_patch_fp)

            py_patch_fp = corresponding_py_patch(
                splitext(basename(sql_patch_fp))[0] + '.py')
            py_patch_filename = basename(py_patch_fp)

            with open(sql_patch_fp, 'U') as patch_file:
                if verbose:
                    print('\tApplying patch %s...' % sql_patch_filename)
                TRN.add(patch_file.read())
                TRN.add(
                    patch_update_sql, [sql_patch_filename])

            TRN.execute()

            if exists(py_patch_fp):
                if verbose:
                    print('\t\tApplying python patch %s...'
                          % py_patch_filename)
                exec(open(py_patch_fp).read())


def destroy_environment(ask_for_confirmation):
    """Drops the database specified in the configuration

    Parameters
    ----------
    ask_for_confirmation: bool
        If True, ask for confirmation if the database is a production database

    Raises
    ------
    RuntimeError
        If the database doesn't exist
    """
    # Connect to the postgres server
    admin_conn = SQLConnectionHandler(admin='admin_without_database')
    if not _check_db_exists(labman_settings.database, admin_conn):
        raise RuntimeError(
            "Database {0} does not exist in the system. You can create it "
            "by running 'labman create_environment'".format(
                labman_settings.database))

    # Connect to the postgres server
    with TRN:
        TRN.add("SELECT test FROM settings")
        is_test_environment = TRN.execute_fetchlast()

    if is_test_environment:
        do_drop = True
    else:
        if ask_for_confirmation:
            confirm = ''
            while confirm not in ('Y', 'y', 'N', 'n'):
                confirm = input("THIS IS NOT A TEST ENVIRONMENT.\n"
                                "Proceed with drop? (y/n)")

            do_drop = confirm in ('Y', 'y')
        else:
            do_drop = True

    if do_drop:
        # The transaction has an open connection to the database, so we need
        # to make sure that we close all the connections in order to drop
        # the environmnent
        TRN.close()
        SQLConnectionHandler.close()
        admin_conn = SQLConnectionHandler(
            admin='admin_without_database')
        admin_conn.autocommit = True
        admin_conn.execute('DROP DATABASE %s' % labman_settings.database)
        admin_conn.autocommit = False
    else:
        print('ABORTING')
