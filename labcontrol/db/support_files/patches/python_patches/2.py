from labcontrol.db.sql_connection import TRN

import logging
from os import environ

handler = logging.StreamHandler()
fmt_str = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
handler.setFormatter(logging.Formatter(fmt_str))
logger = logging.getLogger(__name__)
logger.addHandler(handler)
debug_levels_list = {'DEBUG': logging.DEBUG,
                     'INFO': logging.INFO,
                     'WARNING': logging.WARNING,
                     'ERROR': logging.ERROR,
                     'CRITICAL': logging.CRITICAL}

if 'LABCONTROL_DEBUG_LEVEL' in environ:
    level = environ['QIITA_CLIENT_DEBUG_LEVEL']
    if level in debug_levels_list:
        logger.setLevel(debug_levels_list[level])
    else:
         raise ValueError(
             "%s is not a valid value for QIITA_CLIENT_DEBUG_LEVEL" % level)
    logger.debug('logging set to %s' % level)
else:
    logger.setLevel(logging.CRITICAL)
    logger.debug('logging set to CRITICAL')

with TRN:
    sql = """SELECT COUNT(*) FROM information_schema.columns
             WHERE table_name = 'library_prep_shotgun_process'
             AND column_name = 'kappa_hyper_plus_kit_id';"""
    logger.debug(sql)
    TRN.add(sql)
    result = TRN.execute_fetchflatten()
    logger.debug(str(result))

    # for now, assume result will be either 0 or 1.
    # if 1, then the column 'kappa_hyper_plus_kit_id' needs
    # to be renamed to 'kapa_hyper_plus_kit_id', otherwise
    # it has already been renamed.
    if result == 1:
        sql = """ALTER TABLE labcontrol.library_prep_shotgun_process RENAME
        COLUMN kappa_hyper_plus_kit_id to kapa_hyper_plus_kit_id;"""
        logger.debug(sql)
        TRN.add(sql)
        TRN.execute()
        TRN.commit()
    else:
        logger.debug('labcontrol.library_prep_shotgun_process unchanged')
