# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from os import environ
from os.path import expanduser, exists
from datetime import datetime
from configparser import ConfigParser


class ConfigurationManager(object):
    """Holds the labman configuration

    Parameters
    ----------
    conf_fp: str, optional
        Filepath to the configuration file. Default: config_test.cfg

    Attributes
    ----------
    test_environment : bool
        If true, we are in a test environment.
    database : str
        The postgres database to connect to
    user : str
        The postgres user
    password : str
        The postgres password for the previous user
    admin_user : str
        The administrator user, which can be used to create/drop environments
    admin_password : str
        The postgres password for the admin_user
    host : str
        The host where the database lives
    port : int
        The port used to connect to the postgres database in the previous host
    qiita_server_cert : str
        If qiita enabled, the qiita server certificate
    client_id : str
        The client making the request
    client_secret : str
        The secret key for the client
    valid_groups : list-like of str
        qiita user groups allowed to access labman

    Raises
    ------
    RuntimeError
        When an option is no longer available.
    """
    @staticmethod
    def create(config_fp, test_env, db_host, db_port, db_name, db_user,
               db_password, db_admin_user, db_admin_password, log_dir,
               qiita_server_cert, client_id, client_secret, valid_groups):
        """Creates a new labman configuration file

        Parameters
        ----------
        config_fp : str
            Path to the configuration file
        test_env : bool
            If true, a config file for a test environment will be created
        db_host : str
            The host where the database lives
        db_port : int
            The port used to connect to the postgres database in the previous
            host
        db_name : str
            The postgres database to connect to
        db_user : str
            The postgres user
        db_password : str
            The postgres password for the previous user
        db_admin_user : str
            The administrator user, which can be used to create/drop
            environments
        db_admin_password : str
            The postgres password for the admin_user
        log_dir : str
            Path to the log directory
        qiita_server_cert : str
            The qiita server certificate (for testing)
        client_id : str
            The client making the request
        client_secret : str
            The secret key for the client
        valid_groups : str
            comma-separated list of qiita user groups allowed to access labman
        """
        with open(config_fp, 'w') as f:
            f.write(CONFIG_TEMPLATE % {
                'test': test_env,
                'date': str(datetime.now()),
                'user': db_user,
                'admin_user': db_admin_user,
                'password': db_password,
                'admin_password': db_admin_password,
                'database': db_name,
                'host': db_host,
                'port': db_port,
                'logdir': log_dir,
                'qiita_cert': qiita_server_cert,
                'client_id': client_id,
                'client_secret': client_secret,
                'valid_groups': valid_groups})

    def __init__(self):
        # If conf_fp is None, we default to the test configuration file
        try:
            self.conf_fp = environ['LABMAN_CONFIG_FP']
        except KeyError:
            self.conf_fp = expanduser('~/.labman.cfg')
            if not exists(self.conf_fp):
                raise RuntimeError(
                    'Please configure labman using `labman config`. If the '
                    'config file is not in `~/.labman.cfg`, please set the '
                    '`LABMAN_CONFIG_FP` environment variable to the '
                    'configuration file')

        # Parse the configuration file
        config = ConfigParser()
        with open(self.conf_fp, 'U') as conf_file:
            config.readfp(conf_file)

        _required_sections = {'postgres'}
        if not _required_sections.issubset(set(config.sections())):
            missing = _required_sections - set(config.sections())
            raise RuntimeError(', '.join(missing))

        self._get_main(config)
        self._get_postgres(config)
        self._get_qiita(config)

    def _get_main(self, config):
        """Get the main configuration"""
        self.test_environment = config.getboolean('main', 'TEST_ENVIRONMENT')
        self.log_dir = config.get('main', 'LOG_DIR')

    def _get_postgres(self, config):
        """Get the configuration of the postgres section"""
        self.user = config.get('postgres', 'USER')
        self.admin_user = config.get('postgres', 'ADMIN_USER') or None

        self.password = config.get('postgres', 'PASSWORD')
        if not self.password:
            self.password = None

        self.admin_password = config.get('postgres', 'ADMIN_PASSWORD')
        if not self.admin_password:
            self.admin_password = None

        self.database = config.get('postgres', 'DATABASE')
        self.host = config.get('postgres', 'HOST')
        self.port = config.getint('postgres', 'PORT')

    def _get_qiita(self, config):
        self.qiita_server_cert = config.get('qiita', 'SERVER_CERT')
        self.client_id = config.get('qiita', 'CLIENT_ID')
        self.client_secret = config.get('qiita', 'CLIENT_SECRET')
        self.valid_groups = [vg.strip() for vg in config.get(
            'qiita', 'VALID_GROUPS').split(',')]


CONFIG_TEMPLATE = """# Configuration file generated by labman on %(date)s

# ------------------------- MAIN SETTINGS ----------------------------------
[main]
TEST_ENVIRONMENT=%(test)s
LOG_DIR=%(logdir)s

# ----------------------- POSTGRES SETTINGS --------------------------------
[postgres]
USER=%(user)s
PASSWORD=%(password)s
ADMIN_USER=%(admin_user)s
ADMIN_PASSWORD=%(admin_password)s
DATABASE=%(database)s
HOST=%(host)s
PORT=%(port)s

# ------------------------- QIITA SETTINGS ----------------------------------
[qiita]
SERVER_CERT=%(qiita_cert)s
CLIENT_ID=%(client_id)s
CLIENT_SECRET=%(client_secret)s
VALID_GROUPS=%(valid_groups)s
"""
