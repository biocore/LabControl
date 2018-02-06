# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------


class LabmanError(Exception):
    """Base class for all labman exceptions"""
    pass


class LabmanUnknownIdError(LabmanError):
    """Exception for error when an object doesn't exist in the DB

    Parameters
    ----------
    obj_name : str
        The name of the object
    obj_id : str
        The unknown id
    """
    def __init__(self, obj_name, obj_id):
        super(LabmanUnknownIdError, self).__init__()
        self.args = ("%s with ID '%s' does not exist" % (obj_name, obj_id), )


class LabmanDuplicateError(LabmanError):
    """Exception for error when duplicates occur

    Parameters
    ----------
    obj_name : str
        The name of the object
    attributes : list of (str, str)
        The duplicated attributes
    """
    def __init__(self, obj_name, attributes):
        super(LabmanDuplicateError, self).__init__()
        attr = ', '.join(["%s = %s" % (key, val) for key, val in attributes])
        self.args = ("%s with %s already exists" % (obj_name, attr), )


class LabmanLoginError(LabmanError):
    """Exception for error when login in"""
    def __init__(self):
        super(LabmanLoginError, self).__init__()
        self.args = ("Incorrect user id or password", )


class LabmanLoginDisabledError(LabmanError):
    """Exception for error when user is not allowed"""
    def __init__(self):
        super(LabmanLoginDisabledError, self).__init__()
        self.args = ("Login credentials disabled for this portal", )
