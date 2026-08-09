import array
import os
import hashlib
import struct

from enum import Enum
from io import BytesIO

from UTFAFS import *
from ADX import ADX
from HCA import HCA


class ACB:

	def __init__(self, acbPath, awbPath=None):

		self.AcbPath = acbPath
		self.AwbPath = awbPath

		with open(self.AcbPath, "rb") as f:
			self.AcbBytes = f.read()
			self.AcbStruct = UTF()
			self.AcbStruct.frombytes(self.AcbBytes)

		if self.AwbPath is None:
			self.AwbBytes = None
			self.StreamAwbStruct = None
		else:
			with open(self.AwbPath, "rb") as f:
				self.AwbBytes = f.read()
				self.StreamAwbStruct = AFS2()
				self.StreamAwbStruct.frombytes(self.AwbBytes)

		self.AcfCategories = dict()
		for i in range(self.AcbStruct.GetRowField(0, "AcfReferenceTable").Value.Value.RowCount):
			if self.AcbStruct.GetRowField(0, "AcfReferenceTable").Value.Value.GetRowField(i, "Type").Value ==  3:
				catId = self.AcbStruct.GetRowField(0, "AcfReferenceTable").Value.Value.GetRowField(i, "Id").Value
				catName = self.AcbStruct.GetRowField(0, "AcfReferenceTable").Value.Value.GetRowField(i, "Name").Value.Value
				self.AcfCategories[catId] = catName

		version = self.AcbStruct.GetRowField(0, "Version").Value
		vstring = ".".join(["{:x}".format((version >> 8*i) & 0xFF) for i in reversed(range(4))])

		self.Tables = dict()

		# compatibility
		for shortTableName in ["TrackEvent", "TrackCommand", "SynthCommand", "SeqCommand"]:
			longTableName = f"{shortTableName}Table"
			if longTableName in self.AcbStruct.FieldNames:
				self.Tables[shortTableName] = self.AcbStruct.GetRowField(0, longTableName).Value.Value
			elif "CommandTable" in self.AcbStruct.FieldNames:
				self.Tables[shortTableName] = self.AcbStruct.GetRowField(0, "CommandTable").Value.Value
			else:
				raise ValueError(f"Unknown ACB version: {vstring}")

		for tableName in [
			"Cue", "CueName", "Waveform",
			"Synth", "Track", "Sequence",
			"OutsideLink", "StringValue",
			"WaveformExtensionData",
			"GlobalAisacReference",
			"Aisac", "AisacControlName", "AutoModulation", "Graph",
		]:
			self.Tables[tableName] = self.AcbStruct.GetRowField(0, f"{tableName}Table").Value.Value

		if self.AwbPath is not None:
			# these conditions needed because apparently older ACBs don't have the additional UTF table layer!
			if self.AcbStruct.GetRowField(0, "StreamAwbHash").Value.Magic == b"@UTF":
				storedAwbHash = self.AcbStruct.GetRowField(0, "StreamAwbHash").Value.Value.GetRowField(0, "Hash").Value.Value
			else:
				storedAwbHash = self.AcbStruct.GetRowField(0, "StreamAwbHash").Value.Value
			trueAwbHash = hashlib.md5(self.AwbBytes)
			# ACE-created ACBs fail this lol. sad!
			#assert storedAwbHash == array.array("B", trueAwbHash.digest())
			if self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value is not None:
				if self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Magic == b"@UTF":
					self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value.GetRowField(0, "Header").Value.Value.check_equal(self.StreamAwbStruct)
				else:
					self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value.check_equal(self.StreamAwbStruct)

		if "Id" in self.Tables["Waveform"].FieldNames:
			self.SimpleAwbId = True
		elif "MemoryAwbId" in self.Tables["Waveform"].FieldNames and "StreamAwbId" in self.Tables["Waveform"].FieldNames:
			self.SimpleAwbId = False
		else:
			raise ValueError(f"Unknown ACB version: {vstring}")

		self.MemoryAwbStruct = self.AcbStruct.GetRowField(0, "AwbFile").Value.Value

		self.CueId2CueNameRow = dict()
		self.CueId2CueRow = dict()
		for i in range(self.Tables["CueName"].RowCount):
			cueIndex = self.Tables["CueName"].GetRowField(i, "CueIndex").Value

			cueId = self.Tables["Cue"].GetRowField(cueIndex, "CueId").Value
			self.CueId2CueNameRow[cueId] = i
			self.CueId2CueRow[cueId] = cueIndex

		self.MemoryAwbId2WaveformRow = dict()
		self.StreamAwbId2WaveformRow = dict()
		for j in range(self.Tables["Waveform"].RowCount):
			streamingEnum = self.Tables["Waveform"].GetRowField(j, "Streaming").Value
			toStreamOrNotToStream = list()
			if streamingEnum == 0 or streamingEnum == 2:
				toStreamOrNotToStream.append(False)
			if streamingEnum == 1 or streamingEnum == 2:
				toStreamOrNotToStream.append(True)
			for streaming in toStreamOrNotToStream:
				if streaming:
					if self.SimpleAwbId:
						awbId = self.Tables["Waveform"].GetRowField(j, "Id").Value
					else:
						awbId = self.Tables["Waveform"].GetRowField(j, "StreamAwbId").Value
						if streamingEnum == 1:
							assert self.Tables["Waveform"].GetRowField(j, "MemoryAwbId").Value == 0xFFFF
					if awbId not in self.StreamAwbId2WaveformRow:
						self.StreamAwbId2WaveformRow[awbId] = set()
					self.StreamAwbId2WaveformRow[awbId].add(j)
				else:
					if self.SimpleAwbId:
						awbId = self.Tables["Waveform"].GetRowField(j, "Id").Value
					else:
						awbId = self.Tables["Waveform"].GetRowField(j, "MemoryAwbId").Value
						if streamingEnum == 0:
							assert self.Tables["Waveform"].GetRowField(j, "StreamAwbId").Value == 0xFFFF
					if awbId not in self.MemoryAwbId2WaveformRow:
						self.MemoryAwbId2WaveformRow[awbId] = set()
					self.MemoryAwbId2WaveformRow[awbId].add(j)

		self.AisacControlIdToName = dict()
		if self.Tables["AisacControlName"] is not None:
			for i in range(self.Tables["AisacControlName"].RowCount):
				controlId = self.Tables["AisacControlName"].GetRowField(i, "AisacControlId").Value
				controlName = self.Tables["AisacControlName"].GetRowField(i, "AisacControlName").Value.Value
				self.AisacControlIdToName[controlId] = controlName
				print(controlId, controlName)

	def RefreshHash(self):
		#if self.AwbPath is not None:
		if self.StreamAwbStruct is not None:
			# get offsets correct before getting actual bytes
			self.StreamAwbStruct.update_offsets()
			if self.AcbStruct.GetRowField(0, "StreamAwbHash").Value.Magic == b"@UTF":
				self.AcbStruct.GetRowField(0, "StreamAwbHash").Value.Value.GetRowField(0, "Hash").Value.Value = array.array("B", hashlib.md5(self.StreamAwbStruct.tobytes()).digest())
				storedAwbHash = self.AcbStruct.GetRowField(0, "StreamAwbHash").Value.Value.GetRowField(0, "Hash").Value.Value
			else:
				self.AcbStruct.GetRowField(0, "StreamAwbHash").Value.Value = array.array("B", hashlib.md5(self.StreamAwbStruct.tobytes()).digest())
				storedAwbHash = self.AcbStruct.GetRowField(0, "StreamAwbHash").Value.Value
			self.AwbBytes = self.StreamAwbStruct.tobytes()
			trueAwbHash = hashlib.md5(self.AwbBytes)
			assert storedAwbHash == array.array("B", trueAwbHash.digest())

	def PrettyPrint(self):
		for cueId in sorted(self.CueId2CueNameRow):
			cueRow = self.CueId2CueRow[cueId]
			duration = self.Tables["Cue"].GetRowField(cueRow, "Length").Value #/1000
			cueNameRow = self.CueId2CueNameRow[cueId]
			cueName = self.Tables["CueName"].GetRowField(cueNameRow, "CueName").Value.Value
			if duration == 0 or duration == 0xFFFFFFFF:
				print(f"Cue #{cueId}: {cueName}")
			else:
				print(f"Cue #{cueId}: {cueName}", "({}s)".format(duration/1000))
			refType = self.Tables["Cue"].GetRowField(cueRow, "ReferenceType").Value
			refIndex = self.Tables["Cue"].GetRowField(cueRow, "ReferenceIndex").Value
			self.RecursivelyGetReferences(refType, refIndex, depth=1, ind=0, printing=True, extracting=False)
			print()

	def PrintCmds(self, cmdBytes, depth=0):
		while cmdBytes and cmdBytes != [0]:
			cmdType = (cmdBytes.pop(0) << 8) + cmdBytes.pop(0)
			paramCount = cmdBytes.pop(0)
			params = [cmdBytes.pop(0) for j in range(paramCount)]
			self.PrintCmd(cmdType, paramCount, params, depth=depth)

	def PrintCmd(self, cmdType, paramCount, params, depth=0):
		if CommandType(cmdType) == CommandType.VolumeBus:
			stringInd, volume = ParamsToArgs(params, [2, 2])
			busName = self.Tables["StringValue"].GetRowField(stringInd, "StringValue").Value.Value
			print("{}{}({}) = {}/10000".format(" "*(depth+2), CommandType(cmdType).name, busName, volume))
		elif CommandType(cmdType) == CommandType.CuePriorityMode:
			print("{}{}({})".format(" "*(depth+2), CommandType(cmdType).name, params[0]))
		elif CommandType(cmdType) == CommandType.CuePriority:
			val = struct.unpack("!b", bytes(params))[0]
			print("{}{} = {}".format(" "*(depth+2), CommandType(cmdType).name, val))
		elif CommandType(cmdType) == CommandType.CuePriorityModeAndValue or CommandType(cmdType) == CommandType.PriorityModeAndValue:
			val = struct.unpack("!b", bytes(params[1:]))[0]
			print("{}{}({}) = {}".format(" "*(depth+2), CommandType(cmdType).name, params[0], val))
		elif CommandType(cmdType) == CommandType.Pan3dAngle:
			angle = struct.unpack("!h", bytes(params))[0]
			print("{}{} = {}".format(" "*(depth+2), CommandType(cmdType).name, angle))
		elif CommandType(cmdType) == CommandType.MaximumPitch:
			pitch = struct.unpack("!h", bytes(params))[0]
			print("{}{} = {}".format(" "*(depth+2), CommandType(cmdType).name, pitch))
		elif CommandType(cmdType) == CommandType.VolumeEnvelopeAttackRateAndCurve or CommandType(cmdType) == CommandType.VolumeEnvelopeReleaseRateAndCurve or CommandType(cmdType) == CommandType.VolumeEnvelopeDelayAndHold or CommandType(cmdType) == CommandType.VolumeEnvelopeDecayRateAndCurve:
			unk1, unk2 = ParamsToArgs(params, [2, 2])
			print("{}{} = {}, {}".format(" "*(depth+2), CommandType(cmdType).name, unk1, unk2))
		elif CommandType(cmdType) == CommandType.VolumeEnvelopeSustainLevel:
			level = ParamsToArgs(params, [2])[0]
			print("{}{} = {}".format(" "*(depth+2), CommandType(cmdType).name, level))
		elif CommandType(cmdType) == CommandType.Category:
			assert paramCount % 4 == 0
			acfCategories = list()
			for acfCategoryId in ParamsToArgs(params, [4]*(paramCount//4)):
				assert acfCategoryId in self.AcfCategories
				acfCategories.append(self.AcfCategories[acfCategoryId])
			print("{}{} = {}".format(" "*(depth+2), CommandType(cmdType).name, ", ".join(acfCategories)))
			assert not params
		elif CommandType(cmdType) == CommandType.GlobalAisacReference:
			ind = ParamsToArgs(params, [2])[0]
			print("{}{}({})".format(" "*(depth+2), CommandType(cmdType).name, ind))
		elif CommandType(cmdType) == CommandType.Pan3dInteriorDistanceGain:
			unk = ParamsToArgs(params, [2])[0]
			print("{}{} = {}".format(" "*(depth+2), CommandType(cmdType).name, unk))
		elif CommandType(cmdType) == CommandType.Pos3dDistanceMin or CommandType(cmdType) == CommandType.Pos3dDistanceMax:
			assert paramCount == 4
			flt = struct.unpack("!f", bytes(params))[0]
			print("{}{} = {}".format(" "*(depth+2), CommandType(cmdType).name, flt))
		elif CommandType(cmdType) == CommandType.CueLimits:
			limit1, limit2 = ParamsToArgs(params, [2, 2])
			print("{}{} = {}, {}".format(" "*(depth+2), CommandType(cmdType).name, limit1, limit2))
		elif CommandType(cmdType) == CommandType.CueLimitsAndMode:
			limit1, limit2, mode = ParamsToArgs(params, [2, 2, 1])
			print("{}{}({}) = {}, {}".format(" "*(depth+2), CommandType(cmdType).name, mode, limit1, limit2))
		elif CommandType(cmdType) == CommandType.VolumeGain_Res100:
			gain = ParamsToArgs(params, [2])[0]
			print("{}{} = {}%".format(" "*(depth+2), CommandType(cmdType).name, gain))
		elif CommandType(cmdType) == CommandType.VolumeBus:
			stringInd, volume = ParamsToArgs(params, [2, 2])
			busName = self.Tables["StringValue"].GetRowField(stringInd, "StringValue").Value.Value
			print("{}{}({}) = {}/10000".format(" "*(depth+2), CommandType(cmdType).name, busName, volume))
		elif CommandType(cmdType) == CommandType.Selector:
			selectId = ParamsToArgs(params, [2])[0]
			print("{}{}({})".format(" "*(depth+2), CommandType(cmdType).name, selectId))
		elif CommandType(cmdType) == CommandType.VolumeBus:
			stringInd, volume = ParamsToArgs(params, [2, 2])
			busName = self.Tables["StringValue"].GetRowField(stringInd, "StringValue").Value.Value
			print("{}{}({}) = {}/10000".format(" "*(depth+2), CommandType(cmdType).name, busName, volume))
		elif CommandType(cmdType) == CommandType.Biquad:
			unk1, unk2, unk3, unk4 = ParamsToArgs(params, [1, 2, 2, 2])
			print("{}{} ({}, {}, {}, {})".format(" "*(depth+2), CommandType(cmdType).name, unk1, unk2, unk3, unk4))
		elif CommandType(cmdType) == CommandType.Bandpass:
			unk1, unk2 = ParamsToArgs(params, [2, 2])
			print("{}{} ({}, {})".format(" "*(depth+2), CommandType(cmdType).name, unk1, unk2))
		elif CommandType(cmdType) == CommandType.TrackSelectorLabel:
			selectId, selectVal = ParamsToArgs(params, [2, 2])
			print("{}{}({}) = {}".format(" "*(depth+2), CommandType(cmdType).name, selectId, selectVal))
		else:
			print("{}{} ({})".format(" "*(depth+2), CommandType(cmdType).name, ", ".join(str(p) for p in params)))

	def PrintLocalAisacs(self, tableName, refIndex, depth=0):
		aisacBytes = self.Tables[tableName].GetRowField(refIndex, "LocalAisacs").Value.Value
		if aisacBytes is not None:
			aisacControls = list()
			aisacAutomations = list()
			aisacAutoModulations = list()
			for aisacInd in ParamsToArgs(aisacBytes, [2]*(len(aisacBytes)//2)):
				print(self.Tables["Aisac"].GetRowField(aisacInd, "Id").Value, self.Tables["Aisac"].GetRowField(aisacInd, "Type").Value)
				print(self.Tables["Aisac"].GetRowField(aisacInd, "AutoModulationIndex").Value, self.Tables["Aisac"].GetRowField(aisacInd, "GraphIndexes").Value.Value)
				controlId = self.Tables["Aisac"].GetRowField(aisacInd, "ControlId").Value
				autoModInd = self.Tables["Aisac"].GetRowField(aisacInd, "AutoModulationIndex").Value
				graphInds = self.Tables["Aisac"].GetRowField(aisacInd, "GraphIndexes").Value.Value
				if controlId >= 3000:
					autoModInd = self.Tables["Aisac"].GetRowField(aisacInd, "AutoModulationIndex").Value
					#print("#####", self.Tables["AutoModulation"].GetRowField(autoModInd, "Type").Value)
					#print("#####", self.Tables["AutoModulation"].GetRowField(autoModInd, "TriggerType").Value)
					#print("#####", self.Tables["AutoModulation"].GetRowField(autoModInd, "Time").Value)
					#print("#####", self.Tables["AutoModulation"].GetRowField(autoModInd, "Key").Value)
				elif controlId >= 2000:
					assert autoModInd == 0xFFFF
				else:
					assert autoModInd == 0xFFFF
					aisacControls.append(self.AisacControlIdToName[controlId])
			print("{}Local Aisacs:".format(" "*depth))
			if aisacControls:
				print("{}Controls: {}".format(" "*(depth+1), ", ".join(aisacControls)))
			print("{}Automations: ".format(" "*(depth+1)))
			print("{}Modulations: ".format(" "*(depth+1)))

	def PrintGlobalAisacs(self, tableName, refIndex, depth=0):
		globalAisacStart = self.Tables[tableName].GetRowField(refIndex, "GlobalAisacStartIndex").Value
		globalAisacCount = self.Tables[tableName].GetRowField(refIndex, "GlobalAisacNumRefs").Value
		if globalAisacStart != 0xFFFF and globalAisacCount > 0:
			print("{}Global Aisacs:".format(" "*(depth+1)))
			for globalAisacInd in range(globalAisacStart, globalAisacStart+globalAisacCount):
				globalAisacName = self.Tables["GlobalAisacReference"].GetRowField(globalAisacInd, "Name").Value.Value
				print("{}{}".format(" "*(depth+2), globalAisacName))

	def RecursivelyGetReferences(self, refType, refIndex, depth=0, ind=0, printing=False, keycode=None, outputFormat=None, path="", extracting=False):
		if ReferenceType(refType) == ReferenceType.Waveform:
			streamingEnum = self.Tables["Waveform"].GetRowField(refIndex, "Streaming").Value
			encodeType = self.Tables["Waveform"].GetRowField(refIndex, "EncodeType").Value
			extIndex = self.Tables["Waveform"].GetRowField(refIndex, "ExtensionData").Value
			toStreamOrNotToStream = list()
			if streamingEnum == 0 or streamingEnum == 2:
				toStreamOrNotToStream.append(False)
			if streamingEnum == 1 or streamingEnum == 2:
				toStreamOrNotToStream.append(True)
			for streaming in toStreamOrNotToStream:
				if streaming:
					awb = self.StreamAwbStruct
					if self.SimpleAwbId:
						awbId = self.Tables["Waveform"].GetRowField(refIndex, "Id").Value
					else:
						awbId = self.Tables["Waveform"].GetRowField(refIndex, "StreamAwbId").Value
						if streamingEnum == 1:
							assert self.Tables["Waveform"].GetRowField(refIndex, "MemoryAwbId").Value == 0xFFFF
				else:
					awb = self.MemoryAwbStruct
					if self.SimpleAwbId:
						awbId = self.Tables["Waveform"].GetRowField(refIndex, "Id").Value
					else:
						awbId = self.Tables["Waveform"].GetRowField(refIndex, "MemoryAwbId").Value
						if streamingEnum == 0:
							assert self.Tables["Waveform"].GetRowField(refIndex, "StreamAwbId").Value == 0xFFFF
				#assert awb is not None
				audio = None
				if awb is not None and (printing or (extracting and keycode is not None)):
					if EncodeExt[encodeType] == "ADX":
						audio = ADX()
						audio.frombytes(awb.EntryData[awb.IdToInd[awbId]])
					elif EncodeExt[encodeType] == "HCA":
						audio = HCA()
						audio.frombytes(awb.EntryData[awb.IdToInd[awbId]])
				if printing:
					print("{}Waveform{} from {} AWB".format(" "*depth, "" if streaming or not streamingEnum else " (Dummy)", "Streaming" if streaming else "Memory"))
					print("{}ID: {}".format(" "*(depth+1), awbId))
					print("{}Type: {}".format(" "*(depth+1), EncodeExt[encodeType]))
					print("{}Channels: {}".format(" "*(depth+1), self.Tables["Waveform"].GetRowField(refIndex, "NumChannels").Value))
					print("{}Loop: {}".format(" "*(depth+1), self.Tables["Waveform"].GetRowField(refIndex, "LoopFlag").Value))
					if extIndex != 0xFFFF:
						print("{}Loop Start: {}".format(" "*(depth+2), self.Tables["WaveformExtensionData"].GetRowField(extIndex, "LoopStart").Value))
						print("{}Loop End: {}".format(" "*(depth+2), self.Tables["WaveformExtensionData"].GetRowField(extIndex, "LoopEnd").Value))
					print("{}Sampling Rate: {}".format(" "*(depth+1), self.Tables["Waveform"].GetRowField(refIndex, "SamplingRate").Value))
					print("{}Samples: {}".format(" "*(depth+1), self.Tables["Waveform"].GetRowField(refIndex, "NumSamples").Value))
					if audio is not None:
						print("{}Audio File:".format(" "*(depth+1)))
						print("{}Channels: {}".format(" "*(depth+2), audio.ChannelCount))
						print("{}Loops: {}".format(" "*(depth+2), audio.LoopCount))
						if audio.LoopCount:
							print("{}Loop Start: {}".format(" "*(depth+3), audio.LoopStartSample - audio.InsertedSamples))
							print("{}Loop End: {}".format(" "*(depth+3), audio.LoopEndSample - audio.InsertedSamples))
						print("{}Sampling Rate: {}".format(" "*(depth+2), audio.SampleRate))
						print("{}Samples: {}".format(" "*(depth+2), audio.SampleCount))
				# i'm gonna say... for the sake of cue-based extraction, when streaming == 2, ignore the dummy memory waveform
				if extracting and (streaming or not streamingEnum):
					if outputFormat is not None:
						output_ext = outputFormat
					else:
						output_ext = EncodeExt[encodeType]
					filename = f"{path}.{output_ext}"
					if audio is not None:
						if keycode is not None:
							if EncodeExt[encodeType] == "ADX":
								audio.decrypt(keycode)
							elif EncodeExt[encodeType] == "HCA":
								if awb.Key:
									audio.Crypt(keycode * ((awb.Key << 16) | ((~awb.Key + 2) + 2**16)))
								else:
									audio.Crypt(keycode)
						audio.write_right(filename)
					elif awb is not None:
						with open(filename, "wb") as f:
							f.write(awb.EntryData[awbId])
					else:
						print("{}Matching AWB not found; skipping extraction for {}.".format(" "*(depth+3) if printing else "", filename))
		elif ReferenceType(refType) == ReferenceType.Synth or ReferenceType(refType) == ReferenceType.LinkedSynth:
			if printing:
				print("{}Synth #{}".format(" "*depth, ind+1))
				self.PrintLocalAisacs("Synth", refIndex, depth=depth)
				self.PrintGlobalAisacs("Synth", refIndex, depth=depth)
				cmdIndex = self.Tables["Synth"].GetRowField(refIndex, "CommandIndex").Value
				if cmdIndex != 0xFFFF:
					cmdBytes = list(self.Tables["SynthCommand"].GetRowField(cmdIndex, "Command").Value.Value)
					print("{}Synth Commands:".format(" "*(depth+1)))
					self.PrintCmds(cmdBytes, depth=depth)
			refItems2 = self.Tables["Synth"].GetRowField(refIndex, "ReferenceItems").Value.Value
			refType2 = (refItems2[0] << 8) + refItems2[1]
			refIndex2 = (refItems2[2] << 8) + refItems2[3]
			self.RecursivelyGetReferences(refType2, refIndex2, depth=depth+1, ind=0, printing=printing, keycode=keycode, outputFormat=outputFormat, path=path, extracting=extracting)
		elif ReferenceType(refType) == ReferenceType.Sequence or ReferenceType(refType) == ReferenceType.LinkedSequence:
			seqType = self.Tables["Sequence"].GetRowField(refIndex, "Type").Value
			pbr = self.Tables["Sequence"].GetRowField(refIndex, "PlaybackRatio").Value
			##### Category. etc.
			if printing:
				print("{}{} Sequence (x{} speed)".format(" "*depth, SequenceType(seqType).name, pbr/100))
				self.PrintLocalAisacs("Sequence", refIndex, depth=depth)
				self.PrintGlobalAisacs("Sequence", refIndex, depth=depth)
				cmdIndex = self.Tables["Sequence"].GetRowField(refIndex, "CommandIndex").Value
				if cmdIndex != 0xFFFF:
					cmdBytes = list(self.Tables["SeqCommand"].GetRowField(cmdIndex, "Command").Value.Value)
					print("{}Sequence Commands:".format(" "*(depth+1)))
					self.PrintCmds(cmdBytes, depth=depth)
			#####
			numTracks = self.Tables["Sequence"].GetRowField(refIndex, "NumTracks").Value
			trackIndex = self.Tables["Sequence"].GetRowField(refIndex, "TrackIndex").Value.Value
			trackValues = self.Tables["Sequence"].GetRowField(refIndex, "TrackValues").Value.Value
			for i in range(numTracks):
				trackId = (trackIndex[2*i] << 8) + trackIndex[(2*i)+1]
				if printing and trackValues:
					print("{}Track Value: {}".format(" "*(depth+1), (trackValues[2*i] << 8) + trackValues[(2*i)+1]))
				self.RecursivelyGetReferences(ReferenceType.Track.value, trackId, depth=depth+1, ind=i, printing=printing, keycode=keycode, outputFormat=outputFormat, path=f"{path}.{i}", extracting=extracting)
		elif ReferenceType(refType) == ReferenceType.Track:
			eventIndex = self.Tables["Track"].GetRowField(refIndex, "EventIndex").Value
			if printing:
				print("{}Track #{}".format(" "*depth, ind+1))
				self.PrintLocalAisacs("Track", refIndex, depth=depth)
				self.PrintGlobalAisacs("Track", refIndex, depth=depth)
				cmdIndex = self.Tables["Track"].GetRowField(refIndex, "CommandIndex").Value
				if cmdIndex != 0xFFFF:
					cmdBytes = list(self.Tables["TrackCommand"].GetRowField(cmdIndex, "Command").Value.Value)
					print("{}Track Commands:".format(" "*(depth+1)))
					self.PrintCmds(cmdBytes, depth=depth)
			ind = 0
			cmdBytes = list(self.Tables["TrackEvent"].GetRowField(eventIndex, "Command").Value.Value)
			# ...ok, track events are more complicated than the rest so I'm leaving them independent for now....
			while cmdBytes and cmdBytes != [0]:
				cmdType = (cmdBytes.pop(0) << 8) + cmdBytes.pop(0)
				paramCount = cmdBytes.pop(0)
				params = [cmdBytes.pop(0) for j in range(paramCount)]
				if CommandType(cmdType) == CommandType.NoteOn:
					refType2, refIndex2 = ParamsToArgs(params, [2, 2])
					self.RecursivelyGetReferences(refType2, refIndex2, depth=depth+1, ind=ind, printing=printing, keycode=keycode, outputFormat=outputFormat, path=f"{path}.{ind}", extracting=extracting)
					ind += 1
				elif CommandType(cmdType) == CommandType.NoteOnWithNo:
					refType2, refIndex2, unk = ParamsToArgs(params, [2, 2, 2])
					self.RecursivelyGetReferences(refType2, refIndex2, depth=depth+1, ind=ind, printing=printing, keycode=keycode, outputFormat=outputFormat, path=f"{path}.{ind}", extracting=extracting)
					ind += 1
				elif printing and CommandType(cmdType) == CommandType.Delay:
					milliseconds = ParamsToArgs(params, [4])[0]
					print("{}{} = {} ms".format(" "*(depth+1), CommandType(cmdType).name, milliseconds))
				elif printing and CommandType(cmdType) == CommandType.LoopStart:
					loopId, loopCount = ParamsToArgs(params, [2, 2])
					if loopCount == 0xFFFF:
						print("{}{} (Loop[{}]: indefinite)".format(" "*(depth+1), CommandType(cmdType).name, loopId))
					else:
						print("{}{} (Loop #{}: x{})".format(" "*(depth+1), CommandType(cmdType).name, loopId, loopCount))
				elif printing and CommandType(cmdType) == CommandType.LoopEnd:
					loopId, unk1, unk2 = ParamsToArgs(params, [2, 2, 2])
					print("{}{} (Loop [{}]: {}, {})".format(" "*(depth+1), CommandType(cmdType).name, loopId, unk1, unk2))
				elif printing and cmdType:
					print("{}Track Event: {} ({})".format(" "*(depth+1), CommandType(cmdType).name, ", ".join(str(p) for p in params)))
		elif ReferenceType(refType) == ReferenceType.LinkedCue:
			if self.Tables["OutsideLink"] is not None:
				acbIndex = self.Tables["OutsideLink"].GetRowField(refIndex, "AcbNameStringIndex").Value
				if acbIndex == 0xFFFF and printing:
					linkId = self.Tables["OutsideLink"].GetRowField(refIndex, "Id").Value
					print("{}Link to Cue #{}".format(" "*depth, linkId))


	def ReplaceWaveform(self, awbId, streaming, replacementBytes, replacementType=0):
		awb = self.StreamAwbStruct if streaming else self.MemoryAwbStruct
		mapper = self.StreamAwbId2WaveformRow if streaming else self.MemoryAwbId2WaveformRow
		if EncodeExt[replacementType] == "ADX":
			audio = ADX()
		elif EncodeExt[replacementType] == "HCA":
			audio = HCA()
		else:
			raise ValueError("Filetypes other than ADX and HCA not yet implemented.")
		audio.frombytes(replacementBytes)
		if awbId in mapper:
			for row in mapper[awbId]:
				self.Tables["Waveform"].SetRowField(row, "EncodeType", replacementType)
				self.Tables["Waveform"].SetRowField(row, "NumChannels", audio.ChannelCount)
				extIndex = self.Tables["Waveform"].GetRowField(row, "ExtensionData").Value
				if audio.LoopCount:
					self.Tables["Waveform"].SetRowField(row, "LoopFlag", 2)
					if self.Tables["WaveformExtensionData"] is None:
						self.AcbStruct.SetRowField(0, f"WaveformExtensionDataTable", RefData(magic=b"@UTF", value=UTF(
							encodingType=self.AcbStruct.EncodingType,
							tableName=RefString(encodingType=self.AcbStruct.EncodingType, value="WaveformExtensionData"),
							columnCount=2,
							fields=[
								Field(typeFlag=4, name=RefString(encodingType=self.AcbStruct.EncodingType, value="LoopStart")),
								Field(typeFlag=4, name=RefString(encodingType=self.AcbStruct.EncodingType, value="LoopEnd")),
							],
						)))
						self.AcbStruct.GetRowField(0, f"WaveformExtensionDataTable").Value.Length = 1 # dummy
						self.Tables["WaveformExtensionData"] = self.AcbStruct.GetRowField(0, f"WaveformExtensionDataTable").Value.Value
						self.AcbStruct.update_offsets()
					if extIndex == 0xFFFF:
						extIndex = self.AddWaveformExtensionRow(audio.LoopStartSample - audio.InsertedSamples, audio.LoopEndSample - audio.InsertedSamples)
					self.Tables["Waveform"].SetRowField(row, "ExtensionData", extIndex)
					self.Tables["WaveformExtensionData"].SetRowField(extIndex, "LoopStart", audio.LoopStartSample - audio.InsertedSamples)
					self.Tables["WaveformExtensionData"].SetRowField(extIndex, "LoopEnd", audio.LoopEndSample - audio.InsertedSamples)
				else:
					self.Tables["Waveform"].SetRowField(row, "LoopFlag", 1)
					self.Tables["Waveform"].SetRowField(row, "ExtensionData", 0xFFFF) # I don't feel like deleting the row if it exists, whatever
				self.Tables["Waveform"].SetRowField(row, "SamplingRate", audio.SampleRate)
				self.Tables["Waveform"].SetRowField(row, "NumSamples", audio.LoopEndSample - audio.InsertedSamples if audio.LoopCount else audio.SampleCount)
				awb.EntryData[awb.IdToInd[awbId]] = replacementBytes
			if streaming:
				self.StreamAwbStruct.update_offsets()
				if self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value is not None:
					if self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Magic == b"@UTF":
						self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value.GetRowField(0, "Header").Value.Value.set_equal(self.StreamAwbStruct)
					else:
						self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value.set_equal(self.StreamAwbStruct)
				self.RefreshHash()
			self.AcbStruct.update_offsets()
		else:
			raise ValueError("{} AWB doesn't contain an entry with ID {}.".format("Streamed" if streaming else "In-memory", awbId))

	# new AWB entry
	def AddAwbEntry(self, streaming, newBytes, awbId=None):
		if not streaming and not self.MemoryAwbStruct:
			self.MemoryAwbStruct = AFS2()
		awbMap = self.StreamAwbStruct.IdToInd if streaming else self.MemoryAwbStruct.IdToInd
		if awbId is None:
			awbId = 0
			for existingId in awbMap:
				if existingId+1 not in awbMap:
					awbId = existingId+1
					break
		assert awbId not in awbMap

		awb = self.StreamAwbStruct if streaming else self.MemoryAwbStruct
		assert awb is not None

		awb.EntryCount += 1
		entry = (max([entry2.Value for entry2 in awb.EntryIds]) if awb.EntryIds else 0) + 1

		entryId = AfsValue()
		entryId.FieldLength = awb.IdFieldLength
		entryId.Value = awbId
		awb.EntryIds.append(entryId)

		if awb.EndPosition.Value % awb.Align:
			awb.EntryPads.append(b"\x00"*(awb.Align - (awb.EndPosition.Value % awb.Align)))
		else:
			awb.EntryPads.append(None)

		awb.EntryPositions.append(awb.EndPosition)

		endPosition = AfsValue()
		endPosition.FieldLength = awb.PositionFieldLength
		endPosition.Value = awb.EndPosition.Value + len(newBytes)
		awb.EndPosition = endPosition
	
		awb.EntryData.append(newBytes)
		if streaming:
			self.StreamAwbStruct.update_offsets()
			if self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value is not None:
				if self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Magic == b"@UTF":
					self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value.GetRowField(0, "Header").Value.Value.set_equal(self.StreamAwbStruct)
				else:
					self.AcbStruct.GetRowField(0, "StreamAwbAfs2Header").Value.Value.set_equal(self.StreamAwbStruct)
			self.RefreshHash()
		else:
			self.AcbStruct.update_offsets()
		return awbId

	def AddWaveformRow(self, streaming, newType, awbId):
		awb = self.StreamAwbStruct if streaming else self.MemoryAwbStruct
		assert awb is not None
		if EncodeExt[newType] == "ADX":
			audio = ADX()
		elif EncodeExt[newType] == "HCA":
			audio = HCA()
		else:
			raise ValueError("Filetypes other than ADX and HCA not yet implemented.")
		audio.frombytes(awb.EntryData[awbId])

		extIndex = 0xFFFF
		if audio.LoopCount:
			if self.Tables["WaveformExtensionData"] is None:
				self.AcbStruct.SetRowField(0, f"WaveformExtensionDataTable", RefData(magic=b"@UTF", value=UTF(
					encodingType=self.AcbStruct.EncodingType,
					tableName=RefString(encodingType=self.AcbStruct.EncodingType, value="WaveformExtensionData"),
					columnCount=2,
					fields=[
						Field(typeFlag=4, name=RefString(encodingType=self.AcbStruct.EncodingType, value="LoopStart")),
						Field(typeFlag=4, name=RefString(encodingType=self.AcbStruct.EncodingType, value="LoopEnd")),
					],
				)))
				self.AcbStruct.GetRowField(0, f"WaveformExtensionDataTable").Value.Length = 1 # dummy
				self.Tables["WaveformExtensionData"] = self.AcbStruct.GetRowField(0, f"WaveformExtensionDataTable").Value.Value
				self.AcbStruct.update_offsets()
			extIndex = self.AddWaveformExtensionRow(audio.LoopStartSample - audio.InsertedSamples, audio.LoopEndSample - audio.InsertedSamples)

		rowFields = {
			"EncodeType": newType,
			"Streaming": streaming,
			"NumChannels": audio.ChannelCount,
			"LoopFlag": 2 if audio.LoopCount else 1, # I think this means no loop; 0 also does, and 2 means loop
			"SamplingRate": audio.SampleRate,
			"NumSamples": audio.LoopEndSample - audio.InsertedSamples if audio.LoopCount else audio.SampleCount,
			"ExtensionData": extIndex,
			"StreamAwbPortNo": 0, # multiple AWBs??
			"LipMorthIndex": 0xFFFF, # only in recent versions... older versions will just ignore this
		}
		if self.SimpleAwbId:
			rowFields["Id"] = awbId
		elif streaming:
			rowFields["MemoryAwbId"] = 0xFFFF
			rowFields["StreamAwbId"] = awbId
		else:
			rowFields["MemoryAwbId"] = awbId
			rowFields["StreamAwbId"] = 0xFFFF
		waveRow = self.Tables["Waveform"].RowCount
		self.Tables["Waveform"].AddRow(rowFields)
		return audio.Duration, waveRow

	def AddWaveformExtensionRow(self, loopStart, loopEnd):
		extRow = self.Tables["WaveformExtensionData"].RowCount
		self.Tables["WaveformExtensionData"].AddRow({
			"LoopStart": loopStart,
			"LoopEnd": loopEnd,
		})
		return extRow

	def AddSynthRow(self, waveRow, baseSynthInd=None):
		refBytes = list()
		refType = ReferenceType.Waveform.value
		refBytes.append((refType >> 8) & 0xFF)
		refBytes.append(refType & 0xFF)
		refBytes.append((waveRow >> 8) & 0xFF)
		refBytes.append(waveRow & 0xFF)

		synthRow = self.Tables["Synth"].RowCount
		if baseSynthInd is None:
			self.Tables["Synth"].AddRow({
				"Type": 0,
				"VoiceLimitGroupName": RefString(encodingType=self.Tables["Synth"].EncodingType),
				"CommandIndex": 0xFFFF,
				"ReferenceItems": RefData(length=4, magic=b"\x00"*4, value=array.array("B", refBytes)),
				"LocalAisacs": RefData(),
				"GlobalAisacStartIndex": 0xFFFF,
				"GlobalAisacNumRefs": 0,
				"ControlWorkArea1": 0,
				"ControlWorkArea2": 0,
				"TrackValues": RefData(),
				"ParameterPallet": 0xFFFF,
				"ActionTrackStartIndex": 0xFFFF,
				"NumActionTracks": 0,
			})
		else:
			self.Tables["Synth"].CopyRow(baseSynthInd)
			self.Tables["Synth"].SetRowField(synthRow, "ReferenceItems", RefData(length=4, magic=b"\x00"*4, value=array.array("B", refBytes)))
			globalAisacStart = self.Tables["Synth"].GetRowField(synthRow, "GlobalAisacStartIndex").Value
			globalAisacCount = self.Tables["Synth"].GetRowField(synthRow, "GlobalAisacNumRefs").Value
			if globalAisacStart != 0xFFFF and globalAisacCount > 0:
				newStart = self.Tables["GlobalAisacReference"].RowCount
				for globalAisacInd in range(globalAisacCount):
					globalAisacName = self.Tables["GlobalAisacReference"].GetRowField(globalAisacStart+globalAisacInd, "Name").Value.Value
					self.Tables["GlobalAisacReference"].CopyRow(globalAisacStart+globalAisacInd)
				self.Tables["Synth"].SetRowField(synthRow, "GlobalAisacStartIndex", newStart)
		return synthRow

	def AddTrackEventRow(self, synthRow):
		cmdBytes = list()
		cmdType = CommandType.NoteOn.value
		cmdBytes.append((cmdType >> 8) & 0xFF)
		cmdBytes.append(cmdType & 0xFF)
		cmdBytes.append(4)
		refType = ReferenceType.Synth.value
		cmdBytes.append((refType >> 8) & 0xFF)
		cmdBytes.append(refType & 0xFF)
		cmdBytes.append((synthRow >> 8) & 0xFF)
		cmdBytes.append(synthRow & 0xFF)
		cmdBytes += [0, 0, 0] # null command
		assert len(cmdBytes) == 10

		cmdRow = self.Tables["TrackEvent"].RowCount
		self.Tables["TrackEvent"].AddRow({
			"Command": RefData(length=len(cmdBytes), magic=b"\x00"*4, value=array.array("B", cmdBytes))
		})
		return cmdRow

	def AddTrackRow(self, eventRow, baseTrackInd=None):
		trackRow = self.Tables["Track"].RowCount
		if baseTrackInd is None:
			self.Tables["Track"].AddRow({
				"EventIndex": eventRow,
				"CommandIndex": 0xFFFF,
				"LocalAisacs": RefData(),
				"GlobalAisacStartIndex": 0xFFFF,
				"GlobalAisacNumRefs": 0,
				"ParameterPallet": 0xFFFF,
				"TargetType": 0,
				"TargetName": RefString(encodingType=self.Tables["Track"].EncodingType),
				"TargetId": 0xFFFFFFFF,
				"TargetAcbName": RefString(encodingType=self.Tables["Track"].EncodingType),
				"Scope": 0,
				"TargetTrackNo": 0xFFFF,
			})
		else:
			self.Tables["Track"].CopyRow(baseTrackInd)
			self.Tables["Track"].SetRowField(trackRow, "EventIndex", eventRow)
			globalAisacStart = self.Tables["Track"].GetRowField(trackRow, "GlobalAisacStartIndex").Value
			globalAisacCount = self.Tables["Track"].GetRowField(trackRow, "GlobalAisacNumRefs").Value
			if globalAisacStart != 0xFFFF and globalAisacCount > 0:
				newStart = self.Tables["GlobalAisacReference"].RowCount
				for globalAisacInd in range(globalAisacCount):
					globalAisacName = self.Tables["GlobalAisacReference"].GetRowField(globalAisacStart+globalAisacInd, "Name").Value.Value
					self.Tables["GlobalAisacReference"].CopyRow(globalAisacStart+globalAisacInd)
				self.Tables["Track"].SetRowField(trackRow, "GlobalAisacStartIndex", newStart)
		return trackRow

	# TODO: this is as dumb as can be for now
	def AddCommandRow(self, name, cmdBytes):
		cmdRow = self.Tables[f"{name}Command"].RowCount
		self.Tables[f"{name}Command"].AddRow({
			"Command": RefData(length=len(cmdBytes), magic=b"\x00"*4, value=array.array("B", cmdBytes))
		})
		return cmdRow

	def AddSequenceRow(self, trackRows, cmdRow=0xFFFF, seqType=None, baseSeqInd=None):
		trackBytes = list()
		trackValues = list()
		for trackRow in trackRows:
			trackBytes.append((trackRow >> 8) & 0xFF)
			trackBytes.append(trackRow & 0xFF)
			trackValues += [0, 100]
		assert len(trackBytes) == len(trackValues) == 2*len(trackRows)
		trackIndex = RefData(length=4, magic=b"\x00"*4, value=array.array("B", trackBytes))
		trackValues = RefData(length=4, magic=b"\x00"*4, value=array.array("B", trackValues))

		seqRow = self.Tables["Sequence"].RowCount
		if baseSeqInd is None:
			self.Tables["Sequence"].AddRow({
				"PlaybackRatio": 100,
				"NumTracks": len(trackRows),
				"TrackIndex": trackIndex,
				"CommandIndex": cmdRow,
				"LocalAisacs": RefData(),
				"GlobalAisacStartIndex": 0xFFFF,
				"GlobalAisacNumRefs": 0,
				"ParameterPallet": 0xFFFF,
				"ActionTrackStartIndex": 0xFFFF,
				"NumActionTracks": 0,
				"TrackValues": RefData() if len(trackRows) <= 1 else trackValues,
				"Type": 0 if seqType is None else seqType,
				"ControlWorkArea1": 1,
				"ControlWorkArea2": 1,
				"InstPluginTrackStartIndex": 0xFFFF, # only in recent versions... older versions will just ignore this
				"NumInstPluginTracks": 0, # (ditto)
			})
		else:
			self.Tables["Sequence"].CopyRow(baseSeqInd)
			self.Tables["Sequence"].SetRowField(seqRow, "NumTracks", len(trackRows))
			self.Tables["Sequence"].SetRowField(seqRow, "TrackIndex", trackIndex)
			self.Tables["Sequence"].SetRowField(seqRow, "TrackValues", RefData() if len(trackRows) <= 1 else trackValues)
			self.Tables["Sequence"].SetRowField(seqRow, "CommandIndex", cmdRow)
			if seqType is not None:
				self.Tables["Sequence"].SetRowField(seqRow, "Type", seqType)
			globalAisacStart = self.Tables["Sequence"].GetRowField(seqRow, "GlobalAisacStartIndex").Value
			globalAisacCount = self.Tables["Sequence"].GetRowField(seqRow, "GlobalAisacNumRefs").Value
			if globalAisacStart != 0xFFFF and globalAisacCount > 0:
				newStart = self.Tables["GlobalAisacReference"].RowCount
				for globalAisacInd in range(globalAisacCount):
					globalAisacName = self.Tables["GlobalAisacReference"].GetRowField(globalAisacStart+globalAisacInd, "Name").Value.Value
					self.Tables["GlobalAisacReference"].CopyRow(globalAisacStart+globalAisacInd)
				self.Tables["Sequence"].SetRowField(seqRow, "GlobalAisacStartIndex", newStart)

		return seqRow

	def AddCueRow(self, length, seqRow, cueId=None, numWaveforms=0):
		if cueId is None:
			for existingId in self.CueId2CueRow:
				if existingId+1 not in self.CueId2CueRow:
					cueId = existingId+1
					break
		assert cueId is not None
		assert cueId not in self.CueId2CueRow

		cueRow = self.Tables["Cue"].RowCount
		self.Tables["Cue"].AddRow({
			"CueId": cueId,
			"ReferenceType": ReferenceType.Sequence.value,
			"ReferenceIndex": seqRow,
			"UserData": RefString(encodingType=self.Tables["Cue"].EncodingType),
			"Worksize": 0,
			"AisacControlMap": RefData(),
			"Length": length,
			"NumAisacControlMaps": 0,
			"HeaderVisibility": 1,
			"NumRelatedWaveforms": numWaveforms, # only in recent versions... older versions will just ignore this
		})
		return cueId, cueRow

	def AddCueNameRow(self, cueName, cueRow):
		cueNameRow = self.Tables["CueName"].RowCount
		self.Tables["CueName"].AddRow({
			"CueName": RefString(encodingType=self.Tables["CueName"].EncodingType, value=cueName),
			"CueIndex": cueRow
		})
		return cueNameRow

	# each sound in newBytesList is put as the single synth in its own track
	# ...so this can do multi-track stuff, but not multi-synth stuff, if that makes sense
	# (obviously it'd be nice to do that but it's more complicated)
	def AddWaveformAndCue(self, streaming, newBytesList, newType, cueName=None, cueId=None, seqCmdBytes=None, seqType=None, baseCueId=None):

		# copy the seq params + as many tracks (+track events) of the base cue as there are tracks for the new one
		# all synths in the copied track are replaced with ones pointing to the current new sound
		# any other command refs are the same, rather than duplicated
		baseSeqInd = None
		baseTrack = list()
		baseTrackSynth = list()
		if baseCueId is not None:
			cueRow = self.CueId2CueRow[baseCueId]
			refType = self.Tables["Cue"].GetRowField(cueRow, "ReferenceType").Value
			refIndex = self.Tables["Cue"].GetRowField(cueRow, "ReferenceIndex").Value
			if ReferenceType(refType) == ReferenceType.Sequence or ReferenceType(refType) == ReferenceType.LinkedSequence:
				baseSeqInd = refIndex
				# for each track in the base seq, get first synth
				# track events are simplified rather than copied
				# if we have more tracks than the original sequence, we reference the 0th
				numTracks = self.Tables["Sequence"].GetRowField(baseSeqInd, "NumTracks").Value
				trackIndex = self.Tables["Sequence"].GetRowField(baseSeqInd, "TrackIndex").Value.Value
				assert len(trackIndex) == 2*numTracks
				for i in range(numTracks):
					baseTrackSynth.append(None)
					trackId = (trackIndex[2*i] << 8) + trackIndex[(2*i)+1]
					baseTrack.append(trackId)
					eventIndex = self.Tables["Track"].GetRowField(trackId, "EventIndex").Value
					cmdBytes = list(self.Tables["TrackEvent"].GetRowField(eventIndex, "Command").Value.Value)
					while cmdBytes and cmdBytes != [0]:
						cmdType = (cmdBytes.pop(0) << 8) + cmdBytes.pop(0)
						paramCount = cmdBytes.pop(0)
						params = [cmdBytes.pop(0) for j in range(paramCount)]
						if CommandType(cmdType) == CommandType.NoteOn:
							refType2, refIndex2 = ParamsToArgs(params, [2, 2])
							if ReferenceType(refType2) == ReferenceType.Synth or ReferenceType(refType2) == ReferenceType.LinkedSynth:
								baseTrackSynth[-1] = refIndex2
								break
						elif CommandType(cmdType) == CommandType.NoteOnWithNo:
							refType2, refIndex2, unk = ParamsToArgs(params, [2, 2, 2])
							if ReferenceType(refType2) == ReferenceType.Synth or ReferenceType(refType2) == ReferenceType.LinkedSynth:
								baseTrackSynth[-1] = refIndex2
								break

		trackRows = list()
		for i in range(len(newBytesList)):
			# new AWB entry
			awbId = self.AddAwbEntry(streaming, newBytesList[i])
			# new Waveform row
			length, waveRow = self.AddWaveformRow(streaming, ExtEncode[newType].value, awbId)
			# new Synth row
			synthRow = self.AddSynthRow(waveRow, baseSynthInd=(baseTrackSynth[i] if i < len(baseTrackSynth) else baseTrackSynth[0] if baseTrackSynth else None))
			# new TrackEvent row
			trackEventRow = self.AddTrackEventRow(synthRow)
			#trackEventRow = self.AddLinkCommandRow(cueId)
			# new Track row
			trackRow = self.AddTrackRow(trackEventRow, baseTrackInd=(baseTrack[i] if i < len(baseTrack) else baseTrack[0] if baseTrack else None))
			trackRows.append(trackRow)

		# new Sequence Command row (because we need to change the CueLimits lol)
		# god, i need a new way to deal with commands, this is untenable
		if seqCmdBytes is None and baseSeqInd is not None:
			baseSeqCmdIndex = self.Tables["Sequence"].GetRowField(baseSeqInd, "CommandIndex").Value
			if baseSeqCmdIndex != 0xFFFF:
				seqCmdBytes = list(self.Tables["SeqCommand"].GetRowField(baseSeqCmdIndex, "Command").Value.Value)
				i = 0
				while i < len(seqCmdBytes)-3:
					cmdType = (seqCmdBytes[i] << 8) + seqCmdBytes[i+1]
					paramCount = seqCmdBytes[i+2]
					params = [seqCmdBytes[i+3+j] for j in range(paramCount)]
					if CommandType(cmdType) == CommandType.CueLimits or CommandType(cmdType) == CommandType.CueLimitsAndMode:
						seqCmdBytes[i+3+2] = (self.Tables["Cue"].RowCount >> 8) & 0xFF
						seqCmdBytes[i+3+3] = self.Tables["Cue"].RowCount & 0xFF
					i += 3 + paramCount
		seqCmdRow = 0xFFFF
		if seqCmdBytes is not None:
			seqCmdRow = self.AddCommandRow("Seq", seqCmdBytes)

		# new Sequence row
		seqRow = self.AddSequenceRow(trackRows, cmdRow=seqCmdRow, seqType=seqType, baseSeqInd=baseSeqInd)
		# new Cue row
		cueId, cueRow = self.AddCueRow(length, seqRow, cueId=cueId, numWaveforms=len(newBytesList))
		# new CueName row
		if cueName is None:
			cueName = f"Cue{cueId}"
		cueNameRow = self.AddCueNameRow(cueName, cueRow)

		return cueId, cueNameRow

	def AddTracksToCue(self, streaming, newBytesList, newType, cueId, seqType=None, baseTrackWithinCue=None):

		cueRow = self.CueId2CueRow[cueId]
		refType = self.Tables["Cue"].GetRowField(cueRow, "ReferenceType").Value
		refIndex = self.Tables["Cue"].GetRowField(cueRow, "ReferenceIndex").Value
		# if this isn't true then idklol
		assert ReferenceType(refType) == ReferenceType.Sequence or ReferenceType(refType) == ReferenceType.LinkedSequence
		seqRow = refIndex
		originalNumTracks = self.Tables["Sequence"].GetRowField(seqRow, "NumTracks").Value
		originalTrackIndex = self.Tables["Sequence"].GetRowField(seqRow, "TrackIndex").Value.Value
		originalTrackValues = self.Tables["Sequence"].GetRowField(seqRow, "TrackValues").Value.Value
		assert len(originalTrackIndex) == 2*originalNumTracks

		baseTrack = None
		baseTrackSynth = None
		if baseTrackWithinCue is not None:
			# for each track in the base seq, get first synth
			# track events are simplified rather than copied
			# if we have more tracks than the original sequence, we reference the 0th
			assert baseTrackWithinCue >= 0 and baseTrackWithinCue < originalNumTracks
			baseTrack = (originalTrackIndex[2*baseTrackWithinCue] << 8) + originalTrackIndex[(2*baseTrackWithinCue)+1]
			eventIndex = self.Tables["Track"].GetRowField(baseTrack, "EventIndex").Value
			cmdBytes = list(self.Tables["TrackEvent"].GetRowField(eventIndex, "Command").Value.Value)
			while cmdBytes and cmdBytes != [0]:
				cmdType = (cmdBytes.pop(0) << 8) + cmdBytes.pop(0)
				paramCount = cmdBytes.pop(0)
				params = [cmdBytes.pop(0) for j in range(paramCount)]
				if CommandType(cmdType) == CommandType.NoteOn:
					refType2, refIndex2 = ParamsToArgs(params, [2, 2])
					if ReferenceType(refType2) == ReferenceType.Synth or ReferenceType(refType2) == ReferenceType.LinkedSynth:
						baseTrackSynth = refIndex2
						break
				elif CommandType(cmdType) == CommandType.NoteOnWithNo:
					refType2, refIndex2, unk = ParamsToArgs(params, [2, 2, 2])
					if ReferenceType(refType2) == ReferenceType.Synth or ReferenceType(refType2) == ReferenceType.LinkedSynth:
						baseTrackSynth = refIndex2
						break

		newTrackBytes = list(originalTrackIndex)
		newTrackWeights = list(originalTrackValues)
		for i in range(len(newBytesList)):
			# new AWB entry
			awbId = self.AddAwbEntry(streaming, newBytesList[i])
			# new Waveform row
			length, waveRow = self.AddWaveformRow(streaming, ExtEncode[newType].value, awbId)
			# new Synth row
			synthRow = self.AddSynthRow(waveRow, baseSynthInd=baseTrackSynth)
			# new TrackEvent row
			trackEventRow = self.AddTrackEventRow(synthRow)
			#trackEventRow = self.AddLinkCommandRow(cueId)
			# new Track row
			trackRow = self.AddTrackRow(trackEventRow, baseTrackInd=baseTrack)
			newTrackBytes.append((trackRow >> 8) & 0xFF)
			newTrackBytes.append(trackRow & 0xFF)
			newTrackWeights += [0, 100]

		newTrackIndex = RefData(length=4, magic=b"\x00"*4, value=array.array("B", newTrackBytes))
		newTrackValues = RefData(length=4, magic=b"\x00"*4, value=array.array("B", newTrackWeights))
		self.Tables["Sequence"].SetRowField(seqRow, "NumTracks", originalNumTracks + len(newBytesList))
		self.Tables["Sequence"].SetRowField(seqRow, "TrackIndex", newTrackIndex)
		self.Tables["Sequence"].SetRowField(seqRow, "TrackValues", newTrackValues)
		if seqType is not None:
			self.Tables["Sequence"].SetRowField(seqRow, "Type", seqType)

		originalWaveformCount = self.Tables["Cue"].GetRowField(cueRow, "NumRelatedWaveforms").Value
		self.Tables["Cue"].SetRowField(cueRow, "NumRelatedWaveforms", originalWaveformCount + len(newBytesList))

	def SetSeqCommandRow(self, cmdRow, cmdBytes):
		self.Tables["SeqCommand"].SetRow(cmdRow, {
			"Command": RefData(length=len(cmdBytes), magic=b"\x00"*4, value=array.array("B", cmdBytes))
		})

	def Extract(self, base_path, keycode=None, outputFormat=None, printing=False, nameByCue=False):
		os.makedirs(base_path, exist_ok=True)
		if nameByCue:
			for cueId in sorted(self.CueId2CueNameRow):
				cueRow = self.CueId2CueRow[cueId]
				cueNameRow = self.CueId2CueNameRow[cueId]
				cueName = self.Tables["CueName"].GetRowField(cueNameRow, "CueName").Value.Value
				if printing:
					print(f"Cue #{cueId}: {cueName}")
				refType = self.Tables["Cue"].GetRowField(cueRow, "ReferenceType").Value
				refIndex = self.Tables["Cue"].GetRowField(cueRow, "ReferenceIndex").Value
				self.RecursivelyGetReferences(refType, refIndex, printing=printing, keycode=keycode, outputFormat=outputFormat, path=f"{base_path}/{cueId}.{cueName}", extracting=True)
				if printing:
					print()
		else:
			for i in range(self.Tables["Waveform"].RowCount):
				streamingEnum = self.Tables["Waveform"].GetRowField(i, "Streaming").Value
				encodeType = self.Tables["Waveform"].GetRowField(i, "EncodeType").Value
				extIndex = self.Tables["Waveform"].GetRowField(i, "ExtensionData").Value
				toStreamOrNotToStream = list()
				if streamingEnum == 0 or streamingEnum == 2:
					toStreamOrNotToStream.append(False)
				if streamingEnum == 1 or streamingEnum == 2:
					toStreamOrNotToStream.append(True)
				for streaming in toStreamOrNotToStream:
					if streaming:
						awb = self.StreamAwbStruct
						if self.SimpleAwbId:
							awbId = self.Tables["Waveform"].GetRowField(i, "Id").Value
						else:
							awbId = self.Tables["Waveform"].GetRowField(i, "StreamAwbId").Value
							if streamingEnum == 1:
								assert self.Tables["Waveform"].GetRowField(i, "MemoryAwbId").Value == 0xFFFF
					else:
						awb = self.MemoryAwbStruct
						if self.SimpleAwbId:
							awbId = self.Tables["Waveform"].GetRowField(i, "Id").Value
						else:
							awbId = self.Tables["Waveform"].GetRowField(i, "MemoryAwbId").Value
							if streamingEnum == 0:
								assert self.Tables["Waveform"].GetRowField(i, "StreamAwbId").Value == 0xFFFF
					audio = None
					if awb is not None and (printing or keycode is not None):
						if EncodeExt[encodeType] == "ADX":
							audio = ADX()
							audio.frombytes(awb.EntryData[awb.IdToInd[awbId]])
						elif EncodeExt[encodeType] == "HCA":
							audio = HCA()
							audio.frombytes(awb.EntryData[awb.IdToInd[awbId]])
					if printing:
						print("Waveform from {} AWB".format("Streaming" if streaming else "Memory"))
						print(" ID: {}".format(awbId))
						print(" Type: {}".format(EncodeExt[encodeType]))
						print(" Channels: {}".format(self.Tables["Waveform"].GetRowField(i, "NumChannels").Value))
						print(" Loop: {}".format(self.Tables["Waveform"].GetRowField(i, "LoopFlag").Value))
						if extIndex != 0xFFFF:
							print("  Loop Start: {}".format(self.Tables["WaveformExtensionData"].GetRowField(extIndex, "LoopStart").Value))
							print("  Loop End: {}".format(self.Tables["WaveformExtensionData"].GetRowField(extIndex, "LoopEnd").Value))
						print(" Sampling Rate: {}".format(self.Tables["Waveform"].GetRowField(i, "SamplingRate").Value))
						print(" Samples: {}".format(self.Tables["Waveform"].GetRowField(i, "NumSamples").Value))
						if audio is not None:
							print(" Audio File:")
							print("  Channels: {}".format(audio.ChannelCount))
							print("  Loops: {}".format(audio.LoopCount))
							if audio.LoopCount:
								print("   Loop Start: {}".format(audio.LoopStartSample))
								print("   Loop End: {}".format(audio.LoopEndSample))
							print("  Sampling Rate: {}".format(audio.SampleRate))
							print("  Samples: {}".format(audio.SampleCount))
					if outputFormat is not None:
						output_ext = outputFormat
					else:
						output_ext = EncodeExt[encodeType]
					filename = "{}/{}-{}.{}".format(base_path, "stream" if streaming else "memory", awbId, output_ext)
					if audio is not None:
						if keycode is not None:
							if EncodeExt[encodeType] == "ADX":
								audio.decrypt(keycode)
							elif EncodeExt[encodeType] == "HCA":
								if awb.Key:
									audio.Crypt(keycode * ((awb.Key << 16) | ((~awb.Key + 2) + 2**16)))
								else:
									audio.Crypt(keycode)
						audio.write_right(filename)
					elif awb is not None:
						with open(filename, "wb") as f:
							f.write(awb.EntryData[awbId])
					else:
						print(f"   Matching AWB not found; skipping extraction for {filename}.")
					if printing:
						print()


def ParamsToArgs(paramBytes, argSizes):
	ret = list()
	assert len(paramBytes) == sum(argSizes)
	for argSize in argSizes:
		ret.append(sum(paramBytes.pop(0) << (i*8) for i in reversed(range(argSize))))
	assert len(ret) == len(argSizes)
	assert not paramBytes
	return ret


class ReferenceType(Enum):
	Null				= 0
	Waveform			= 1
	Synth				= 2
	Sequence			= 3
	Track				= 4
	LinkedCue			= 5
	LinkedSynth			= 6
	LinkedSequence		= 7
	BlockSequence		= 8
	LinkedBlockSequence	= 9


class SequenceType(Enum):
	Polyphonic		= 0
	Sequential		= 1
	Shuffle			= 2
	Random			= 3
	RandomNoRepeat	= 4
	SwitchGameVar	= 5
	ComboSequential	= 6
	SwitchSelector	= 7
	TrackTransition	= 8


class CommandType(Enum):
	Null										= 0
	VolumeOffset								= 1
	VolumeGain_NoUse							= 2
	VolumeOffsetGain							= 3
	VolumeGainRandomRange_NoUse					= 4
	PitchOffset									= 5
	PitchGain									= 6
	PitchOffsetGain								= 7
	PitchOffsetRandomRange						= 8
	PreDelay									= 9
	PreDelayRandomRange							= 10
	Pan3dAngle									= 11
	Pan3dAngleRandomRange						= 12
	Pan3dInteriorDistanceOffset					= 13
	Pan3dInteriorDistanceGain					= 14
	Pan3dInteriorDistanceOffsetGain				= 15
	Pan3dVolume									= 16
	Pan3dLock									= 17
	CenterLfeSendGain_Synth__________			= 18
	CenterLfeSendGain_Waveform__________		= 19
	LRSendGain									= 20
	LsRsSendGain								= 21
	Ex1Ex2SendGain								= 22
	DrySendL									= 23
	DrySendR									= 24
	DrySendCenter								= 25
	DrySendLFE									= 26
	DrySendsL									= 27
	DrySendsR									= 28
	DrySendsEx1									= 29
	DrySendsEx2									= 30
	Biquad										= 31
	Bandpass									= 32
	Mute										= 33
	PriorityModeAndValue						= 34
	PriorityHoldtimeAndDelta					= 35
	VolumeEnvelopeAttackRateAndCurve			= 36
	VolumeEnvelopeDelayAndHold					= 37
	VolumeEnvelopeDecayRateAndCurve				= 38
	VolumeEnvelopeSustainLevel					= 39
	VolumeEnvelopeReleaseRateAndCurve			= 40
	VoiceLimitGroupAndMode						= 41
	GameVariableAndState						= 42
	Probability									= 43
	Bus0Send									= 44
	Bus1Send_Cue								= 45
	Bus1Send_Synth								= 46
	Bus2Send_Cue								= 47
	Bus2Send_Synth								= 48
	Bus3Send_Cue								= 49
	Bus3Send_Synth								= 50
	Bus4Send_Cue								= 51
	Bus4Send_Synth								= 52
	Bus5Send_Cue								= 53
	Bus5Send_Synth								= 54
	Bus6Send_Cue								= 55
	Bus6Send_Synth								= 56
	Bus7Send_Cue								= 57
	Bus7Send_Synth								= 58
	VolumeGainWithRandomRange_NoUse				= 59
	PitchOffsetWithRandomRange					= 60
	Pan3dAngleWithRandomRange					= 61
	Pan3dInteriorDistanceGainRandomRange		= 62
	Pan3dInteriorDistanceGainWithRandomRange	= 63
	BiquadWithRandomRange						= 64
	Category									= 65
	Pos3dVolume									= 66
	Pos3dInsideAndOutsideAngle					= 67
	Pos3dDistanceMin							= 68
	Pos3dDistanceMax							= 69
	PanType										= 70
	PreDelayWithRandomRange						= 71
	CuePriority									= 72
	CueLimits									= 73
	Pos3dDopplerCoefficient						= 74
	GlobalAisacReference						= 75
	MixdownCenterLfeSendGain_Synth_NoUse		= 76
	MixdownCenterLfeSendGain_Track_NoUse		= 77
	Pos3dListnerBaseAisacControlAngle			= 78
	CueLimitsAndMode							= 79
	CuePriorityModeAndValue						= 80
	CuePriorityMode								= 81
	SilentMode									= 82
	MixdownCenterSendGain_Synth					= 83
	MixdownCenterSendGain_Track					= 84
	MixdownLfeSendGain_Synth					= 85
	MixdownLfeSendGain_Track					= 86
	VolumeGain_Res100							= 87
	VolumeRandomization1						= 88
	VolumeRandomization2						= 89
	PlaybackRatio								= 90
	SwitchVariableId							= 91
	SwitchVariableName							= 92
	TrackMonoFlag								= 93
	ComboTimeAndLoopBack						= 94
	DeviceSend0									= 95
	DeviceSend1									= 96
	DeviceSend2									= 97
	BeatInfo									= 98
	Selector									= 99
	TrackSelectorLabel							= 100
	FadeTime4MusicTransition					= 101
	FadeTimeOffset4MusicTransition				= 102
	FadeCurveType4MusicTransition				= 103
	Dummy_2										= 104
	UsePlayerFader								= 105
	Dummy_1										= 106
	FrontBypass									= 107
	Pos3dSourceBaseAisacControlAngle			= 108
	OutputAsrRackId								= 109
	CuePlaybackMode								= 110
	VolumeBus									= 111
	Dummy_4										= 112
	BeatSyncInfos								= 113
	IgnorePlayerParameter						= 114
	TrackBpm4TrackTransition					= 115
	TransitionType4MusicTransition				= 116
	IgnoreLoop									= 117
	MultiplDiscreteAudioChannelsRouting			= 118
	TrackTransitionType4TrackTransition			= 119
	MultiplePlaybackProhibitionTime				= 120
	MaximumPitch								= 121
	FixedAngleZeroWithinMinDistance				= 122
	RendererType								= 123
	StopAtLoopEnd								= 124
	Unk127										= 127
	Unk128										= 128
	#####
	Unk146										= 146
	Unk147										= 147
	#####
	Unk997										= 997
	SequenceStartRandom							= 998
	SequenceStart								= 999
	NoteOff										= 1000
	NoteOnWithOff								= 1001
	#####
	Unk1199										= 1199
	#####
	LoopEnd										= 1200
	LoopStart									= 1201
	#####
	SequenceCallback							= 1250
	SequenceCallbackWithId						= 1251
	SequenceCallbackWithString					= 1252
	SequenceCallbackWithIdAndString				= 1253
	#####
	AutoRepeatIntervalWithNum					= 1989
	AutoRepeatInterval							= 1990
	TimingRandom								= 1991
	#####
	NoteOn										= 2000
	Delay										= 2001
	SetSynthOrWaveform							= 2002
	NoteOnWithNo								= 2003
	Unk2004										= 2004
	Unk2005										= 2005
	#####
	SequenceEndForReact							= 3999
	SequenceEnd									= 4000
	#####
	BlockEnd									= 4050
	TransitionTrack								= 4051
	FirstAfterTransitionTrack					= 4052
	#####
	StartAction									= 7100
	StopAction									= 7101
	MuteTrackAction								= 7102
	ChangePlaybackParameter						= 7103
	SetSelectorLabel							= 7104
	ChangePlaybackParameterFloatRatio			= 7105
	FaderSetting								= 7106
	ChangePlaybackParameterFloatRatioWithCurve	= 7107
	#####
	StopHaptic									= 8000
	StartHapticUhlEffect						= 8001
	StartHapticEffectWithPriority				= 8002
	StartTouchSenseEffect						= 8003
	StartTouchSenseEffectWithPriority			= 8004


EncodeExt = {
	0:	"ADX",
	1:	"AHX",
	2:	"HCA",
	3:	"ADX",
	4:	"WIIADPCM",
	5:	"DSADPCM",
	6:	"HCAMX",
	7:	"VAG",
	8:	"AT3",
	9:	"BCWAV",
	10:	"VAG",
	11:	"AT9",
	12:	"XMA",
	13:	"DSP",
	18:	"AT9",
	19:	"M4A",
	24:	"OGG", # :shrug:
}


class ExtEncode(Enum):
	ADX			= 0
	AHX			= 1
	HCA			= 2
	ADX2		= 3
	WIIADPCM	= 4
	DSADPCM		= 5
	HCAMX		= 6
	VAG			= 7
	AT3			= 8
	BCWAV		= 9
	VAG2		= 10
	AT9			= 11
	XMA			= 12
	DSP			= 13
	AT92		= 18
	M4A			= 19
	OGG			= 24
