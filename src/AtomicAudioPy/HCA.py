
from exbip.Serializable import Serializable
from exbip.BinaryTargets.Interface.Base import EndiannessManager


class HCA(Serializable):

	def __init__(self):
		self.Magic				= None
		self.Version			= None
		self.HeaderSize			= None

		self.FmtChunk			= None
		self.CompChunk			= None
		self.DecChunk			= None
		self.LoopChunk			= None
		self.AthChunk			= None
		self.CiphChunk			= None
		self.RvaChunk			= None
		self.VbrChunk			= None
		self.CommChunk			= None
		self.PadChunk			= None

		self.Data				= None

		self.ChannelCount		= None
		self.SampleRate			= None
		self.SampleCount		= None
		self.Duration			= None
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

			self.Magic = rw.rw_uint8s(self.Magic, 4)
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
						self.PadChunk = rw.rw_obj(self.PadChunk, PadChunk, self.HeaderSize-rw.tell()-4)
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
					self.PadChunk = rw.rw_obj(self.PadChunk, PadChunk, self.HeaderSize-rw.tell()-4)
			assert rw.tell() == self.HeaderSize

		self.Data = rw.rw_bytestring(self.Data, self.FmtChunk.FrameCount*self.CompChunk.FrameSize)

		self.ChannelCount	= self.FmtChunk.ChannelCount
		self.SampleRate		= self.FmtChunk.SampleRate
		self.SampleCount	= self.FmtChunk.SampleCount
		self.Duration		= int(1000*self.SampleCount/self.SampleRate)
		self.LoopCount		= None if self.LoopChunk is None else 1
		if self.LoopCount:
			self.LoopStartSample = self.LoopChunk.LoopStartSample
			self.LoopEndSample = self.LoopChunk.LoopEndSample

		failed = False
		try:
			rw.assert_eof()
		except Exception:
			print("Failed to read file!")
			remainder = rw.peek_bytestream(64)
			print(len(remainder), remainder)


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

		self.Magic = rw.rw_uint8s(self.Magic, 4)
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

		self.Magic = rw.rw_uint8s(self.Magic, 4)
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

		self.Magic = rw.rw_uint8s(self.Magic, 4)
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
		self.LoopStartSample	= None
		self.LoopEndSample		= None
		self.PreLoopSamples		= None
		self.PostLoopSamples	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_uint8s(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"loop"

		self.LoopStartSample	= rw.rw_uint32(self.LoopStartSample)
		self.LoopEndSample		= rw.rw_uint32(self.LoopEndSample)
		self.PreLoopSamples		= rw.rw_uint16(self.PreLoopSamples)
		self.PostLoopSamples	= rw.rw_uint16(self.PostLoopSamples)


class AthChunk(Serializable):

	def __init__(self):

		self.Magic			= None
		self.UseAthCurve	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_uint8s(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"ath\0"

		self.UseAthCurve = rw.rw_uint16(self.UseAthCurve)


class CiphChunk(Serializable):

	def __init__(self):

		self.Magic			= None
		self.EncryptionType	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_uint8s(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"ciph"

		self.EncryptionType = rw.rw_uint16(self.EncryptionType)


class RvaChunk(Serializable):

	def __init__(self):

		self.Magic	= None
		self.Volume	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_uint8s(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"rva\0"

		self.Volume = rw.rw_float32(self.Volume)


class VbrChunk(Serializable):

	def __init__(self):

		self.Magic			= None
		self.MaxFrameSize	= None
		self.NoiseLevel		= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_uint8s(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"vbr\0"

		self.MaxFrameSize	= rw.rw_uint16(self.MaxFrameSize)
		self.NoiseLevel		= rw.rw_uint16(self.NoiseLevel)


class CommChunk(Serializable):

	def __init__(self):

		self.Magic		= None
		self.RESERVE	= None
		self.Comment	= None

	def __rw_hook__(self, rw):

		self.Magic = rw.rw_uint8s(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"comm"

		self.RESERVE = rw.rw_uint8(self.RESERVE)
		assert self.RESERVE == 0

		self.Comment = rw.rw_cbytestring(self.Comment)


class PadChunk(Serializable):

	def __init__(self):

		self.Magic		= None
		self.Padding	= None

	def __rw_hook__(self, rw, size):

		self.Magic = rw.rw_uint8s(self.Magic, 4)
		assert DecryptByteString(self.Magic) == b"pad\0"

		self.Padding = rw.rw_bytestring(self.Padding, size)
		# last two bytes aren't zero??? but the size is right...
		#assert self.Padding == b"\0"*size


def DecryptByteString(bs):
	return bytes([b & 0x7F for b in bs])
