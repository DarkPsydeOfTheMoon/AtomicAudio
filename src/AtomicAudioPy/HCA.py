
from exbip.Serializable import Serializable
from exbip.BinaryTargets.Interface.Base import EndiannessManager


class HCA(Serializable):

	def __init__(self):

		self.Header				= None
		self.CheckSum			= None
		self.Data				= None

		self.ChannelCount		= None
		self.SampleRate			= None
		self.SampleCount		= None
		self.Duration			= None
		self.FrameCount			= None
		self.FrameSize			= None
		self.LoopCount			= None
		self.LoopStartSample	= None
		self.LoopEndSample		= None

	def update_offsets(self):
		self.tobytes()

	def write_right(self, path):
		self.update_offsets()
		self.write(path)

	def __rw_hook__(self, rw):

		with EndiannessManager(rw, ">"):

			self.Header = rw.rw_obj(self.Header, HCAHeader)

			checksum = CRC16().Compute(self.Header.tobytes(), self.Header.HeaderSize-2)
			if rw.is_parselike:
				self.CheckSum = checksum
			self.CheckSum = rw.rw_uint16(self.CheckSum)
			assert self.CheckSum == checksum
			assert rw.tell() == self.Header.HeaderSize

			self.Data = rw.rw_bytestring(self.Data, self.Header.FmtChunk.FrameCount*self.Header.CompChunk.FrameSize)
			assert len(self.Data) == self.Header.FmtChunk.FrameCount*self.Header.CompChunk.FrameSize

		self.ChannelCount	= self.Header.FmtChunk.ChannelCount
		self.SampleRate		= self.Header.FmtChunk.SampleRate
		self.SampleCount	= self.Header.FmtChunk.SampleCount
		self.Duration		= int(1000*self.SampleCount/self.SampleRate)
		self.FrameCount		= self.Header.FmtChunk.FrameCount
		self.FrameSize		= self.Header.CompChunk.FrameSize
		self.LoopCount		= None if self.Header.LoopChunk is None else 1
		if self.LoopCount:
			self.LoopStartSample	= self.Header.LoopChunk.LoopStartSample
			self.LoopEndSample		= self.Header.LoopChunk.LoopEndSample

		crc = CRC16()
		for i in range(self.FrameCount):
			frame = self.Data[i*self.FrameSize:(i+1)*self.FrameSize]
			assert len(frame) == self.FrameSize
			if crc.Compute(frame, len(frame)-2) != (frame[-2] << 8) | frame[-1]:
				raise ValueError("ruh-roh")

		failed = False
		try:
			rw.assert_eof()
		except Exception:
			print("Failed to read file!")
			remainder = rw.peek_bytestream(64)
			print(len(remainder), remainder)

	def Crypt(self, keycode=None):
		# encrypt
		if self.Header.CiphChunk is None or self.Header.CiphChunk.EncryptionType == 0:
			# type 1 encryption
			if keycode is None:
				key = HCAKey(keytype=1)
			# type 2 encryption
			else:
				key = HCAKey(keytype=56, keycode=keycode)
			key.Encrypt(self)
		# decrypt
		else:
			# type 1 decryption
			if self.Header.CiphChunk.EncryptionType == 1:
				key = HCAKey(keytype=1)
			# type 56 decryption
			elif self.Header.CiphChunk.EncryptionType == 56:
				key = HCAKey(keytype=56, keycode=keycode)
			if key is not None:
				key.Decrypt(self)


