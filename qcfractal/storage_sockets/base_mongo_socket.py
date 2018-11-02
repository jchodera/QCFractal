"""
Database connection class which directly calls the PyMongo API to capture
common subroutines.
"""

try:
    import pymongo
except ImportError:
    raise ImportError(
        "Mongostorage_socket requires pymongo, please install this python module or try a different db_socket.")

import collections
import copy
import datetime
import logging

import bcrypt
import bson.errors
import pandas as pd
from bson.objectid import ObjectId

from . import storage_utils
# Pull in the hashing algorithms from the client
from .. import interface
from abc import ABC
from typing import List, Set, Dict, Tuple, Optional, Union

def _translate_id_index(index):
    if index in ["id", "ids"]:
        return "_id"
    else:
        raise KeyError("Id Index alias '{}' not understood".format(index))


def _str_to_indices(ids):
    for num, x in enumerate(ids):
        if isinstance(x, str):
            ids[num] = ObjectId(x)


def _str_to_indices_with_errors(ids):
    if isinstance(ids, str):
        ids = [ids]

    good = []
    bad = []
    for x in ids:
        if isinstance(x, str):
            try:
                good.append(ObjectId(x))
            except bson.errors.InvalidId:
                bad.append(x)
        elif isinstance(x, ObjectId):
            good.append(x)
        else:
            bad.append(x)
    return good, bad


