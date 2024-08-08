
import array
import math

from enum import Enum
from io import BufferedReader, BytesIO

from exbip.Serializable import Serializable
from exbip.BinaryTargets.Interface.Base import EndiannessManager


class ADX(Serializable):

	def __init__(self, encodingType=3, channelCount=1, sampleRate=24000, highpassFreq=500, version=4):
		self.HeaderMagic = 0x8000
		self.HeaderSize = None
		self.EncodingType = encodingType
		self.FrameSize = 18
		self.BitDepth = 4
		self.ChannelCount = channelCount
		self.SampleRate = sampleRate
		self.SampleCount = None
		self.HighpassFreq = highpassFreq
		self.Version = version
		self.Revision = 0

		self.CodingType = None
		self.Coefficients = None
		self.SetCoefficients()

		self.Duration = None

		self.HistoryPrePad = 0
		self.HistorySamples = [array.array("H", [0, 0]) for i in range(self.ChannelCount)]
		self.HistoryPostPad = 0

		self.AinfMagic = None
		self.AinfSize = None
		self.AinfData = None

		self.InsertedSamples = 0
		self.LoopCount = None

		self.LoopType = None
		self.LoopStartSample = None
		self.LoopStartByte = None
		self.LoopEndSample = None
		self.LoopEndByte = None

		self.AudioMagic = None
		self.SamplesPerFrame = (self.FrameSize - 2) * 2
		self.FrameCount = None
		self.AudioSize = None
		self.BaseOffset = 0
		self.FirstOffset = 0
		self.AudioDataBytes = None
		self.AudioData = list()

		self.FooterMagic = 0x8001
		self.FooterPaddingSize = 0
		self.FooterPadding = None

	def update_offsets(self):
		self.tobytes()

	def write_right(self, path):
		self.update_offsets()
		self.write(path)

	def __rw_hook__(self, rw):

		rw.endianness = ">"

		self.HeaderMagic = rw.rw_uint16(self.HeaderMagic)
		assert self.HeaderMagic == 0x8000

		self.HeaderSize = rw.rw_uint16(self.HeaderSize)
		headerStart = rw.tell()

		self.EncodingType = rw.rw_uint8(self.EncodingType)
		# doesn't work in every env???
		#assert self.EncodingType in EncodingMode
		assert self.EncodingType in {2, 3, 4, 16}

		self.FrameSize = rw.rw_uint8(self.FrameSize)
		assert self.FrameSize == 18 # seems like this CAN be different, but... rarely
		self.BitDepth = rw.rw_uint8(self.BitDepth)
		assert self.BitDepth == 4

		self.ChannelCount = rw.rw_uint8(self.ChannelCount)
		self.SampleRate = rw.rw_uint32(self.SampleRate)
		self.SampleCount = rw.rw_uint32(self.SampleCount)
		self.HighpassFreq = rw.rw_uint16(self.HighpassFreq)
		self.Version = rw.rw_uint8(self.Version)
		# Revision is what gets unset/set after decrypting, it seems...?
		self.Revision = rw.rw_uint8(self.Revision)
		if self.Revision:
			self.CodingType = self.Revision

		self.Duration = int(1000*self.SampleCount/self.SampleRate)
		self.SetCoefficients()

		if self.Version == 4:
			self.HistoryPrePad = rw.rw_uint32(self.HistoryPrePad)
			assert self.HistoryPrePad == 0
			for i in range(self.ChannelCount):
				if rw.is_constructlike: # reader
					self.HistorySamples.append(None)
				self.HistorySamples[i] = rw.rw_uint16s(self.HistorySamples[i], 2)
			if self.ChannelCount == 1:
				self.HistoryPostPad = rw.rw_uint32(self.HistoryPostPad)
				assert self.HistoryPostPad == 0
			# haven't been able to test this so who knows if i'm doing it right
			# there might be an extra 4 byte pad first...?
			if rw.is_constructlike and rw.peek_bytestream(4) == b"AINF":
				self.AinfMagic = rw.rw_string(self.AinfMagic, 4)
				self.AinfSize = rw.rw_uint32(self.AinfSize)
				self.AinfData = rw.rw_uint8s(self.AinfData, self.AinfSize)

		if self.Version != 5 and rw.tell()+24 <= self.HeaderSize:
			self.InsertedSamples = rw.rw_uint16(self.InsertedSamples)
			self.LoopCount = rw.rw_uint16(self.LoopCount)
			if self.LoopCount:
				self.LoopType = rw.rw_uint32(self.LoopType)
				self.LoopStartSample = rw.rw_uint32(self.LoopStartSample)
				self.LoopStartByte = rw.rw_uint32(self.LoopStartByte)
				self.LoopEndSample = rw.rw_uint32(self.LoopEndSample)
				self.LoopEndByte = rw.rw_uint32(self.LoopEndByte)

		# i have NO idea why the amount of padding is whatever it is so fuck that i guess
		# if it breaks later on i can figure it out then
		if rw.is_parselike:
			self.AudioMagic = b"(c)CRI"
		self.AudioMagic = rw.rw_bytestring(self.AudioMagic, self.HeaderSize+4-rw.tell())
		assert self.AudioMagic == b"\x00"*(len(self.AudioMagic)-6) + b"(c)CRI"
		if rw.is_parselike:
			self.HeaderSize = rw.tell() - headerStart
		assert rw.tell() - headerStart == self.HeaderSize

		self.SamplesPerFrame = (self.FrameSize - 2) * 2
		assert self.SamplesPerFrame == 32

		self.FrameCount = math.ceil(self.SampleCount / self.SamplesPerFrame)
		self.AudioSize = self.FrameSize*self.FrameCount*self.ChannelCount

		self.BaseOffset = self.InsertedSamples // self.SamplesPerFrame * self.FrameSize
		self.FirstOffset = self.InsertedSamples % self.SamplesPerFrame

		self.AudioDataBytes = rw.rw_bytestring(self.AudioDataBytes, self.AudioSize)

		self.FooterMagic = rw.rw_uint16(self.FooterMagic)
		assert self.FooterMagic == 0x8001

		if self.LoopCount is not None and (rw.tell() + self.FrameSize) % 2048:
			paddingSize = self.FrameSize + 2048 - (rw.tell() + 2 + self.FrameSize) % 2048
		else:
			paddingSize = self.FrameSize-4
		if rw.is_parselike:
			self.FooterPaddingSize = paddingSize
		self.FooterPaddingSize = rw.rw_uint16(self.FooterPaddingSize)
		assert self.FooterPaddingSize == paddingSize

		self.FooterPadding = rw.rw_bytestring(self.FooterPadding, paddingSize)
		assert self.FooterPadding == b"\x00"*paddingSize

		failed = False
		try:
			rw.assert_eof()
		except Exception:
			failed = True

		if failed:
			print("Failed to read file!")
			remainder = rw.peek_bytestream(64)
			print(len(remainder), remainder)

	def SetCoefficients(self):
		if EncodingMode(self.EncodingType) == EncodingMode.Fixed:
			self.Coefficients = [[0, 0], [3840, 0], [7360, 62208], [6272, 62016]]
		else:
			z = math.cos(2.0*math.pi*self.HighpassFreq/self.SampleRate);
			a = math.sqrt(2)-z;
			b = math.sqrt(2)-1;
			c = (a-math.sqrt((a+b)*(a-b)))/b;
			coef1 = math.floor(c*8192)
			coef2 = math.floor(c*c*-4096)
			self.Coefficients = [[coef1, coef2]]

	def decode(self):
		pcmData = [0]*(self.SamplesPerFrame*self.ChannelCount*self.FrameCount)
		for channel in range(self.ChannelCount):
			history1, history2 = self.HistorySamples[channel]
			for i in range(self.FrameCount):
				start = self.BaseOffset + (i*self.ChannelCount + channel)*(self.FrameSize)
				filterNum = (self.AudioDataBytes[start] >> 5) & 0xF
				scale = (self.AudioDataBytes[start] << 8) + self.AudioDataBytes[start+1]
				if i == 0: #TODO: ....actually I dunno about how I've handled this
					start += self.FirstOffset // 2

				if EncodingMode(self.EncodingType) == EncodingMode.Fixed:
					scale = (scale & 0x1FFF) + 1
				elif EncodingMode(self.EncodingType) == EncodingMode.Exponential:
					scale = 1 << (12 - scale)
					assert filterNum == 0
				else:
					scale += 1
					assert filterNum == 0
				coef1, coef2 = self.Coefficients[filterNum]
				start += 2

				for j in range(self.SamplesPerFrame-(0 if i else self.FirstOffset)):
					if start + (j//2) >= self.AudioSize:
						break
					# if odd, get low nibble
					if j % 2:
						nibble = ((self.AudioDataBytes[start + (j//2)] & 0xF) ^ 0x8) - 0x8
					# if even, get high nibble
					else:
						nibble = (((self.AudioDataBytes[start + (j//2)] >> 4) & 0xF) ^ 0x8) - 0x8
					delta = nibble * scale
					prediction = (coef1 * history1 + coef2 * history2) >> 12
					sample = max(-0x8000, min(0x7FFF, prediction + delta))
					history2 = history1
					history1 = sample
					pcmData[self.ChannelCount*(i*self.SamplesPerFrame + j) + channel] = sample
		return pcmData

	def decrypt(self, keycode):
		self.crypt(keycode)
		self.Revision = 0

	def encrypt(self, keycode, codingType=None):
		assert codingType is not None or self.CodingType is not None
		if codingType is not None:
			self.Revision = codingType
		elif self.CodingType is not None:
			self.Revision = self.CodingType
		self.crypt(keycode)

	def crypt(self, keycode):
		keycode -= 1
		seed = (keycode >> 27) & 0x7FFF
		mult = ((keycode >> 12) & 0x7FFC) | 1
		inc = ((keycode << 1) & 0x7FFF) | 1
		self.AudioDataBytes = list(self.AudioDataBytes)
		xor = seed
		for i in range(self.FrameCount*self.ChannelCount):
			pos = i * self.FrameSize
			self.AudioDataBytes[pos] ^= ((xor >> 8) & 0xFF)
			if self.Revision == 9:
				self.AudioDataBytes[pos] &= 0x1F
			self.AudioDataBytes[pos+1] ^= (xor & 0xFF)
			xor = (xor * mult + inc) & 0x7FFF
		self.AudioDataBytes = bytes(self.AudioDataBytes)


class EncodingMode(Enum):
	Fixed		= 2
	Linear		= 3
	Exponential	= 4
	Ahx			= 16


if __name__ == "__main__":
	main()
