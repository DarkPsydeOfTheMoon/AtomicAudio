def ReadableTrait(Reader):
    class ReadableTraitImpl:
        def read(self, filepath, *args, **kwargs):
            reader = Reader()
            with reader.FileIO(filepath) as rw:
                rw.rw_obj(self, *args, **kwargs)

        def frombytes(self, byte_data, *args, **kwargs):
            reader = Reader()
            with reader.BytestreamIO(byte_data):
                reader.rw_obj(self, *args, **kwargs)

    return ReadableTraitImpl


def WriteableTrait(Writer):
    class WriteableTraitImpl:
        def write(self, filepath, *args, **kwargs):
            writer = Writer()
            with writer.FileIO(filepath) as rw:
                rw.rw_obj(self, *args, **kwargs)

        def tobytes(self, *args, **kwargs):
            writer = Writer()
            #with writer.BytestreamIO(b''):
            with writer.BytestreamIO():
                writer.rw_obj(self, *args, **kwargs)
                writer.seek(0)
                return writer._bytestream.read()

    return WriteableTraitImpl

