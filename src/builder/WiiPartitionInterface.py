from abc import ABC, abstractmethod
from typing import List, Callable

from WiiPartitionInfo import WiiPartitionInfo
from crypto.CryptPartWriter import CryptPartWriter
from file_system_table.FSTToBytes import FSTToBytes
from helpers.Enums import WiiPartType
from structs.Certificate import Certificate
from structs.DiscHeader import DiscHeader
from structs.TMD import TMD
from structs.WiiPartitionHeader import WiiPartitionHeader


class WiiPartitionInterface(ABC):
    @abstractmethod
    def get_partition_type(self) -> WiiPartType: pass
    @abstractmethod
    def get_header(self) -> WiiPartitionHeader: pass
    @abstractmethod
    def get_tmd(self) -> TMD: pass
    @abstractmethod
    def get_certificates(self) -> List[Certificate]: pass
    @abstractmethod
    def get_encrypted_header(self) -> DiscHeader: pass
    @abstractmethod
    def get_bi2(self) -> bytes: pass
    @abstractmethod
    def get_apploader(self) -> bytes: pass
    @abstractmethod
    def get_dol(self) -> bytes: pass
    @abstractmethod
    def get_fst_to_bytes(self) -> FSTToBytes: pass
    @abstractmethod
    def write_file_data(self, writer: CryptPartWriter, progress_cb: Callable) -> int: pass