# labman
lab manager for plate maps and sequence flows

# Install
Labman relies on the Qiita database. You will need first to install Qiita in
a different environment (Qiita is Python 2 only, while labman is Python 3) and
create the Qiita database using the [Qiita installation instructions]
(https://github.com/biocore/qiita/blob/master/INSTALL.md).

Once Qiita is installed, create a new environment for labman and install labman.
For installing labman, install first the qiita_client library:

```bash
pip install https://github.com/qiita-spots/qiita_client/archive/master.zip
```

Then, you can install labman by simply running:

```bash
pip install -e .
```

Configure labman by running labman config and answer to the configuration questions:

```bash
labman config
Path to the configuration file [~/.labman.cfg]:
Main configuration:
Test environment [True]:
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
