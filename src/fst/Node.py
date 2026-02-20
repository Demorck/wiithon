from typing import List, Optional


class FSTNode:
    """A file or directory node in the FST tree"""
    def __init__(self,  name: str = "", is_directory: bool = False,
                        offset: int = 0, length: int = 0) -> None:
        self.name: str = name
        self.is_directory: bool = is_directory
        self.offset: int = offset
        self.length: int = length
        self.children: List["FSTNode"] = []

    def find(self, path: str) -> Optional["FSTNode"]:
        """
        Find a node by the relative path
        :param path:
        :return:
        """

        parts = path.strip("/").split("/")
        current = self
        for part in parts:
            found = None
            for child in current.children:
                if child.name == part:
                    found = child
                    break
            if found is None:
                return None
            current = found

        return current

    def count_files(self) -> int:
        """
        Count the number of files in this subtree
        :return:
        """
        if not self.is_directory:
            return 1

        return sum(child.count_files() for child in self.children)

