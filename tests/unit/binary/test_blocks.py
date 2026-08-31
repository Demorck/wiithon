import unittest

from wiithon.crypto.blocks import encrypt_group, encrypt_group_data, hash_group
from wiithon.crypto.layout import GROUP_SIZE, SHA1_SIZE


class TestGroupHashingSplit(unittest.TestCase):
    def test_split_matches_the_whole(self):
        """hash_group then encrypt_group_data must be encrypt_group"""
        key = bytes(range(16))
        source = bytes(range(256)) * (GROUP_SIZE // 256)

        buffer = bytearray(source)
        hash_group(buffer)

        self.assertEqual(encrypt_group_data(buffer, key), encrypt_group(source, key))

    def test_h3_is_the_same_either_way(self):
        left, right = bytearray(SHA1_SIZE), bytearray(SHA1_SIZE)

        hash_group(bytearray(GROUP_SIZE), left)
        encrypt_group(bytes(GROUP_SIZE), bytes(16), right)

        self.assertEqual(left, right)


if __name__ == '__main__':
    unittest.main()