class BaseMongoSocket(ABC):
    """
    This is a Base classs for Mongo QCDB socket classes.
    """

    def __init__(self,
                 uri,
                 project="molssidb",
                 bypass_security=False,
                 authMechanism="SCRAM-SHA-1",
                 authSource=None,
                 logger=None,
                 max_limit=1000): # FIXME define in confige
        """
        Constructs a new socket where url and port points towards a Mongod instance.

        """

        # Logging data
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)

        # Secuity
        self._bypass_security = bypass_security

        # Build MongoClient
        self.client = pymongo.MongoClient(uri)
        expanded_uri = pymongo.uri_parser.parse_uri(uri)
        if expanded_uri["password"] is not None:
            self.client = pymongo.MongoClient(uri, authMechanism=authMechanism, authSource=authSource)
        else:
            self.client = pymongo.MongoClient(uri)
        self._url, self._port = expanded_uri["nodelist"][0]
        self._project_name = project
        self._tables = self.client[project]
        self._max_limit = max_limit     # will be enforced in all queries

    # ----------------- Mongo meta functions
    #
    def __str__(self):
        return "<MongoSocket: address='{0:s}:{1:d}>".format(str(self._url), self._port)

    def init_database(self):
        """
        Builds out the initial project structure if needed.

        This is the Mongo definition of "Database"
        """
        pass

    def get_project_name(self):
        return self._project_name

    def mixed_molecule_get(self, data):
        """TODO: describe data"""
        return storage_utils.mixed_molecule_get(self, data)

    # TODO: add methods with specifically what needed
    # def locator(self, locator):
    #     """Simple query by locator object
    #
    #     Parameters
    #     ----------
    #     locator : dict
    #         A dictionary with the following fields:
    #             - table: The table to query on
    #             - index: The index to query on
    #             - data: The queries to search fo
    #             - projection: optional, the projection to apply
    #
    #     Returns
    #     -------
    #     dict
    #         The requested location
    #     """
    #     projection = locator.get("projection", None)
    #     return self._get_generic({locator["index"]: locator["data"]}, locator["table"], projection=projection)

    # ---------------------- Mongo molecule functions -------------------------
    #

    def add_molecules(self, data: Union[List[dict], dict],
                      return_json=True, with_ids=True):
        """
        Adds molecules to the database.

        Parameters
        ----------
        data : list of dict of molecule-like JSON objects
            A {key: molecule} dictionary of molecules to input.
            should have same names as the fields in the dB
            preferrably, they should be pydantic objects later

        Returns
        -------
        dict (specity here) TODO

        """

        # Build a dictionary of new molecules
        pass

    def get_molecules(self, molecule_ids: List[str]=None,
                            molecule_hashs: List[str]=None,
                            return_json=True, with_ids=True):
        """
            Get the full molecules by the ids.
            TODO: exaplin what to do for not found ones? (shouldn't happen much)

        Parameters (FIXME)
        ----------
        molecule_ids
        molecule_hashs

        Returns
        -------
            TODO: explain the expected forrmat of the output
        """
        pass

    # TODO: do we delete one or many? suggested to delete just one
    def del_molecule(self, molecule_id: str):
        pass

    def del_molecules(self, molecule_ids: List[str]=None,
                            molecule_hashes: List[str]=None) -> bool:
        """
        Removes a molecule from the database from its hash.

        Parameters
        ----------
        FIXME

        Returns
        -------

        """
        pass

    # ---------------------- Mongo options functions --------------------------

    def add_options(self, data: Union[dict, List[dict]],
                          return_json=True, with_ids=True):
        """
        Adds a list of options to the database.

        Parameters
        ----------
        data :

        Returns
        -------
        FIXME
        """

        pass

    def get_options(self, program=None, name=None, data: dict=None,
                          return_json=True, with_ids=True):
        """

        Parameters
        ----------
        program
        name
        data

        Returns
        -------

        """
        pass

    def del_option(self, program, name) -> bool:
        """
        Removes a option set from the database based on its keys.

        Parameters
        ----------
        program : str
            The program of the option set
        name : str
            The name of the option set

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        pass

    # -------------------------- Collections ---------------------------------
    #
    def add_collection(self, name: str, data, overwrite=False,
                            return_json=True, with_ids=True):
        """
        Adds a collection to the database.

        Parameters
        ----------
        data : dict
            Structured instance of the database.

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        pass

    def get_collections(self, keys: dict, return_json=True, with_ids=True):
        """
        Gets ONE collection
        TODO: do we need pull multiple collections in the same DB access?
        Parameters
        ----------
        name FIXME
        or pass dict
        TODO: add needed keys
        Returns
        -------

        """
        pass

    def del_collection(self, collection: str, name: str) -> bool:
        """
        Removes a collection from the database from its hash.

        Parameters
        ----------


        Returns
        -------
        bool
            Whether the operation was successful.
        """

        pass

    def add_dataset(self, data: dict):
        """
        TODO: to return specific pydantic classes
        Returns
        -------

        """

    def get_dataset(self, name):
        pass

    def del_dataset(self, name=None, id=None):
        pass

    # -------------------------- Results functions ----------------------------
    #
    def add_result(self, program, method, driver, molecule, basis,
                         options: str, data: dict,
                         return_json=True, with_ids=True):
        """ FIXME
        """

        pass

    def add_results(self, data: List[dict],
                          return_json=True, with_ids=True):
        """

        Parameters
        ----------
        data

        Returns
        -------

        """
        pass

    # Do a lookup on the results collection using a <molecule, method> key.
    def get_results(self, query, projection=None,
                          return_json=True, with_ids=True):

        pass

    def del_results(self, results_ids: Union[str, List[str]]):
        """
        Removes a page from the database from its hash.

        Parameters
        ----------
        hash_val : str or list of strs
            The hash of a page.

        Returns
        -------
        bool
            Whether the operation was successful.
        """
        pass

    # ---------------  Mongo procedure/service functions ----------------------

    def add_procedures(self, procedure: str, option: str, data: dict,
                             return_json=True, with_ids=True):
        pass

    def get_procedures(self, query, return_json=True, with_ids=True):
        pass

    def add_optimization_procedure(self):
        """TODO: How similar will this be to the add_procedure?

        """
        pass

    def get_optimization_procedure(self):
        pass

    def add_services(self, data):

        pass

    def get_services(self, query, projection=None, limit=0):

       pass

    def update_services(self, ids, updates):
        """Use specific keys"""
        pass

    def del_services(self, ids: Union[str, List]):
        """ TODO: what are the values, for delete, it's better to use the Ids
            The caller should have it
        """

        pass

    # --------------------- Mongo queue handling functions --------------------

    def queue_submit(self, data, tag=None):
        """
            TODO: explain the format of the data
            what is assumed to be saved before this step

        Parameters
        ----------
        data
        tag

        Returns
        -------

        """

        pass


    def queue_get_next(self, limit=100, tag=None):

        pass

    def get_queue(self, query, with_results=False,
                        return_json=True, with_ids=True):
        """
        TODO: This is getting a task. If soI think it should be get_task
        Parameters
        ----------
        FIXME

        Returns
        -------

        """

        pass

    def queue_get_by_id(self, id: str, limit=100):
        """
        replaced n with limit
        Parameters
        ----------
        id
        limit

        Returns
        -------

        """

        pass

    def queue_mark_complete(self, queue_ids: List[str], result_location: List[dict]):
        """
        Needs to be more specific.
        I think it should always come with the take Ids known, right?
        expected number of tasks?

        Parameters
        ----------
        FIXME

        Returns
        -------

        """
        pass

    def queue_mark_error(self, queue_ids: List[str], msgs: List[str]):
        pass

    def queue_reset_status(self, daqueue_ids):
        pass

    # ---------------------------  Hooks ----------------------------------
    #
    def handle_hooks(self, hooks):
        """

        TODO: is this ever used or needs redesign later?

        Returns
        -------

        """
        # Very dangerous, we need to modify this substatially
        # Does not currently handle multiple identical commands
        # Only handles service updates

        bulk_commands = []
        for hook_list in hooks:
            for hook in hook_list:
                commands = {}
                for com in hook["updates"]:
                    commands["$" + com[0]] = {com[1]: com[2]}

                upd = pymongo.UpdateOne({"_id": ObjectId(hook["document"][1])}, commands)
                bulk_commands.append(upd)

        if len(bulk_commands) == 0:
            return

        ret = self._tables["service_queue"].bulk_write(bulk_commands, ordered=False)
        return ret

    # ------------------------------- QueueManagers ---------------------------
    #
    def manager_update(self, name, tag=None, submitted=0, completed=0, failures=0, returned=0):
        dt = datetime.datetime.utcnow()

        r = self._tables["queue_managers"].update_one(
            {
                "name": name
            },
            {
                # Provide base data
                "$setOnInsert": {
                    "name": name,
                    "created_on": dt,
                    "tag": tag,
                },
                # Set the date
                "$set": {
                    "modifed_on": dt,
                },
                # Incremement relevant data
                "$inc": {
                    "submitted": submitted,
                    "completed": completed,
                    "returned": returned,
                    "failures": failures
                }
            },
            upsert=True)
        return r.matched_count == 1

    def get_managers(self, query, projection=None):

        pass

