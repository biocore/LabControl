# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import TestCase, main
from os import remove, close
from os.path import exists
from tempfile import mkstemp

from psycopg2._psycopg import connection
from psycopg2.extras import DictCursor
from psycopg2 import connect
from psycopg2.extensions import TRANSACTION_STATUS_IDLE


from labman.db.settings import labman_settings
from labman.db.sql_connection import SQLConnectionHandler, Transaction, TRN


DB_CREATE_TEST_TABLE = """CREATE TABLE labman.test_table (
    str_column      varchar DEFAULT 'foo' NOT NULL,
    bool_column     bool DEFAULT True NOT NULL,
    int_column      bigint NOT NULL);"""

DB_DROP_TEST_TABLE = """DROP TABLE IF EXISTS labman.test_table;"""


class TestBase(TestCase):
    def setUp(self):

        # Add the test table to the database, so we can use it in the tests
        with connect(user=labman_settings.user,
                     password=labman_settings.password,
                     host=labman_settings.host, port=labman_settings.port,
                     database=labman_settings.database) as self.con:
            with self.con.cursor() as cur:
                cur.execute(DB_CREATE_TEST_TABLE)
        self.con.commit()
        self._files_to_remove = []
        self.conn_handler = SQLConnectionHandler()

    def tearDown(self):
        for fp in self._files_to_remove:
            if exists(fp):
                remove(fp)

        with self.con.cursor() as cur:
            cur.execute(DB_DROP_TEST_TABLE)
        self.con.commit()

    def _populate_test_table(self):
        """Aux function that populates the test table"""
        sql = """INSERT INTO labman.test_table
                    (str_column, bool_column, int_column)
                 VALUES (%s, %s, %s)"""
        sql_args = [('test1', True, 1), ('test2', True, 2),
                    ('test3', False, 3), ('test4', False, 4)]
        with self.con.cursor() as cur:
            cur.executemany(sql, sql_args)
        self.con.commit()

    def _assert_sql_equal(self, exp):
        """Aux function for testing"""
        with connect(user=labman_settings.user,
                     password=labman_settings.password,
                     host=labman_settings.host, port=labman_settings.port,
                     database=labman_settings.database) as con:
            with con.cursor() as cur:
                cur.execute("SELECT * FROM labman.test_table")
                obs = cur.fetchall()
            con.commit()

        self.assertEqual(obs, exp)