class HCAHeader(Serializable):

	def __init__(self):

		self.Magic			= None
		self.Version		= None
		self.HeaderSize		= None

		self.FmtChunk		= None
		self.CompChunk		= None
		self.DecChunk		= None
		self.LoopChunk		= None
		self.AthChunk		= None
		self.CiphChunk		= None
		self.RvaChunk		= None
		self.VbrChunk		= None
		self.CommChunk		= None
		self.PadChunk		= None

	def __rw_hook__(self, rw):

		with EndiannessManager(rw, ">"):

			self.Magic = rw.rw_bytestring(self.Magic, 4)
			assert DecryptByteString(self.Magic) == b"HCA\0"

			self.Version = rw.rw_uint16(self.Version)

			self.HeaderSize = rw.rw_uint16(self.HeaderSize)

			if rw.is_constructlike:
				while rw.tell() < self.HeaderSize:
					testFormat = DecryptByteString(rw.peek_bytestream(4))
					if testFormat == b"fmt\0":
						self.FmtChunk = rw.rw_obj(self.FmtChunk, FmtChunk)
					elif testFormat == b"comp":
						self.CompChunk = rw.rw_obj(self.CompChunk, CompChunk)
					elif testFormat == b"dec\0":
						self.DecChunk = rw.rw_obj(self.DecChunk, DecChunk)
					elif testFormat == b"loop":
						self.LoopChunk = rw.rw_obj(self.LoopChunk, LoopChunk)
					elif testFormat == b"ath\0":
						self.AthChunk = rw.rw_obj(self.AthChunk, AthChunk)
					elif testFormat == b"ciph":
						self.CiphChunk = rw.rw_obj(self.CiphChunk, CiphChunk)
					elif testFormat == b"rva\0":
						self.RvaChunk = rw.rw_obj(self.RvaChunk, RvaChunk)
					elif testFormat == b"vbr\0":
						self.VbrChunk = rw.rw_obj(self.VbrChunk, VbrChunk)
					elif testFormat == b"comm":
						self.CommChunk = rw.rw_obj(self.CommChunk, CommChunk)
					elif testFormat == b"pad\0":
						# -4 for magic string + -2 for checksum = -6
						self.PadChunk = rw.rw_obj(self.PadChunk, PadChunk, self.HeaderSize-rw.tell()-6)
					else:
						break
			elif rw.is_parselike:
				if self.FmtChunk is not None:
					self.FmtChunk = rw.rw_obj(self.FmtChunk, FmtChunk)
				if self.CompChunk is not None:
					self.CompChunk = rw.rw_obj(self.CompChunk, CompChunk)
				if self.DecChunk is not None:
					self.DecChunk = rw.rw_obj(self.DecChunk, DecChunk)
				if self.LoopChunk is not None:
					self.LoopChunk = rw.rw_obj(self.LoopChunk, LoopChunk)
				if self.AthChunk is not None:
					self.AthChunk = rw.rw_obj(self.AthChunk, AthChunk)
				if self.CiphChunk is not None:
					self.CiphChunk = rw.rw_obj(self.CiphChunk, CiphChunk)
				if self.RvaChunk is not None:
					self.RvaChunk = rw.rw_obj(self.RvaChunk, RvaChunk)
				if self.VbrChunk is not None:
					self.VbrChunk = rw.rw_obj(self.VbrChunk, VbrChunk)
				if self.CommChunk is not None:
					self.CommChunk = rw.rw_obj(self.CommChunk, CommChunk)
				if self.PadChunk is not None:
					# -4 for magic string + -2 for checksum = -6
					self.PadChunk = rw.rw_obj(self.PadChunk, PadChunk, self.HeaderSize-rw.tell()-6)

	def EncryptChunks(self):
		self.Magic = EncryptByteString(self.Magic)
		for chunk in [
			self.FmtChunk, self.CompChunk, self.DecChunk,
			self.LoopChunk, self.AthChunk, self.CiphChunk,
			self.RvaChunk, self.VbrChunk, self.CommChunk,
			self.PadChunk,
		]:
			if chunk is not None:
				chunk.Magic = EncryptByteString(chunk.Magic)

	def DecryptChunks(self):
		self.Magic = DecryptByteString(self.Magic)
		for chunk in [
			self.FmtChunk, self.CompChunk, self.DecChunk,
			self.LoopChunk, self.AthChunk, self.CiphChunk,
			self.RvaChunk, self.VbrChunk, self.CommChunk,
			self.PadChunk,
		]:
			if chunk is not None:
				chunk.Magic = DecryptByteString(chunk.Magic)


class FmtChunk(Serializable):

	def __init__(self):

		self.Magic				= None
		self.ChannelCount		= None

		self.SRH				= None
		self.SRL				= None
		self.SampleRate			= None

		self.FrameCount			= None
		self.InsertedSamples	= None
		self.AppendedSamples	= None
		self.SampleCount		= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"fmt\0"

		self.ChannelCount		= rw.rw_uint8(self.ChannelCount)

		if rw.is_parselike:
			self.SRH = (self.SampleRate >> 16) & 0xFF
			self.SRL = self.SampleRate & 0xFFFF
		self.SRH				= rw.rw_uint8(self.SRH)
		self.SRL				= rw.rw_uint16(self.SRL)
		self.SampleRate			= (self.SRH << 16) | self.SRL

		self.FrameCount			= rw.rw_uint32(self.FrameCount)
		self.InsertedSamples	= rw.rw_uint16(self.InsertedSamples)
		self.AppendedSamples	= rw.rw_uint16(self.AppendedSamples)
		self.SampleCount		= self.FrameCount * 1024 - self.InsertedSamples - self.AppendedSamples


