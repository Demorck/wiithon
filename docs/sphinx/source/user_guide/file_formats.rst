============
File Formats
============

Wiithon provides classes to read and write several Nintendo file formats directly.


RARC
----

RARC is Nintendos archive format, used to bundle multiple files into one.

.. code-block:: python

   from io import BytesIO
   from wiithon.file_helper.rarc import Rarc

   # Reading
   with open("archive.arc", "rb") as f:
       rarc = Rarc.read(f)

   # Listing files
   for entry in rarc.entries:
       print(entry.name, entry.data_size)

   # Reading a file
   data = rarc.get_file("model.bmd")

   # Replacing a file
   rarc.replace_file("model.bmd", new_data)

   # Writing back
   buf = BytesIO()
   rarc.write(buf)
   result = buf.getvalue()

   # Extracting to disk
   rarc.extract_to("output/")


Yaz0
----

Yaz0 is Nintendo's compression format. Many RARC archives are Yaz0-compressed
(magic bytes ``Yaz0`` at offset 0).

.. code-block:: python

   from io import BytesIO
   from wiithon.file_helper.yaz0 import Yaz0

   # Decompressing
   with open("file.szs", "rb") as f:
       yaz0 = Yaz0.read(f)
   raw = yaz0.data

   # Compressing
   compressed = Yaz0.from_data(raw)
   buf = BytesIO()
   compressed.write(buf)


DOL
---

The DOL format is the main executable format for GameCube and Wii games.

.. code-block:: python

   from io import BytesIO
   from wiithon.file_helper.dol import DOL

   with open("main.dol", "rb") as f:
       dol = DOL.read(f)