class TestConnHandler(TestBase):
    def test_init(self):
        obs = SQLConnectionHandler()
        self.assertEqual(obs.admin, 'no_admin')
        self.assertEqual(obs.queues, {})
        self.assertTrue(isinstance(obs._connection, connection))
        self.assertEqual(self.conn_handler._user_conn.closed, 0)

        # Let's close the connection and make sure that it gets reopened
        obs.close()
        obs = SQLConnectionHandler()
        self.assertEqual(self.conn_handler._user_conn.closed, 0)

    def test_init_admin_error(self):
        with self.assertRaises(ValueError):
            SQLConnectionHandler(admin='not a valid value')

    def test_init_admin_with_database(self):
        obs = SQLConnectionHandler(
            admin='admin_with_database')
        self.assertEqual(obs.admin, 'admin_with_database')
        self.assertEqual(obs.queues, {})
        self.assertTrue(isinstance(obs._connection, connection))
        self.assertEqual(self.conn_handler._user_conn.closed, 0)

    def test_init_admin_without_database(self):
        obs = SQLConnectionHandler(
            admin='admin_without_database')
        self.assertEqual(obs.admin, 'admin_without_database')
        self.assertEqual(obs.queues, {})
        self.assertTrue(isinstance(obs._connection, connection))
        self.assertEqual(self.conn_handler._user_conn.closed, 0)

    def test_close(self):
        self.assertEqual(self.conn_handler._user_conn.closed, 0)
        self.conn_handler.close()
        self.assertNotEqual(self.conn_handler._user_conn.closed, 0)

    def test_get_postgres_cursor(self):
        with self.conn_handler.get_postgres_cursor() as cur:
            self.assertEqual(type(cur), DictCursor)

    def test_autocommit(self):
        self.assertFalse(self.conn_handler.autocommit)
        self.conn_handler._connection.autocommit = True
        self.assertTrue(self.conn_handler.autocommit)
        self.conn_handler._connection.autocommit = False
        self.assertFalse(self.conn_handler.autocommit)

    def test_autocommit_setter(self):
        self.assertFalse(self.conn_handler.autocommit)
        self.conn_handler.autocommit = True
        self.assertTrue(self.conn_handler.autocommit)
        self.conn_handler.autocommit = False
        self.assertFalse(self.conn_handler.autocommit)

    def test_autocommit_setter_error(self):
        with self.assertRaises(TypeError):
            self.conn_handler.autocommit = 'not a valid value'

    def test_check_sql_args(self):
        self.conn_handler._check_sql_args(['a', 'list'])
        self.conn_handler._check_sql_args(('a', 'tuple'))
        self.conn_handler._check_sql_args({'a': 'dict'})
        self.conn_handler._check_sql_args(None)

    def test_check_sql_args_error(self):
        with self.assertRaises(TypeError):
            self.conn_handler._check_sql_args("a string")

        with self.assertRaises(TypeError):
            self.conn_handler._check_sql_args(1)

        with self.assertRaises(TypeError):
            self.conn_handler._check_sql_args(1.2)

    def test_sql_executor_no_sql_args(self):
        sql = "INSERT INTO labman.test_table (int_column) VALUES (1)"
        with self.conn_handler._sql_executor(sql) as cur:
            self.assertEqual(type(cur), DictCursor)

        self._assert_sql_equal([('foo', True, 1)])

    def test_sql_executor_with_sql_args(self):
        sql = "INSERT INTO labman.test_table (int_column) VALUES (%s)"
        with self.conn_handler._sql_executor(sql, sql_args=(1,)) as cur:
            self.assertEqual(type(cur), DictCursor)

        self._assert_sql_equal([('foo', True, 1)])

    def test_sql_executor_many(self):
        sql = "INSERT INTO labman.test_table (int_column) VALUES (%s)"
        sql_args = [(1,), (2,)]
        with self.conn_handler._sql_executor(sql, sql_args=sql_args,
                                             many=True) as cur:
            self.assertEqual(type(cur), DictCursor)

        self._assert_sql_equal([('foo', True, 1), ('foo', True, 2)])

    def test_execute_no_sql_args(self):
        sql = "INSERT INTO labman.test_table (int_column) VALUES (1)"
        self.conn_handler.execute(sql)
        self._assert_sql_equal([('foo', True, 1)])

    def test_execute_with_sql_args(self):
        sql = "INSERT INTO labman.test_table (int_column) VALUES (%s)"
        self.conn_handler.execute(sql, (1,))
        self._assert_sql_equal([('foo', True, 1)])

    def test_executemany(self):
        sql = "INSERT INTO labman.test_table (int_column) VALUES (%s)"
        self.conn_handler.executemany(sql, [(1,), (2,)])
        self._assert_sql_equal([('foo', True, 1), ('foo', True, 2)])

    def test_execute_fetchone_no_sql_args(self):
        self._populate_test_table()
        sql = "SELECT str_column FROM labman.test_table WHERE int_column = 1"
        obs = self.conn_handler.execute_fetchone(sql)
        self.assertEqual(obs, ['test1'])

    def test_execute_fetchone_with_sql_args(self):
        self._populate_test_table()
        sql = "SELECT str_column FROM labman.test_table WHERE int_column = %s"
        obs = self.conn_handler.execute_fetchone(sql, (2,))
        self.assertEqual(obs, ['test2'])

    def test_execute_fetchall_no_sql_args(self):
        self._populate_test_table()
        sql = "SELECT * FROM labman.test_table WHERE bool_column = False"
        obs = self.conn_handler.execute_fetchall(sql)
        self.assertEqual(obs, [['test3', False, 3], ['test4', False, 4]])

    def test_execute_fetchall_with_sql_args(self):
        self._populate_test_table()
        sql = "SELECT * FROM labman.test_table WHERE bool_column = %s"
        obs = self.conn_handler.execute_fetchall(sql, (True,))
        self.assertEqual(obs, [['test1', True, 1], ['test2', True, 2]])


