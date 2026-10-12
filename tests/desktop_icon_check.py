"""Verify the shipped EXE contains the authored Windows icon resources."""
from pathlib import Path
import hashlib
import struct
import pefile
from PyInstaller.archive.readers import CArchiveReader
root=Path(__file__).resolve().parents[1]
exe=root/'release/Zoderise-Horizon-Desktop-Gold-Windows-x64.exe'
ico=(root/'assets/zoderise-icon.ico').read_bytes()
count=struct.unpack_from('<H',ico,4)[0]
expected=set()
for i in range(count):
    size,offset=struct.unpack_from('<II',ico,6+i*16+8)
    expected.add(hashlib.sha256(ico[offset:offset+size]).digest())
pe=pefile.PE(str(exe))
actual=set()
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id==3:
        for icon in entry.directory.entries:
            for language in icon.directory.entries:
                data=language.data.struct
                actual.add(hashlib.sha256(pe.get_data(data.OffsetToData,data.Size)).digest())
assert expected.issubset(actual),'Executable does not contain the new authored icon frames'
archive=CArchiveReader(str(exe))
key=next(n for n in archive.toc if n.replace('\\','/')=='assets/zoderise-icon.ico')
assert archive.extract(key)==ico,'Native window icon differs from file icon'
print('PASS: all seven authored icon sizes are embedded in the EXE resources')
print('PASS: desktop-window icon is bundled and matches the file icon')
