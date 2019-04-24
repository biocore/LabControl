# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------


class LabControlError(Exception):
    """Base class for all labcontrol exceptions"""
    pass


class LabControlUnknownIdError(LabControlError):
    """Exception for error when an object doesn't exist in the DB

    Parameters
    ----------
    obj_name : str
        The name of the object
    obj_id : str
        The unknown id
    """
    def __init__(self, obj_name, obj_id):
        super(LabControlUnknownIdError, self).__init__()
        self.args = ("%s with ID '%s' does not exist" % (obj_name, obj_id), )


class LabControlDuplicateError(LabControlError):
    """Exception for error when duplicates occur

    Parameters
    ----------
    obj_name : str
        The name of the object
    attributes : list of (str, str)
        The duplicated attributes
    """
    def __init__(self, obj_name, attributes):
        super(LabControlDuplicateError, self).__init__()
        attr = ', '.join(["%s = %s" % (key, val) for key, val in attributes])
        self.args = ("%s with %s already exists" % (obj_name, attr), )


class LabControlLoginError(LabControlError):
    """Exception for error when login in"""
    def __init__(self):
        super(LabControlLoginError, self).__init__()
        self.args = ("Incorrect user id or password", )


class LabControlLoginDisabledError(LabControlError):
    """Exception for error when user is not allowed"""
    def __init__(self):
        super(LabControlLoginDisabledError, self).__init__()
        self.args = ("Login credentials disabled for this portal", )