class TestTransaction(TestBase):
    def test_init(self):
        obs = Transaction()
        self.assertEqual(obs._queries, [])
        self.assertEqual(obs._results, [])
        self.assertEqual(obs._connection, None)
        self.assertEqual(obs._contexts_entered, 0)
        with obs:
            pass
        self.assertTrue(isinstance(obs._connection, connection))

    def test_add(self):
        with TRN:
            self.assertEqual(TRN._queries, [])

            sql1 = "INSERT INTO labman.test_table (bool_column) VALUES (%s)"
            args1 = [True]
            TRN.add(sql1, args1)
            sql2 = "INSERT INTO labman.test_table (int_column) VALUES (1)"
            TRN.add(sql2)
            args3 = (False,)
            TRN.add(sql1, args3)
            sql3 = """INSERT INTO labman.test_table (int_column)
                      VALEUS (%(foo)s)"""
            args4 = {'foo': 1}
            TRN.add(sql3, args4)

            exp = [(sql1, args1), (sql2, None), (sql1, args3), (sql3, args4)]
            self.assertEqual(TRN._queries, exp)

            # Remove queries so __exit__ doesn't try to execute it
            TRN._queries = []

    def test_add_many(self):
        with TRN:
            self.assertEqual(TRN._queries, [])

            sql = "INSERT INTO labman.test_table (int_column) VALUES (%s)"
            args = [[1], [2], [3]]
            TRN.add(sql, args, many=True)

            exp = [(sql, [1]), (sql, [2]), (sql, [3])]
            self.assertEqual(TRN._queries, exp)

    def test_add_error(self):
        with TRN:
            with self.assertRaises(TypeError):
                TRN.add("SELECT 42", 1)

            with self.assertRaises(TypeError):
                TRN.add("SELECT 42", {'foo': 'bar'}, many=True)

            with self.assertRaises(TypeError):
                TRN.add("SELECT 42", [1, 1], many=True)

    def test_execute(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s)"""
            TRN.add(sql, ["test_insert", 2])
            sql = """UPDATE labman.test_table
                     SET int_column = %s, bool_column = %s
                     WHERE str_column = %s"""
            TRN.add(sql, [20, False, "test_insert"])
            obs = TRN.execute()
            self.assertEqual(obs, [None, None])
            self._assert_sql_equal([])

        self._assert_sql_equal([("test_insert", False, 20)])

    def test_execute_many(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s)"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)
            sql = """UPDATE labman.test_table
                     SET int_column = %s, bool_column = %s
                     WHERE str_column = %s"""
            TRN.add(sql, [20, False, 'insert2'])
            obs = TRN.execute()
            self.assertEqual(obs, [None, None, None, None])

            self._assert_sql_equal([])

        self._assert_sql_equal([('insert1', True, 1),
                                ('insert3', True, 3),
                                ('insert2', False, 20)])

    def test_execute_return(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
            TRN.add(sql, ['test_insert', 2])
            sql = """UPDATE labman.test_table SET bool_column = %s
                     WHERE str_column = %s RETURNING int_column"""
            TRN.add(sql, [False, 'test_insert'])
            obs = TRN.execute()
            self.assertEqual(obs, [[['test_insert', 2]], [[2]]])

    def test_execute_return_many(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)
            sql = """UPDATE labman.test_table SET bool_column = %s
                     WHERE str_column = %s"""
            TRN.add(sql, [False, 'insert2'])
            sql = "SELECT * FROM labman.test_table"
            TRN.add(sql)
            obs = TRN.execute()
            exp = [[['insert1', 1]],  # First query of the many query
                   [['insert2', 2]],  # Second query of the many query
                   [['insert3', 3]],  # Third query of the many query
                   None,  # Update query
                   [['insert1', True, 1],  # First result select
                    ['insert3', True, 3],  # Second result select
                    ['insert2', False, 2]]]  # Third result select
            self.assertEqual(obs, exp)

    def test_execute_huge_transaction(self):
        with TRN:
            # Add a lot of inserts to the transaction
            sql = "INSERT INTO labman.test_table (int_column) VALUES (%s)"
            for i in range(1000):
                TRN.add(sql, [i])
            # Add some updates to the transaction
            sql = """UPDATE labman.test_table SET bool_column = %s
                     WHERE int_column = %s"""
            for i in range(500):
                TRN.add(sql, [False, i])
            # Make the transaction fail with the last insert
            sql = """INSERT INTO labman.table_to_make (the_trans_to_fail)
                     VALUES (1)"""
            TRN.add(sql)

            with self.assertRaises(ValueError):
                TRN.execute()

            # make sure rollback correctly
            self._assert_sql_equal([])

    def test_execute_commit_false(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)

            obs = TRN.execute()
            exp = [[['insert1', 1]], [['insert2', 2]], [['insert3', 3]]]
            self.assertEqual(obs, exp)

            self._assert_sql_equal([])

            TRN.commit()

            self._assert_sql_equal([('insert1', True, 1), ('insert2', True, 2),
                                    ('insert3', True, 3)])

    def test_execute_commit_false_rollback(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)

            obs = TRN.execute()
            exp = [[['insert1', 1]], [['insert2', 2]], [['insert3', 3]]]
            self.assertEqual(obs, exp)

            self._assert_sql_equal([])

            TRN.rollback()

            self._assert_sql_equal([])

    def test_execute_commit_false_wipe_queries(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)

            obs = TRN.execute()
            exp = [[['insert1', 1]], [['insert2', 2]], [['insert3', 3]]]
            self.assertEqual(obs, exp)

            self._assert_sql_equal([])

            sql = """UPDATE labman.test_table SET bool_column = %s
                     WHERE str_column = %s"""
            args = [False, 'insert2']
            TRN.add(sql, args)
            self.assertEqual(TRN._queries, [(sql, args)])

            TRN.execute()
            self._assert_sql_equal([])

        self._assert_sql_equal([('insert1', True, 1), ('insert3', True, 3),
                                ('insert2', False, 2)])

    def test_execute_fetchlast(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)

            sql = """SELECT EXISTS(
                        SELECT * FROM labman.test_table WHERE int_column=%s)"""
            TRN.add(sql, [2])
            self.assertTrue(TRN.execute_fetchlast())

            sql = """SELECT str_column FROM labman.test_table
                     WHERE int_column = %s"""
            TRN.add(sql, [2])
            self.assertEqual(TRN.execute_fetchlast(), 'insert2')

            TRN.add(sql, [4])
            self.assertIsNone(TRN.execute_fetchlast())

    def test_execute_fetchindex(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)
            self.assertEqual(TRN.execute_fetchindex(),
                             [['insert3', 3]])

            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert4', 4], ['insert5', 5], ['insert6', 6]]
            TRN.add(sql, args, many=True)
            self.assertEqual(TRN.execute_fetchindex(3),
                             [['insert4', 4]])

    def test_execute_fetchflatten(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s)"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)

            sql = "SELECT str_column, int_column FROM labman.test_table"
            TRN.add(sql)

            sql = "SELECT int_column FROM labman.test_table"
            TRN.add(sql)
            obs = TRN.execute_fetchflatten()
            self.assertEqual(obs, [1, 2, 3])

            sql = "SELECT 42"
            TRN.add(sql)
            obs = TRN.execute_fetchflatten(idx=3)
            self.assertEqual(obs, ['insert1', 1, 'insert2', 2, 'insert3', 3])

    def test_context_manager_rollback(self):
        try:
            with TRN:
                sql = """INSERT INTO labman.test_table (str_column, int_column)
                     VALUES (%s, %s) RETURNING str_column, int_column"""
                args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
                TRN.add(sql, args, many=True)

                TRN.execute()
                raise ValueError("Force exiting the context manager")
        except ValueError:
            pass
        self._assert_sql_equal([])
        self.assertEqual(
            TRN._connection.get_transaction_status(),
            TRANSACTION_STATUS_IDLE)

    def test_context_manager_execute(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                 VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)
            self._assert_sql_equal([])

        self._assert_sql_equal([('insert1', True, 1), ('insert2', True, 2),
                                ('insert3', True, 3)])
        self.assertEqual(
            TRN._connection.get_transaction_status(),
            TRANSACTION_STATUS_IDLE)

    def test_context_manager_no_commit(self):
        with TRN:
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                 VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)

            TRN.execute()
            self._assert_sql_equal([])

        self._assert_sql_equal([('insert1', True, 1), ('insert2', True, 2),
                                ('insert3', True, 3)])
        self.assertEqual(
            TRN._connection.get_transaction_status(),
            TRANSACTION_STATUS_IDLE)

    def test_context_manager_multiple(self):
        self.assertEqual(TRN._contexts_entered, 0)

        with TRN:
            self.assertEqual(TRN._contexts_entered, 1)

            TRN.add("SELECT 42")
            with TRN:
                self.assertEqual(TRN._contexts_entered, 2)
                sql = """INSERT INTO labman.test_table (str_column, int_column)
                         VALUES (%s, %s) RETURNING str_column, int_column"""
                args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
                TRN.add(sql, args, many=True)

            # We exited the second context, nothing should have been executed
            self.assertEqual(TRN._contexts_entered, 1)
            self.assertEqual(
                TRN._connection.get_transaction_status(),
                TRANSACTION_STATUS_IDLE)
            self._assert_sql_equal([])

        # We have exited the first context, everything should have been
        # executed and committed
        self.assertEqual(TRN._contexts_entered, 0)
        self._assert_sql_equal([('insert1', True, 1), ('insert2', True, 2),
                                ('insert3', True, 3)])
        self.assertEqual(
            TRN._connection.get_transaction_status(),
            TRANSACTION_STATUS_IDLE)

    def test_context_manager_multiple_2(self):
        self.assertEqual(TRN._contexts_entered, 0)

        def tester():
            self.assertEqual(TRN._contexts_entered, 1)
            with TRN:
                self.assertEqual(TRN._contexts_entered, 2)
                sql = """SELECT EXISTS(
                        SELECT * FROM labman.test_table WHERE int_column=%s)"""
                TRN.add(sql, [2])
                self.assertTrue(TRN.execute_fetchlast())
            self.assertEqual(TRN._contexts_entered, 1)

        with TRN:
            self.assertEqual(TRN._contexts_entered, 1)
            sql = """INSERT INTO labman.test_table (str_column, int_column)
                         VALUES (%s, %s) RETURNING str_column, int_column"""
            args = [['insert1', 1], ['insert2', 2], ['insert3', 3]]
            TRN.add(sql, args, many=True)
            tester()
            self.assertEqual(TRN._contexts_entered, 1)
            self._assert_sql_equal([])

        self.assertEqual(TRN._contexts_entered, 0)
        self._assert_sql_equal([('insert1', True, 1), ('insert2', True, 2),
                                ('insert3', True, 3)])
        self.assertEqual(
            TRN._connection.get_transaction_status(),
            TRANSACTION_STATUS_IDLE)

    def test_post_commit_funcs(self):
        fd, fp = mkstemp()
        close(fd)
        self._files_to_remove.append(fp)

        def func(fp):
            with open(fp, 'w') as f:
                f.write('\n')

        with TRN:
            TRN.add("SELECT 42")
            TRN.add_post_commit_func(func, fp)

        self.assertTrue(exists(fp))

    def test_post_commit_funcs_error(self):
        def func():
            raise ValueError()

        with self.assertRaises(RuntimeError):
            with TRN:
                TRN.add("SELECT 42")
                TRN.add_post_commit_func(func)

    def test_post_rollback_funcs(self):
        fd, fp = mkstemp()
        close(fd)
        self._files_to_remove.append(fp)

        def func(fp):
            with open(fp, 'w') as f:
                f.write('\n')

        with TRN:
            TRN.add("SELECT 42")
            TRN.add_post_rollback_func(func, fp)
            TRN.rollback()

        self.assertTrue(exists(fp))

    def test_post_rollback_funcs_error(self):
        def func():
            raise ValueError()

        with self.assertRaises(RuntimeError):
            with TRN:
                TRN.add("SELECT 42")
                TRN.add_post_rollback_func(func)
                TRN.rollback()

    def test_context_manager_checker(self):
        with self.assertRaises(RuntimeError):
            TRN.add("SELECT 42")

        with self.assertRaises(RuntimeError):
            TRN.execute()

        with self.assertRaises(RuntimeError):
            TRN.commit()

        with self.assertRaises(RuntimeError):
            TRN.rollback()

        with TRN:
            TRN.add("SELECT 42")

        with self.assertRaises(RuntimeError):
            TRN.execute()

    def test_index(self):
        with TRN:
            self.assertEqual(TRN.index, 0)

            TRN.add("SELECT 42")
            self.assertEqual(TRN.index, 1)

            sql = "INSERT INTO labman.test_table (int_column) VALUES (%s)"
            args = [[1], [2], [3]]
            TRN.add(sql, args, many=True)
            self.assertEqual(TRN.index, 4)

            TRN.execute()
            self.assertEqual(TRN.index, 4)

            TRN.add(sql, args, many=True)
            self.assertEqual(TRN.index, 7)

        self.assertEqual(TRN.index, 0)


if __name__ == "__main__":
    main()
