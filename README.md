# labman
lab manager for plate maps and sequence flows

# Install
Labman relies on the Qiita database. You will need first to install Qiita in
a different environment (Qiita is Python 2 only, while labman is Python 3) and
create the Qiita database using the [Qiita installation instructions]
(https://github.com/biocore/qiita/blob/master/INSTALL.md).

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

Configure labman by running `labman config` and answer to the configuration questions:

```bash
Path to the configuration file [~/.labman.cfg]:
Main configuration:
Test environment [True]:
Log directory [/tmp/]:
Labman Certificate Filepath []:
Labman Key Filepath []:
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

Finally, apply the SQL patches in the Qiita database so the labman structures
are created:

```bash
psql -d qiita_test -f labman/db/support_files/db_patch.sql
psql -d qiita_test -f labman/db/support_files/db_patch_manual.sql
```

Labman is now ready to run.  Start the labman server with:

```bash
labman start_webserver
```

If it is running successfully, you will see the message `Labman started on port 8080`.