class CompChunk(Serializable):

	def __init__(self):

		self.Magic				= None
		self.FrameSize			= None
		self.MinResolution		= None
		self.MaxResolution		= None
		self.TrackCount			= None
		self.ChannelConfig		= None
		self.TotalBandCount		= None
		self.BaseBandCount		= None
		self.StereoBandCount	= None
		self.BandsPerHfrGroup	= None
		self.RESERVED			= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"comp"

		self.FrameSize			= rw.rw_uint16(self.FrameSize)
		self.MinResolution		= rw.rw_uint8(self.MinResolution)
		self.MaxResolution		= rw.rw_uint8(self.MaxResolution)
		self.TrackCount			= rw.rw_uint8(self.TrackCount)
		self.ChannelConfig		= rw.rw_uint8(self.ChannelConfig)
		self.TotalBandCount		= rw.rw_uint8(self.TotalBandCount)
		self.BaseBandCount		= rw.rw_uint8(self.BaseBandCount)
		self.StereoBandCount	= rw.rw_uint8(self.StereoBandCount)
		self.BandsPerHfrGroup	= rw.rw_uint8(self.BandsPerHfrGroup)

		self.RESERVED = rw.rw_uint16(self.RESERVED)
		assert self.RESERVED == 0


class DecChunk(Serializable):

	def __init__(self):

		self.Magic				= None
		self.FrameSize			= None
		self.MinResolution		= None
		self.MaxResolution		= None

		self._totalBandCount	= None
		self.TotalBandCount		= None

		self._baseBandCount		= None
		self.BaseBandCount		= None

		self._trackAndChannel	= None
		self.TrackCount			= None
		self.ChannelConfig		= None

		self.DecStereoType		= None
		self.StereoBandCount	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"dec\0"

		self.FrameSize			= rw.rw_uint16(self.FrameSize)
		self.MinResolution		= rw.rw_uint8(self.MinResolution)
		self.MaxResolution		= rw.rw_uint8(self.MaxResolution)

		if rw.is_parselike:
			self._totalBandCount = self.TotalBandCount - 1
		self._totalBandCount	= rw.rw_uint8(self._totalBandCount)
		self.TotalBandCount		= self._totalBandCount + 1

		if rw.is_parselike:
			self._baseBandCount = self._baseBandCount - 1
		self._baseBandCount		= rw.rw_uint8(self._baseBandCount)
		self.BaseBandCount		= self._baseBandCount + 1

		if rw.is_parselike:
			self._trackAndChannel = (self.TrackCount << 4) | self.ChannelConfig
		self._trackAndChannel	= rw.rw_uint8(self._trackAndChannel)
		self.TrackCount			= (self._trackAndChannel >> 4) & 0xF
		self.ChannelConfig		= self._trackAndChannel & 0xF

		self.DecStereoType		= rw.rw_uint8(self.DecStereoType)
		if self.DecStereoType:
			self.StereoBandCount	= self.TotalBandCount - self.BaseBandCount
		else:
			self.BaseBandCount		= self.TotalBandCount
			self.StereoBandCount	= 0


class LoopChunk(Serializable):

	def __init__(self):

		self.Magic				= None
		self.LoopStartFrame		= None
		self.LoopEndFrame		= None
		self.PreLoopSamples		= None
		self.PostLoopSamples	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"loop"

		self.LoopStartFrame		= rw.rw_uint32(self.LoopStartFrame)
		self.LoopEndFrame		= rw.rw_uint32(self.LoopEndFrame)
		self.PreLoopSamples		= rw.rw_uint16(self.PreLoopSamples)
		self.PostLoopSamples	= rw.rw_uint16(self.PostLoopSamples)


class AthChunk(Serializable):

	def __init__(self):

		self.Magic			= None
		self.UseAthCurve	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"ath\0"

		self.UseAthCurve = rw.rw_uint16(self.UseAthCurve)


class CiphChunk(Serializable):

	def __init__(self):

		self.Magic			= None
		self.EncryptionType	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"ciph"

		self.EncryptionType = rw.rw_uint16(self.EncryptionType)


class RvaChunk(Serializable):

	def __init__(self):

		self.Magic	= None
		self.Volume	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"rva\0"

		self.Volume = rw.rw_float32(self.Volume)


class VbrChunk(Serializable):

	def __init__(self):

		self.Magic			= None
		self.MaxFrameSize	= None
		self.NoiseLevel		= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"vbr\0"

		self.MaxFrameSize	= rw.rw_uint16(self.MaxFrameSize)
		self.NoiseLevel		= rw.rw_uint16(self.NoiseLevel)


class CommChunk(Serializable):

	def __init__(self):

		self.Magic		= None
		self.RESERVE	= None
		self.Comment	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"comm"

		self.RESERVE = rw.rw_uint8(self.RESERVE)
		assert self.RESERVE == 0

		self.Comment = rw.rw_cbytestring(self.Comment)


