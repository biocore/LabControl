# labman
lab manager for plate maps and sequence flows

# Install
Labman relies on the Qiita database. You will need first to install Qiita in
a different environment (Qiita is Python 2 only, while labman is Python 3) and
create the Qiita database using the [Qiita installation instructions](https://github.com/biocore/qiita/blob/master/INSTALL.md).  The instructions 
below assume the Qiita PostgreSQL database is named `qiita_test`, which is the 
default name of the database created by the Qiita installation process; if your 
Qiita installation has a different database name, substitute that for 
`qiita_test` throughout.

Once Qiita is installed, create a new, empty conda environment for labman.  
Source this environment and install labman; start by first installing the
qiita_client library:

```bash
pip install https://github.com/qiita-spots/qiita_client/archive/master.zip
```

and then cloning the labman repository:

```bash
git clone https://github.com/jdereus/labman.git
```

You can then install labman by simply running:

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

Configure labman by running `labman config` and answer to the configuration questions:

```bash
Path to the configuration file [~/.labman.cfg]:
Main configuration:
Test environment [True]:
Log directory [/tmp/]:
Labman Certificate Filepath []: /PATH/TO/labman/support_files/server.crt
Labman Key Filepath []: /PATH/TO/labman/support_files/server.key
Postgres configuration:
Postgres host [localhost]:
Postgres port [5432]:
Database name [qiita]:
Postgres user [labman]:
Postgres user password []:
Postgres admin user [labman]:
Postgres admin user password []:
Qiita configuration (for testing purposes):
Qiita server certificate []: /PATH/TO/qiita_core/support_files/server.crt
```

Apply the SQL patches in the Qiita database so the basic labman structures
are created:

```bash
psql -d qiita_test -f labman/db/support_files/db_patch.sql
psql -d qiita_test -f labman/db/support_files/db_patch_manual.sql
```

If creating a development environment for labman, then run:

```bash
psql -d qiita_test -f labman/db/support_files/populate_test_db.sql
```

to set up the database to support running the unit tests.  Alternately, if 
creating a production or production-like environment, run:

```bash
psql -d qiita_test -f labman/db/support_files/populate_prod_db.sql
```

Note that the postgres user specified for the labman software (`labman` in the config example above) 
must be granted "select" permissions on all tables in the "qiita" schema and "all" permissions on
all tables in the "labman" schema, as well as being the owner of all tables in the "labman" schema.  
These ownerships and permissions can be granted with SQL like that shown below, after setting the
USER variable to be the postgres user specified for the labman software and DB to be the 
database name for your Qiita installation:

```bash
USER=labman
DB=qiita_test
SCHEMA=labman
psql -d qiita_test -c "create role labman;"
for table in `psql -tc "select tablename from pg_tables where schemaname = '${SCHEMA}';" ${DB}` ; do psql -c "alter table ${SCHEMA}.${table} owner to ${USER}" ${DB}; done
psql -d qiita_test -c "Grant select on all tables in schema qiita to ${USER};"
psql -d qiita_test -c "Grant all on all tables in schema labman to ${USER};"
```

Labman is now ready to run.  Start the labman server with:

```bash
labman start-webserver
```

If it is running successfully, you will see the message `Labman started on port 8080`.  Note that 
by default, labman starts on port 8080; if you would like to start it on a different port, 
use the optional `--port` switch, as shown in the below example to start it on port 5555:

```bash
labman start-webserver --port 5555
```
