#!/usr/bin/python

import base64
import random
from Crypto.Cipher import AES


class FilterModule(object):

    # The filters method ties the label we use in Ansible to the method/function that is actually being executed.
    # Usually we use the same name for both the label and the method.

    def filters(self):
        return {
            'aesencrypt': self.aesencrypt,
            'aesdecrypt': self.aesdecrypt
        }

    # The filter aescrypto takes three arguments. The first argument is the data that is 'piped' into the filter.
    # The second argument is the AES key (we'll use AES-256 so a 32 byte key is necessary).
    # The third argument determines the direction: True for encrypting or False for decrypting.

    def aesencrypt(self, blob, key):

        # As error handling in filters is not particularly well implemented, we'll just pad the key to 32 characters.
        # Of course, providing shorter keys weakens security and is strongly discouraged.

        key = "{}VoyagerVoyagerVoyagerVoyagerVoyager".format(key)[:32]

        # AES uses a block size of 16 bytes. So, the input must be a multiple of 16. The input data could be anything
        # though. So, we will be padding the missing bytes with a byte that indicates the number of characters
        # added. If the input data *is* exactly on a 16 byte boundary, then we'll add 16 bytes. That way, the function
        # that unpads the decrypted data does not have to know anything, it just looks at the last byte, that will
        # range in value from 1 to 16, and remove that much bytes from the data.

        block_size = 16

        def pad(s):
            return s + (block_size - len(s) % block_size) * chr(block_size - len(s) % block_size)

        # AES in CBC mode needs a random 16 byte initialization vector, so that encrypted data can not be related,
        # even when the source data was the same. In that regard, it serves the same purpose a a password salt.
        # The final encrypted data is prepended with the iv, so that the data can be successfully decrypted, and then
        # Base64 encoded to allow for embedding in text structures.

        iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
        crypto = AES.new(key, AES.MODE_CBC, iv)
        encryptedblob = iv + crypto.encrypt(pad(blob))

        return base64.b64encode(encryptedblob)

    def aesdecrypt(self, blob, key):

        # As error handling in filters is not particularly well implemented, we'll just pad the key to 32 characters.
        # Of course, providing shorter keys weakens security and is strongly discouraged.

        key = "{}VoyagerVoyagerVoyagerVoyagerVoyager".format(key)[:32]

        def unpad(s):
            return s[0:-ord(s[-1])]

        # When decoding, we first need to isolate the initialization vector. We do that by taking the first 16 bytes
        # from the Base64 decoded data. Then, we use the remainder of the data and the iv, and decrypt the data. That
        # leaves us with the padded data, which only needs to be un-padded.

        iv = base64.b64decode(blob)[:16]
        crypto = AES.new(key, AES.MODE_CBC, iv)
        decryptedblob = crypto.decrypt(base64.b64decode(blob)[16:])

        return unpad(decryptedblob)