class PadChunk(Serializable):

	def __init__(self):

		self.Magic		= None
		self.Padding	= None

	def __rw_hook__(self, rw, size):

		self.Magic = rw.rw_bytestring(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"pad\0"

		self.Padding = rw.rw_bytestring(self.Padding, size)
		assert self.Padding == b"\0"*size


def DecryptByteString(bs):
	return bytes([b & 0x7F for b in bs])


def EncryptByteString(bs, chunk=True):
	return bytes([bs[i] | (0x80 if bs[i] else 0) for i in range(len(bs))])


class CRC16:

	def __init__(self, polynomial=0x8005):
		self.Table = self.GenerateTable(polynomial)

	def GenerateTable(self, polynomial):
		table = list()
		for i in range(256):
			curByte = (i << 8) & 0xFFFF
			for j in range(8):
				xorFlag = (curByte & 0x8000) != 0
				curByte <<= 1
				if xorFlag:
					curByte = (curByte ^ polynomial) & 0xFFFF
			table.append(curByte)
		return table

	def Compute(self, data, size):
		crc = 0
		for i in range(size):
			crc = ((crc << 8) ^ self.Table[(crc >> 8) ^ data[i]]) & 0xFFFF
		return crc


class HCAKey:

	def __init__(self, keytype, keycode=None):
		assert keytype == 0 or keytype == 1 or keytype == 56
		self.KeyCode = keycode
		self.KeyType = keytype
		self.BaseTable = self.GenerateBaseTable()
		self.DecryptionTable = self.GenerateTable(keytype, keycode)
		self.EncryptionTable = self.InvertTable(self.DecryptionTable)
		self.Crc = CRC16()

	def GenerateBaseTable(self):
		table = list()
		for i in range(256):
			table.append(list())
			xor = i >> 4
			mult = ((i & 1) << 3) | 5
			inc = (i & 0xE) | 1
			for j in range(16):
				xor = (xor * mult + inc) % 16
				table[-1].append(xor & 0xFF)
		return table

	def GenerateTable(self, keytype, keycode):
		if keytype == 0:
			return list(range(256))
		elif keytype == 1:
			table = list()
			xor = 0
			mult = 13
			inc = 11
			outPos = 1
			for i in range(256):
				xor = (xor * mult + inc) % 256
				if xor != 0 and xor != 255:
					table[outPos] = xor & 0xFF
					outPos += 1
			table[255] = 255
			return table
		elif keytype == 56:
			kc = (keycode-1).to_bytes(16, "little")
			rowSeed = kc[0]
			columnSeeds = [
				kc[1],
				(kc[6] ^ kc[1]) & 0xFF,
				(kc[2] ^ kc[3]) & 0xFF,
				kc[2],
				(kc[1] ^ kc[2]) & 0xFF,
				(kc[3] ^ kc[4]) & 0xFF,
				kc[3],
				(kc[2] ^ kc[3]) & 0xFF,
				(kc[4] ^ kc[5]) & 0xFF,
				kc[4],
				(kc[3] ^ kc[4]) & 0xFF,
				(kc[5] ^ kc[6]) & 0xFF,
				kc[5],
				(kc[4] ^ kc[5]) & 0xFF,
				(kc[6] ^ kc[1]) & 0xFF,
				kc[6],
			]
			table1 = [0]*256
			row = self.BaseTable[rowSeed]
			for r in range(16):
				col = self.BaseTable[columnSeeds[r]]
				for c in range(16):
					table1[16 * r + c] = (row[r] << 4) | col[c]
			# shuffle time
			table2 = [0]*256
			x = 0
			outPos = 1
			for i in range(256):
				x = (x + 17) & 0xFF
				if table1[x] != 0 and table1[x] != 255:
					table2[outPos] = table1[x]
					outPos += 1
			table2[0] = 0
			table2[255] = 255
			return table2

	def InvertTable(self, table1):
		table2 = [0]*len(table1)
		for i in range(len(table1)):
			table2[table1[i]] = i
		return table2

	def Encrypt(self, hca):
		hca.Data = bytes(self.Crypt(hca, self.EncryptionTable))
		hca.Header.CiphChunk.EncryptionType = self.KeyType
		hca.Header.CiphChunk.EncryptionType = self.KeyType
		hca.Header.EncryptChunks()

	def Decrypt(self, hca):
		hca.Data = bytes(self.Crypt(hca, self.DecryptionTable))
		hca.Header.CiphChunk.EncryptionType = 0
		hca.Header.DecryptChunks()

	def Crypt(self, hca, table):
		data = [0]*len(hca.Data)
		for i in range(hca.FrameCount):
			for j in range(hca.FrameSize-2):
				pos = i*hca.FrameSize + j
				data[pos] = table[hca.Data[pos]]
			crc = self.Crc.Compute(data[i*hca.FrameSize:(i+1)*hca.FrameSize], hca.FrameSize-2)
			data[(i+1)*hca.FrameSize - 2] = (crc >> 8) & 0xFF
			data[(i+1)*hca.FrameSize - 1] = crc & 0xFF
		return data
