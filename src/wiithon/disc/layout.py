"""On-disc offsets of a Wii disc image. See https://wiibrew.org/wiki/Wii_disc"""

PARTITION_TABLE_OFFSET:   int = 0x40000
PARTITION_TABLE_ENTRIES:  int = 0x40020
PARTITION_GROUP_COUNT:    int = 4
REGION_OFFSET:            int = 0x4E000
REGION_SIZE:              int = 0x20
MAGIC_WORD_OFFSET:        int = 0x4FFFC
WII_MAGIC_WORD:           int = 0xC3F81A8E
FIRST_PARTITION_OFFSET:   int = 0x50000

DISC_HEADER_SIZE:         int = 0x440
BI2_OFFSET:               int = 0x440
BI2_SIZE:                 int = 0x2000
APPLOADER_OFFSET:         int = 0x2440
APPLOADER_HEADER_SIZE:    int = 0x20