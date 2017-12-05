#!/usr/bin/python
#
# Copyright (c) 2017 Emma Laurijssens van Engelenhoven, <emma@talwyn-esp.nl>
#
#  GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
author: Emma Laurijssens van Engelenhoven (@elaurijssens)
description:
  - Insert or delete documents from a MongoDB collection. For retrieving data, use the mongodb lookup function.
module: mongodb_document
options:
  connection_string:
    description:
      - The connection string with which to connect to the MongoDB host. 
    required: true
  database:
    descriptiom:
      - The name of the database to connect to.
    required: True
  collection:
    description:
      - The name of the collection of documents we'll be looking at.
    required: True
  document:
    description:
      - The document to look for. If a simple tuple is specified, it'll work as a filter, meaning that only the first 
      - match is considered. In this case, state=present will be successful with any occurence, and state=absent
      - will delete the first match.  
    required: True
  state:
    description:
      - The desired state of the document
    default: present
    choices: [present, absent]

short_description: Manage MongoDB documents in  an existing collection
version_added: "2.5"

'''

EXAMPLES = '''
  - name: Make sure document exists
    mongodb_document:
      connection_string: "mongodb://password:username@mongodb.host:port"
      database: "exampledb"
      collection: "mycollection"
      state: present
      document:
        key: "value"
        dictionary:
          item1: "val1"
          item2: "val2"

  - name: Make sure document does not exist
    mongodb_document:
      connection_string: "mongodb://password:username@mongodb.host:port"
      database: "exampledb"
      collection: "mycollection"
      state: absent
      document:
        key: "value"
        dictionary:
          item1: "val1"
          item2: "val2"

  - name: Delete first document that has "key" set to "value"
    mongodb_document:
      connection_string: "mongodb://password:username@mongodb.host:port"
      database: "exampledb"
      collection: "mycollection"
      state: absent
      document:
        key: "value"
'''

RETURN = '''
found:
    description: Was the document found?
    returned: always
    type: bool
_id:
    description: The _id of the document when found or created
    returned: success
    type: string
'''


from ansible.module_utils.basic import AnsibleModule

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from copy import deepcopy


def main():

        # Get our arguments straight
        module_arg_spec = dict(
            connection_string=dict(type='str', required=True, no_log=True),
            database=dict(type='str', required=True),
            collection=dict(type='str', required=True),
            document=dict(type='dict', required=True),
            state=dict(type='str', required=False, default='present', choices=['present', 'absent'])
        )

        # In essence, we don't want anything to change if nothing happens
        result = dict(changed=False)

        # Initialise the module object
        mongo_module = AnsibleModule(argument_spec=module_arg_spec,
                                     supports_check_mode=True)

        # MongoDB adds _id to the document if it has to create it. _id is a MongoDB cursor, an object type that is
        # only defined in the pymongo library. So what? Well, if we don't copy the dict first, it will add an object
        # type that AnsibleModule doesn't understand. Ansible, when run with -vvv, will show the invocation parameters
        # and filter out parameters that we don't want to log. That is all done by the exit_json method, and it will
        # fail miserably on unknown object types. It does that always, not only when you use -vvv.
        doc_to_work_on = deepcopy(mongo_module.params["document"])

        # Now we're at it, let's use variables for the rest as well. They're strings, and immutable, but still.
        connstring = mongo_module.params["connection_string"]
        database_name = mongo_module.params["database"]
        collection_name = mongo_module.params["collection"]
        document_state = mongo_module.params["state"]

        # Connect to the database host
        mongo_client = MongoClient(host=connstring, connect=True)

        # What if the database host doesn't exist?
        try:
            # The ismaster command is cheap and does not require auth.
            mongo_client.admin.command('ismaster')
        except ConnectionFailure:
            mongo_module.fail_json(msg="Server not available")

        # Get the collection we'll be searching
        mongo_database = mongo_client[database_name]
        mongo_collection = mongo_database[collection_name]

        # Does the document specified exist already?
        document_exists = list(mongo_collection.find(doc_to_work_on, {"_id": 1}).limit(1))

        if not document_exists:
            # If the document is not found, and state=present, we need to create it, or pretend we do when in check_mode
            result["found"] = False
            if document_state == "present":
                if not mongo_module.check_mode:
                    record_id = mongo_collection.insert_one(document=doc_to_work_on).inserted_id
                    result["_id"] = str(record_id)
                else:
                    # In check mode, we do need to return _id
                    result["_id"] = "000000000000000000000000"
                result["changed"] = True
        else:
            # If the document exists, and state=absent, we need to delete it, unless when in check_mode.
            if document_state == "absent":
                if not mongo_module.check_mode:
                    mongo_collection.delete_one(filter=doc_to_work_on)
                result["changed"] = True
            result["found"] = True
            result["_id"] = str(document_exists[0]["_id"])

        # Close stuff
        mongo_client.close()

        # Return the results
        mongo_module.exit_json(**result)


if __name__ == '__main__':
    main()
