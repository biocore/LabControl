# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------


class LabcontrolError(Exception):
    """Base class for all labcontrol exceptions"""
    pass


class LabcontrolUnknownIdError(LabcontrolError):
    """Exception for error when an object doesn't exist in the DB

    Parameters
    ----------
    obj_name : str
        The name of the object
    obj_id : str
        The unknown id
    """
    def __init__(self, obj_name, obj_id):
        super(LabcontrolUnknownIdError, self).__init__()
        self.args = ("%s with ID '%s' does not exist" % (obj_name, obj_id), )


class LabcontrolDuplicateError(LabcontrolError):
    """Exception for error when duplicates occur

    Parameters
    ----------
    obj_name : str
        The name of the object
    attributes : list of (str, str)
        The duplicated attributes
    """
    def __init__(self, obj_name, attributes):
        super(LabcontrolDuplicateError, self).__init__()
        attr = ', '.join(["%s = %s" % (key, val) for key, val in attributes])
        self.args = ("%s with %s already exists" % (obj_name, attr), )


class LabcontrolLoginError(LabcontrolError):
    """Exception for error when login in"""
    def __init__(self):
        super(LabcontrolLoginError, self).__init__()
        self.args = ("Incorrect user id or password", )


class LabcontrolLoginDisabledError(LabcontrolError):
    """Exception for error when user is not allowed"""
    def __init__(self):
        super(LabcontrolLoginDisabledError, self).__init__()
        self.args = ("Login credentials disabled for this portal", )
