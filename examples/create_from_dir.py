from builder.DirectoryPartitionBuilder import DirectoryPartitionBuilder
from helpers.Enums import WiiPartType

def main():
    dir_builder = DirectoryPartitionBuilder("src", WiiPartType.DATA)
    for entry in dir_builder.fst.entries:
        print(entry.name)

if __name__ == "__main__":
    main()