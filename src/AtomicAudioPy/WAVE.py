
import math

from exbip.Serializable import Serializable
from exbip.BinaryTargets.Interface.Base import EndiannessManager

from ADX import ADX


class WAVE(Serializable):

	def __init__(self, audioFormat=1, numChannels=1, sampleRate=24000, bitsPerSample=16):
		self.RiffMagic = "RIFF"
		self.FileSize = 0
		self.WaveMagic = "WAVE"

		self.FormatMagic = "fmt "
		self.FormatSize = 0
		self.AudioFormat = audioFormat
		self.NumChannels = numChannels
		self.SampleRate = sampleRate
		self.ByteRate = None
		self.BlockAlign = None # i should use this probably
		self.BitsPerSample = bitsPerSample

		self.DataMagic = "data"
		self.DataSize = 0
		self.Data = None

	def update_offsets(self):
		self.tobytes()

	def write_right(self, path):
		self.update_offsets()
		self.write(path)

	def __rw_hook__(self, rw):

		rw.endianness = "<"

		self.RiffMagic = rw.rw_string(self.RiffMagic, 4)
		if rw.is_parselike:
			self.RiffMagic = self.RiffMagic.decode()
		assert self.RiffMagic == "RIFF"

		self.FileSize = rw.rw_uint32(self.FileSize)
		fileStart = rw.tell()

		self.WaveMagic = rw.rw_string(self.WaveMagic, 4)
		if rw.is_parselike:
			self.WaveMagic = self.WaveMagic.decode()
		assert self.WaveMagic == "WAVE"

		self.FormatMagic = rw.rw_string(self.FormatMagic, 4)
		if rw.is_parselike:
			self.FormatMagic = self.FormatMagic.decode()
		assert self.FormatMagic == "fmt "

		self.FormatSize = rw.rw_uint32(self.FormatSize)
		formatStart = rw.tell()

		self.AudioFormat = rw.rw_uint16(self.AudioFormat)
		assert self.AudioFormat == 1 # PCM -- idk how to handle anything else lol
		self.NumChannels = rw.rw_uint16(self.NumChannels)
		self.SampleRate = rw.rw_uint32(self.SampleRate)
		if rw.is_parselike:
			self.ByteRate = math.ceil(self.SampleRate*self.BitsPerSample*self.NumChannels / 8)
		self.ByteRate = rw.rw_uint32(self.ByteRate)
		if rw.is_parselike:
			self.BlockAlign = math.ceil(self.BitsPerSample*self.NumChannels / 8)
		self.BlockAlign = rw.rw_uint16(self.BlockAlign)
		self.BitsPerSample = rw.rw_uint16(self.BitsPerSample)
		assert self.BitsPerSample == 8 or self.BitsPerSample == 16

		assert self.ByteRate == self.SampleRate*self.BitsPerSample*self.NumChannels // 8
		assert self.BlockAlign == self.BitsPerSample*self.NumChannels // 8

		if rw.is_parselike:
			self.FormatSize = rw.tell() - formatStart
		assert rw.tell() - formatStart == self.FormatSize

		print(self.NumChannels, self.SampleRate, self.BitsPerSample)

		self.DataMagic = rw.rw_string(self.DataMagic, 4)
		if rw.is_parselike:
			self.DataMagic = self.DataMagic.decode()
		assert self.DataMagic == "data"

		self.DataSize = rw.rw_uint32(self.DataSize)
		dataStart = rw.tell()

		self.Data = rw.rw_uint8s(self.Data, self.DataSize)
		if rw.is_parselike:
			self.DataSize = rw.tell() - dataStart
		assert rw.tell() - dataStart == self.DataSize

		if rw.is_parselike:
			self.FileSize = rw.tell() - fileStart
		assert rw.tell() - fileStart == self.FileSize

		failed = False
		try:
			rw.assert_eof()
		except Exception:
			failed = True

		if failed:
			print("Failed to read file!")
			remainder = rw.peek_bytestream(64)
			print(len(remainder), remainder)

	def decode(self):
		shortSamples = list()
		if self.BitsPerSample == 8:
			for sample in self.Data:
				# hmmmm. i don't think this is right
				shortSamples.append((sample << 8) ^ 0x8000)
		elif self.BitsPerSample == 16:
			for i in range(0, self.DataSize, 2):
				unsigned = ((self.Data[i+1] << 8) + self.Data[i]) & 0xFFFF
				signed = (unsigned ^ 0x8000) - 0x8000
				shortSamples.append(signed)
		else:
			raise ValueError("pls i only know how to do 8bit and 16bit TT_TT")
		print(shortSamples[:64])
		return shortSamples

	def encode(self, shortSamples):
		print(shortSamples[:64])
		if self.BitsPerSample == 8:
			byteSamples = [0]*len(shortSamples)
			for i in range(len(shortSamples)):
				byteSamples[i] = ((shortSamples[i] ^ 0x8000) >> 8) & 0xFF
			self.Data = byteSamples
		elif self.BitsPerSample == 16:
			byteSamples = [0]*(2*len(shortSamples))
			for i in range(len(shortSamples)):
				byteSamples[2*i] = shortSamples[i] & 0xFF
				byteSamples[2*i + 1] = (shortSamples[i] >> 8) & 0xFF
			self.Data = byteSamples
		else:
			raise ValueError("pls i only know how to do 8bit and 16bit TT_TT")


if __name__ == "__main__":
	main()