### Users

    def add_user(self, username, password, permissions=None):
        """
        Adds a new user and associated permissions.

        Passwords are stored using bcrypt.

        Parameters
        ----------
        username : str
            New user's username
        password : str
            The user's password
        permissions : list of str, optional
            The associated permissions of a user ['read', 'write', 'compute', 'queue', 'admin']

        Returns
        -------
        tuple
            Successful insert or not
        """

        if permissions is None:
            permissions = ["read"]
        hashed = bcrypt.hashpw(password.encode("UTF-8"), bcrypt.gensalt(6))
        try:
            self._tables["users"].insert_one({"username": username, "password": hashed, "permissions": permissions})
            return True
        except pymongo.errors.DuplicateKeyError:
            return False

    def verify_user(self, username, password, permission):
        """
        Verifies if a user has the requested permissions or not.

        Passwords are store and verified using bcrypt.

        Parameters
        ----------
        username : str
            The username to verify
        password : str
            The password associated with the username
        permission : str
            The associated permissions of a user ['read', 'write', 'compute', 'queue', 'admin']

        Returns
        -------
        tuple
            A tuple of (success flag, failure string)

        Examples
        --------

        >>> db.add_user("george", "shortpw")

        >>> db.verify_user("george", "shortpw", "read")
        True

        >>> db.verify_user("george", "shortpw", "admin")
        False

        """

        if self._bypass_security:
            return (True, "Success")

        data = self._tables["users"].find_one({"username": username})
        if data is None:
            return (False, "User not found.")

        pwcheck = bcrypt.checkpw(password.encode("UTF-8"), data["password"])
        if pwcheck is False:
            return (False, "Incorrect password.")

        # Admin has access to everything
        if (permission.lower() not in data["permissions"]) and ("admin" not in data["permissions"]):
            return (False, "User has insufficient permissions.")

        return (True, "Success")

    def remove_user(self, username):
        """Removes a user from the MongoDB Tables

        Parameters
        ----------
        username : str
            The username to remove

        Returns
        -------
        bool
            If the operation was successful or not.
        """
        return self._tables["users"].delete_one({"username": username}).deleted_count == 1

### Complex parsers

    def search_qc_variable(self, hashes, field):
        """
         FIXME: seems unused, self.project here is never defined in mono_socket

        Displays the first `field` value for each molecule in `hashes`.

        Parameters
        ----------
        hashes : list
            A list of molecules hashes.
        field : str
            A page field.

        Returns
        -------
        dataframe
            Returns a dataframe with your results. The rows will have the
            molecule hashes and the column will contain the name. Each cell
            contains the field value for the molecule in that row.

        """
        d = {}
        for mol in hashes:
            command = [{"$match": {"molecule_hash": mol}}, {"$group": {"_id": {}, "value": {"$push": "$" + field}}}]
            results = list(self.project["results"].aggregate(command))
            if len(results) == 0 or len(results[0]["value"]) == 0:
                d[mol] = None
            else:
                d[mol] = results[0]["value"][0]
        return pd.DataFrame(data=d, index=[field]).transpose()
