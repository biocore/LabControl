# LabControl
[![Build Status](https://travis-ci.org/biocore/LabControl.svg?branch=master)](https://travis-ci.org/biocore/LabControl)

lab manager for plate maps and sequence flows

# Install
LabControl relies on the Qiita database and webserver. You will need first to 
install Qiita in a different environment than LabControl using the [Qiita installation instructions](https://github.com/biocore/qiita/blob/master/INSTALL.md).  
(It is also necessary to start the qiita webserver on port 8383, rather than
the default port for qiita of 21174; this can be done with the command 
 `qiita pet webserver start --port 8383` .) The instructions
below assume the Qiita PostgreSQL database is named `qiita_test`, which is the
default name of the database created by the Qiita installation process; if your
Qiita installation has a different database name, substitute that for
`qiita_test` throughout.

Once Qiita is installed, create a new, empty conda environment for LabControl.
Source this environment and install LabControl; start by first installing the
qiita_client library:

```bash
pip install https://github.com/qiita-spots/qiita_client/archive/master.zip
```

and then cloning the LabControl repository:

```bash
git clone https://github.com/biocore/LabControl.git
```

You can then install LabControl by simply running:

```bash
pip install -e .
```

Generate a certificate for HTTPS (note that the below command uses default values,
but of course we suggest changing them):

```bash
mkdir -p support_files
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout support_files/server.key \
    -out support_files/server.crt \
    -subj "/C=US/ST=CA/L=LaJolla/O=/CN=localhost"
```

Configure LabControl by running `labcontrol config` and answer to the configuration questions:

```bash
Path to the configuration file [~/.labcontrol.cfg]:
Main configuration:
Test environment [True]:
Log directory [/tmp/]:
LabControl Certificate Filepath []: /PATH/TO/labcontrol/support_files/server.crt
LabControl Key Filepath []: /PATH/TO/labcontrol/support_files/server.key
Server cookie secret (default: random) ['random-key']:
Postgres configuration:
Postgres host [localhost]:
Postgres port [5432]:
Database name [qiita]:
Postgres user [labcontrol]:
Postgres user password []:
Postgres admin user [labcontrol]:
Postgres admin user password []:
Qiita configuration (for testing purposes):
Qiita server certificate []: /PATH/TO/qiita_core/support_files/server.crt
```

Apply the SQL patches in the Qiita database so the basic LabControl structures
are created:

```bash
psql -d qiita_test -f labcontrol/db/support_files/db_patch.sql
psql -d qiita_test -f labcontrol/db/support_files/db_patch_manual.sql
```

If creating a development environment for LabControl, then run:

```bash
psql -d qiita_test -f labcontrol/db/support_files/populate_test_db.sql
```

to set up the database to support running the unit tests.  Alternately, if
creating a production or production-like environment, run:

```bash
psql -d qiita_test -f labcontrol/db/support_files/populate_prod_db.sql
```

Note that the postgres user specified for the LabControl software (`labcontrol` in the config example above)
must be granted "select" permissions on all tables in the "qiita" schema and "all" permissions on
all tables in the "labcontrol" schema, as well as being the owner of all tables in the "labcontrol" schema.  
These ownerships and permissions can be granted with SQL like that shown below, after setting the
USER variable to be the postgres user specified for the LabControl software and DB to be the
database name for your Qiita installation:

```bash
USER=labcontrol
DB=qiita_test
SCHEMA=labcontrol
for table in `psql -tc "select tablename from pg_tables where schemaname = '${SCHEMA}';" ${DB}` ; do psql -c "alter table ${SCHEMA}.${table} owner to ${USER}" ${DB}; done
psql -d qiita-test -c "Grant select on all tables in schema qiita to ${USER};"
psql -d qiita-test -c "Grant all on all tables in schema labcontrol to ${USER};"
```

LabControl is now ready to run.  Start the LabControl server with:

```bash
labcontrol start-webserver
```

If it is running successfully, you will see the message `LabControl started on port 8181`.  Note that
by default, LabControl starts on port 8181; if you would like to start it on a different port,
use the optional `--port` switch, as shown in the below example to start it on port 5555:

```bash
labcontrol start-webserver --port 5555
```
