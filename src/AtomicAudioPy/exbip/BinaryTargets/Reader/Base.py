import io
import os
from ..Interface import IConstructTarget
from ..Interface import ISequentialStreamTarget


class FileIO:
    def __init__(self, rw, filepath):
        self.rw = rw
        self.filepath = filepath

    def __enter__(self):
        self.rw._bytestream = open(self.filepath, 'rb')
        return self.rw

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rw._bytestream.close()
        self.rw._bytestream = None


class SSOIO:
    def __init__(self, rw, filepath):
        self.rw = rw
        self.filepath = filepath

    def __enter__(self):
        with open(self.filepath, 'rb', buffering=0) as F:
            self.rw._bytestream = io.BytesIO(F.read())
        return self.rw

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rw._bytestream = None


class BytestreamIO:
    def __init__(self, rw, initializer):
        self.rw = rw
        self.initializer = initializer

    def __enter__(self):
        self.rw._bytestream = io.BytesIO(self.initializer)
        return self.rw

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rw._bytestream.close()
        self.rw._bytestream = None


class ReaderBase(IConstructTarget, ISequentialStreamTarget):
    def __init__(self):
        super().__init__()
        self._bytestream = None

    def global_tell(self):
        return self._bytestream.tell()

    def global_seek(self, offset, whence=os.SEEK_SET):
        return self._bytestream.seek(offset, whence)

    ###########################
    # READER-SPECIFIC METHODS #
    ###########################
    def FileIO(self, filepath):
        return FileIO(self, filepath)

    def SSOIO(self, filepath):
        return SSOIO(self, filepath)

    def BytestreamIO(self, initializer):
        return BytestreamIO(self, initializer)

    def _rw_raw(self, value, length):
        return self._bytestream.read(length)

    def peek_bytestream(self, length):
        val = self._rw_raw(None, length)
        self.seek(-len(val), 1)
        return val
        #return self._rw_raw.peek()
