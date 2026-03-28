from abc import ABC, abstractmethod
from typing import List

from structs.Certificate import Certificate
from structs.DiscHeader import DiscHeader
from structs.TMD import TMD
from structs.Ticket import Ticket
from helpers.Enums import WiiPartType
from file_system_table.FST import FST


class WiiPartitionInterface(ABC):
    @abstractmethod
    def get_partition_type(self) -> WiiPartType: pass
    
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
    def get_fst(self) -> FST: pass
    
    @abstractmethod
    def get_ticket(self) -> Ticket: pass
    
    @abstractmethod
    def get_file_data(self, path: List[str]) -> bytes: pass
