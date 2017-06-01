#!/bin/bash

set -e

# Shell script to install Qiita. This file is mainly used in travis. Qiita
# is an optional dependency of labman, and after a short research online
# http://steven.casagrande.io/articles/travis-ci-and-if-statements/
# https://groups.google.com/forum/#!topic/travis-ci/uaAP9zEdiCg
# it looks like having a script file with the if statements is the
# safest way moving forward

if [ ${ENABLE_QIITA} == 'True' ]
then
    # Create a new environment for Qiita
    conda create --yes -n qiita_env python=2.7 pip nose flake8 pyzmq networkx \
        pyparsing natsort mock future libgfortran 'pandas>=0.18' \
        'scipy>0.13.0' 'numpy>=1.7' 'h5py>=2.3.1'

    # Activate the new Qiita environment
    source activate qiita_env

    # Install some other dependencies
    pip install sphinx==1.5.5 sphinx-bootstrap-theme coveralls ipython[all]==2.4.1
    # Install Qiita
    pip install https://github.com/biocore/qiita/archive/master.zip --process-dependency-links

    # Export MOI environment variables
    export MOI_CONFIG_FP=$HOME/miniconda3/envs/qiita_env/lib/python2.7/site-packages/qiita_core/support_files/config_test.cfg

    # Create the ipython profiles and the Qiita environment
    ipython profile create qiita-general --parallel
    qiita-env start_cluster qiita-general
    qiita-env make --no-load-ontologies

    # Start the qiita server in the backend
    qiita pet webserver start &

    # Deactivate the Qiita environment
    source deactivate

    # Set the labman config file to be the config file with Qiita enabled
    cp labman/db/support_files/test_config_qiita.cfg ~/.labman.cfg
else
    # Set the labman config file to be the config file without Qiita enabled
    cp labman/db/support_files/test_config.cfg ~/.labman.cfg
fi
