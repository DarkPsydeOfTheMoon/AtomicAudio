import io
import os
from ..Interface import IParseTarget
from ..Interface import ISequentialStreamTarget


class FileIO:
    def __init__(self, rw, filepath):
        self.rw = rw
        self.filepath = filepath

    def __enter__(self):
        self.rw._bytestream = open(self.filepath, 'wb')
        return self.rw

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rw._bytestream.close()
        self.rw._bytestream = None


class SSOIO:
    def __init__(self, rw, filepath):
        self.rw = rw
        self.filepath = filepath

    def __enter__(self):
        self.rw._bytestream = io.BytesIO()
        return self.rw

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rw._bytestream.seek(0)
        with open(self.filepath, 'wb') as F:
            F.write(self.rw._bytestream.read())
        self.rw._bytestream = None


class BytestreamIO:
    def __init__(self, rw):
        self.rw = rw

    def __enter__(self):
        self.rw._bytestream = io.BytesIO()
        return self.rw

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rw._bytestream.close()
        self.rw._bytestream = None


class WriterBase(IParseTarget, ISequentialStreamTarget):
    def __init__(self):
        super().__init__()
        self._bytestream = None

    def global_tell(self):
        return self._bytestream.tell()

    def global_seek(self, offset, whence=os.SEEK_SET):
        return self._bytestream.seek(offset, whence)

    def FileIO(self, filepath):
        return FileIO(self, filepath)

    def SSOIO(self, filepath):
        return SSOIO(self, filepath)

    def BytestreamIO(self):
        return BytestreamIO(self)

    def _rw_raw(self, value, length):
        return self._bytestream.write(value)
