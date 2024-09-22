import os

import xml.etree.ElementTree as ET

from enum import Enum

from exbip.Serializable import Serializable
from exbip.BinaryTargets.Interface.Base import EndiannessManager


class UTF(Serializable):

	def __init__(self, encodingType=None, tableName=None, columnCount=None, fields=None):
		self.Magic = "@UTF"
		self.TableSize = 0
		self.I_00 = 0
		self.EncodingType = encodingType
		self.RowOffset = 0
		self.StringsOffset = 0
		self.TableName = tableName
		self.DataOffset = 0
		self.ColumnCount = columnCount
		self.RowLength = 0
		self.RowCount = 0

		self.Fields = fields
		if self.Fields is None:
			self.FieldNames = dict()
		else:
			self.FieldNames = {self.Fields[i].Name.Value:i for i in range(len(self.Fields))}

		self.Rows = list()

	def to_xml(self, parent=None):

		if parent is None:
			root = ET.Element("UTF")
		else:
			root = ET.SubElement(parent, "UTF")

		fields = ET.SubElement(root, "Fields")
		for i in range(self.ColumnCount):
			fieldType = TypeFlag(self.Fields[i].TypeFlag)
			if self.Fields[i].NameFlag:
				field = ET.SubElement(fields, self.Fields[i].Name.Value, type=fieldType.name)
			else:
				field = ET.SubElement(fields, str(i), type=fieldType.name)
			if self.Fields[i].DefaultValueFlag:
				fieldVal = self.Fields[i].DefaultValue.Value
				if fieldType == TypeFlag.String:
					field.text = fieldVal.Value
				elif fieldType == TypeFlag.Data:
					if fieldVal.Magic == b"@UTF":
						fieldVal.Value.to_xml(parent=field)
					elif fieldVal.Magic == b"AFS2":
						for k in range(fieldVal.Value.EntryCount):
							if k < fieldVal.Value.EntryCount-1:
								size = fieldVal.Value.EntryPositions[k+1].Value - fieldVal.Value.EntryPositions[k].Value
							else:
								size = fieldVal.Value.EndPosition.Value - fieldVal.Value.EntryPositions[k].Value
							ET.SubElement(field, "Entry", ind=str(k), idx=str(fieldVal.Value.EntryIds[k].Value), size=str(size))
					elif fieldVal.Value is not None:
						field.text = " ".join(f"{b:02X}" for b in fieldVal.Value)
				elif fieldType == TypeFlag.GUID:
					field.text = " ".join(f"{b:02X}" for b in fieldVal.Value)
				else:
					field.text = str(fieldVal)

		rows = ET.SubElement(root, "Rows")
		for i in range(self.RowCount):
			row = ET.SubElement(rows, self.TableName.Value+"Row", ind=str(i))
			for j in range(self.ColumnCount):
				if self.Fields[j].RowStorageFlag:
					fieldName = self.Fields[j].Name.Value
					fieldType = TypeFlag(self.Fields[j].TypeFlag)
					fieldVal = self.GetRowField(i, fieldName).Value
					if fieldVal is not None:
						if fieldType == TypeFlag.String:
							if fieldVal.Value:
								col = ET.SubElement(row, fieldName if self.Fields[j].NameFlag else str(j))
								col.text = fieldVal.Value
						elif fieldType == TypeFlag.Data:
							if fieldVal.Magic == b"@UTF":
								col = ET.SubElement(row, fieldName, dataType="UTF")
								fieldVal.Value.to_xml(parent=col)
							elif fieldVal.Magic == b"AFS2":
								col = ET.SubElement(row, fieldName, dataType="AWB")
								for k in range(fieldVal.Value.EntryCount):
									if k < fieldVal.Value.EntryCount-1:
										size = fieldVal.Value.EntryPositions[k+1].Value - fieldVal.Value.EntryPositions[k].Value
									else:
										size = fieldVal.Value.EndPosition.Value - fieldVal.Value.EntryPositions[k].Value
									ET.SubElement(col, "Entry", ind=str(k), idx=str(fieldVal.Value.EntryIds[k].Value), size=str(size))
							elif fieldVal.Magic is not None:
								col = ET.SubElement(row, fieldName, dataType="HEX")
								col.text = " ".join(f"{b:02X}" for b in fieldVal.Value)
						elif fieldType == TypeFlag.GUID:
							if fieldVal.Value:
								col = ET.SubElement(row, fieldName)
								col.text = " ".join(f"{b:02X}" for b in fieldVal.Value)
						else:
							col = ET.SubElement(row, fieldName)
							col.text = str(fieldVal)

		return root

	def update_offsets(self):
		self.tobytes()

	def write_right(self, path):
		self.update_offsets()
		self.write(path)

	def __rw_hook__(self, rw):

		with EndiannessManager(rw, ">"):

			self.Magic = rw.rw_string(self.Magic, 4, encoding="ascii")
			if rw.is_parselike: # writer
				self.Magic = self.Magic.decode()
			assert self.Magic == "@UTF"

			self.TableSize = rw.rw_uint32(self.TableSize)
			self.I_00 = rw.rw_uint8(self.I_00)
			assert self.I_00 == 0

			self.EncodingType = rw.rw_uint8(self.EncodingType)
			self.RowOffset = rw.rw_uint16(self.RowOffset)
			self.StringsOffset = rw.rw_uint32(self.StringsOffset)
			self.DataOffset = rw.rw_uint32(self.DataOffset)
			self.TableName = rw.rw_obj(self.TableName, RefString, self.EncodingType)


			if rw.is_parselike:
				self.ColumnCount = len(self.Fields)
			self.ColumnCount = rw.rw_uint16(self.ColumnCount)
			self.RowLength = rw.rw_uint16(self.RowLength)
			if rw.is_parselike:
				self.RowCount = len(self.Rows)
			self.RowCount = rw.rw_uint32(self.RowCount)

			self.Fields = rw.rw_objs(self.Fields, Field, self.ColumnCount, self.EncodingType)

			##########
			## ROWS ##
			##########

			if rw.is_parselike:
				self.RowOffset = rw.tell() - 8
			assert rw.tell() == self.RowOffset+8
			for i in range(self.RowCount):
				rowstart = rw.tell()
				if rw.is_constructlike: # reader
					self.Rows.append(list())
				for j in range(self.ColumnCount):
					if rw.is_constructlike: # reader
						self.Rows[i].append(None)
					if self.Fields[j].RowStorageFlag:
						self.Rows[i][j] = rw.rw_obj(self.Rows[i][j], CriValue, self.Fields[j].TypeFlag, self.EncodingType)
				if i == 0 and rw.is_parselike:
			 		self.RowLength = rw.tell() - rowstart
				#assert rw.tell() - rowstart == self.RowLength

			#############
			## STRINGS ##
			#############

			if rw.is_parselike:
				self.StringsOffset = rw.tell() - 8
			assert rw.tell() == self.StringsOffset+8

			if rw.is_parselike:
				self.TableName.Offset = rw.tell() - (self.StringsOffset+8)
			assert rw.tell() == self.StringsOffset+8 + self.TableName.Offset
			self.TableName.RwValue(rw)

			for i in range(self.ColumnCount):
				if self.Fields[i].NameFlag:
					if rw.is_parselike:
						self.Fields[i].Name.Offset = rw.tell() - (self.StringsOffset+8)
					assert rw.tell() == self.StringsOffset+8 + self.Fields[i].Name.Offset
					self.Fields[i].Name.RwValue(rw)
					self.FieldNames[self.Fields[i].Name.Value] = i
				if self.Fields[i].DefaultValueFlag:
					if TypeFlag(self.Fields[i].DefaultValue.TypeFlag) == TypeFlag.String:
						if rw.is_parselike:
							self.Fields[i].DefaultValue.Value.Offset = rw.tell() - (self.StringsOffset+8)
						assert rw.tell() == self.StringsOffset+8 + self.Fields[i].DefaultValue.Value.Offset
						self.Fields[i].DefaultValue.Value.RwValue(rw)

			for i in range(self.RowCount):
				for j in range(self.ColumnCount):
					if self.Fields[j].RowStorageFlag and TypeFlag(self.Fields[j].TypeFlag) == TypeFlag.String:
						if rw.is_parselike:
							self.Rows[i][j].Value.Offset = rw.tell() - (self.StringsOffset+8)
						assert rw.tell() == self.StringsOffset+8 + self.Rows[i][j].Value.Offset
						self.Rows[i][j].Value.RwValue(rw)

			##########
			## DATA ##
			##########

			if rw.is_constructlike:
				assert rw.tell() <= self.DataOffset+8
				stringsPadSize = self.DataOffset+8 - rw.tell()
				stringsPad = None
				stringsPad = rw.rw_bytestring(stringsPad, stringsPadSize)
				assert all(c == 0 for c in stringsPad)
			elif rw.is_parselike:
				self.DataOffset = rw.tell() - 8

			assert rw.tell() == self.DataOffset+8

			# default values
			for i in range(self.ColumnCount):
				if self.Fields[i].DefaultValueFlag and TypeFlag(self.Fields[i].DefaultValue.TypeFlag) == TypeFlag.Data and self.Fields[i].DefaultValue.Value.Length:
					if rw.is_parselike:
						self.Fields[i].DefaultValue.Value.Offset = rw.tell() - (self.DataOffset+8)
					assert rw.tell() == self.DataOffset+8 + self.Fields[i].DefaultValue.Value.Offset
					self.Fields[i].DefaultValue.Value.RwValue(rw)
					assert rw.tell() == self.DataOffset+8 + self.Fields[i].DefaultValue.Value.Offset + self.Fields[i].DefaultValue.Value.Length

			# row storage values
			for i in range(self.RowCount):
				for j in range(self.ColumnCount):
					if self.Fields[j].RowStorageFlag and TypeFlag(self.Fields[j].TypeFlag) == TypeFlag.Data and self.Rows[i][j].Value.Length:
						if rw.is_parselike:
							self.Rows[i][j].Value.Offset = rw.tell() - (self.DataOffset+8)
						assert rw.tell() <= self.DataOffset+8 + self.Rows[i][j].Value.Offset
						if rw.is_constructlike:
							dataPadSize = self.DataOffset+8+self.Rows[i][j].Value.Offset - rw.tell()
							dataPad = None
							dataPad = rw.rw_bytestring(dataPad, dataPadSize)
							assert all(c == 0 for c in dataPad)
						elif rw.is_parselike:
							self.Rows[i][j].Value.Offset = rw.tell() - (self.DataOffset+8)
						assert rw.tell() == self.DataOffset+8 + self.Rows[i][j].Value.Offset
						self.Rows[i][j].Value.RwValue(rw)
						if rw.is_parselike:
							self.Rows[i][j].Value.Length = rw.tell() - (self.DataOffset+8 + self.Rows[i][j].Value.Offset)
						assert rw.tell() == self.DataOffset+8 + self.Rows[i][j].Value.Offset + self.Rows[i][j].Value.Length

			endPadSize = 4 - ((rw.tell() % 4) or 4)
			endPadding = None
			if rw.is_parselike and endPadSize:
				endPadding = b"\x00"*endPadSize

			if endPadSize:
				endPadding = rw.rw_bytestring(endPadding, endPadSize)
				assert len(endPadding) == endPadSize
				assert all(c == 0 for c in endPadding)

			if rw.is_parselike:
				self.TableSize = rw.tell() - 8

	def GetRowField(self, rowInd, fieldName):
		fieldInd = self.FieldNames[fieldName]
		if self.Fields[fieldInd].RowStorageFlag:
			return self.Rows[rowInd][fieldInd]
		if self.Fields[fieldInd].DefaultValueFlag:
			return self.Fields[fieldInd].DefaultValue
		return None

	def SetRowField(self, rowInd, fieldName, newValue, overwriteDefaultValue=True):
		fieldInd = self.FieldNames[fieldName]
		if self.Fields[fieldInd].DefaultValueFlag and newValue != self.Fields[fieldInd].DefaultValue:
			assert not self.Fields[fieldInd].RowStorageFlag
			self.Fields[fieldInd].RowStorageFlag = 1
			self.Fields[fieldInd].DefaultValueFlag = 0
			for rowInd2 in range(self.RowCount):
				if rowInd2 != rowInd:
					self.Rows[rowInd2][fieldInd] = CriValue(
						typeFlag=self.Fields[fieldInd].TypeFlag,
						value=self.Fields[fieldInd].DefaultValue.Value,
					)
		if self.Fields[fieldInd].RowStorageFlag:
			self.Rows[rowInd][fieldInd] = CriValue(
				typeFlag=self.Fields[fieldInd].TypeFlag,
				value=newValue,
			)

	def AddRow(self, rowFields):
		row = list()
		for i in range(self.ColumnCount):
			row.append(CriValue(
				typeFlag=self.Fields[i].TypeFlag,
				value=rowFields[self.Fields[i].Name.Value],
			))
		self.Rows.append(row)
		self.RowCount += 1

	def SetRow(self, rowInd, rowFields):
		for i in range(self.ColumnCount):
			self.Rows[rowInd][i] = CriValue(
				typeFlag=self.Fields[i].TypeFlag,
				value=rowFields[self.Fields[i].Name.Value],
			)


class Field(Serializable):

	def __init__(self, typeFlag=0, nameFlag=1, defaultValueFlag=0, rowStorageFlag=1, name=None, defaultValue=None):
		self.BitFlag = None
		self.TypeFlag = typeFlag
		self.StorageFlag = None

		self.NameFlag = nameFlag
		self.DefaultValueFlag = defaultValueFlag
		self.RowStorageFlag = rowStorageFlag

		self.Name = name
		self.DefaultValue = defaultValue

	def __rw_hook__(self, rw, encodingType):
		if rw.is_parselike: # write
			self.StorageFlag = (self.NameFlag & 0x1) + ((self.DefaultValueFlag & 0x1) << 1) + ((self.RowStorageFlag & 0x1) << 2)
			self.BitFlag = (self.TypeFlag & 0xF) + ((self.StorageFlag & 0xF) << 4)

		self.BitFlag = rw.rw_uint8(self.BitFlag)

		if rw.is_constructlike: # read
			self.TypeFlag = self.BitFlag & 0xF
			self.StorageFlag = (self.BitFlag >> 4) & 0xF
			###
			self.NameFlag = self.StorageFlag & 0x1
			self.DefaultValueFlag = (self.StorageFlag >> 1) & 0x1
			self.RowStorageFlag = (self.StorageFlag >> 2) & 0x1

		if self.NameFlag:
			self.Name = rw.rw_obj(self.Name, RefString, encodingType)
		if self.DefaultValueFlag:
			self.DefaultValue = rw.rw_obj(self.DefaultValue, CriValue, self.TypeFlag, encodingType)


class RefString(Serializable):

	def __init__(self, encodingType=0, offset=0, value=""):
		self.EncodingType = encodingType
		self.Offset = offset
		self.Value = value

	def __rw_hook__(self, rw, encodingType):
		self.EncodingType = encodingType
		self.Offset = rw.rw_uint32(self.Offset)

	def RwValue(self, rw):
		if EncodingType(self.EncodingType) == EncodingType.Utf8:
			self.Value = rw.rw_cstring(self.Value, encoding="utf-8")
		elif EncodingType(self.EncodingType) == EncodingType.ShiftJis:
			self.Value = rw.rw_cstring(self.Value, encoding="shift-jis")


class CriValue(Serializable):

	def __init__(self, typeFlag=None, value=None):
		self.TypeFlag = typeFlag
		self.Value = value

	def __rw_hook__(self, rw, typeFlag, encodingType):
		self.TypeFlag = typeFlag
		if TypeFlag(typeFlag) == TypeFlag.UInt8:
			self.Value = rw.rw_uint8(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.Int8:
			self.Value = rw.rw_int8(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.UInt16:
			self.Value = rw.rw_uint16(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.Int16:
			self.Value = rw.rw_int16(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.UInt32:
			self.Value = rw.rw_uint32(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.Int32:
			self.Value = rw.rw_int32(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.UInt64:
			self.Value = rw.rw_uint64(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.Int64:
			self.Value = rw.rw_int64(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.Single:
			self.Value = rw.rw_float32(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.Double:
			self.Value = rw.rw_float64(self.Value)
		elif TypeFlag(typeFlag) == TypeFlag.String:
			self.Value = rw.rw_obj(self.Value, RefString, encodingType)
		elif TypeFlag(typeFlag) == TypeFlag.Data:
			self.Value = rw.rw_obj(self.Value, RefData)
		elif TypeFlag(typeFlag) == TypeFlag.GUID:
			self.Value = rw.rw_uint8s(self.Value, 16)


class RefData(Serializable):

	def __init__(self, offset=0, length=0, magic=None, value=None):
		self.Offset = offset
		self.Length = length
		self.Magic = magic
		self.Value = value

	def __rw_hook__(self, rw):
		self.Offset = rw.rw_uint32(self.Offset)
		self.Length = rw.rw_uint32(self.Length)

	def RwValue(self, rw):
		pos = rw.tell()
		if self.Length:
			if rw.is_constructlike: # reader
				self.Magic = rw.peek_bytestream(4)
			with rw.relative_origin():
				if self.Magic == b"@UTF":
					self.Value = rw.rw_obj(self.Value, UTF)
				elif self.Magic == b"AFS2":
					self.Value = rw.rw_obj(self.Value, AFS2)
				else:
					self.Value = rw.rw_uint8s(self.Value, self.Length)
		if rw.is_constructlike:
			assert rw.tell() <= pos + self.Length
			padSize = pos + self.Length - rw.tell()
			pad = None
			pad = rw.rw_bytestring(pad, padSize)
			assert all(c == 0 for c in pad)
		elif rw.is_parselike:
			self.Length = rw.tell() - pos
		assert rw.tell() == pos + self.Length
	

class AFS2(Serializable):

	def __init__(self):
		self.Magic = None

		self.Type = None
		self.PositionFieldLength = None
		self.IdFieldLength = None
		self.Padding = None

		self.EntryCount = None
		self.Align = None
		self.Key = None

		self.EntryIds = None
		self.EntryPositions = None

		self.EndPosition = None

		self.EntryPads = None
		self.EntryData = None

		self.IdToInd = dict()

	def update_offsets(self):
		self.tobytes()

	def write_right(self, path):
		self.update_offsets()
		self.write(path)

	def check_equal(self, afs2):
		assert isinstance(afs2, AFS2)
		assert self.Magic == afs2.Magic
		assert self.Type == afs2.Type
		assert self.PositionFieldLength == afs2.PositionFieldLength
		assert self.IdFieldLength == afs2.IdFieldLength
		assert self.Padding == afs2.Padding
		assert self.EntryCount == afs2.EntryCount
		assert self.Align == afs2.Align
		assert self.Key == afs2.Key
		assert all(self.EntryIds[i].Value == afs2.EntryIds[i].Value for i in range(self.EntryCount))
		assert all(self.EntryPositions[i].Value == afs2.EntryPositions[i].Value for i in range(self.EntryCount))
		assert self.EndPosition.Value == afs2.EndPosition.Value

	def set_equal(self, afs2):
		self.Magic = afs2.Magic
		self.Type = afs2.Type
		self.PositionFieldLength = afs2.PositionFieldLength
		self.IdFieldLength = afs2.IdFieldLength
		self.Padding = afs2.Padding
		self.EntryCount = afs2.EntryCount
		self.Align = afs2.Align
		self.Key = afs2.Key
		self.EntryIds = list()
		self.EntryPositions = list()
		self.IdToInd = dict()

		for i in range(self.EntryCount):

			entryId = AfsValue()
			entryId.FieldLength = self.IdFieldLength
			entryId.Value = afs2.EntryIds[i].Value
			self.EntryIds.append(entryId)
			self.IdToInd[entryId.Value] = i

			entryPosition = AfsValue()
			entryPosition.FieldLength = self.PositionFieldLength
			entryPosition.Value = afs2.EntryPositions[i].Value
			self.EntryPositions.append(entryPosition)

		self.EndPosition.Value = afs2.EndPosition.Value
		self.check_equal(afs2)

	def __rw_hook__(self, rw):

		with EndiannessManager(rw, "<"):

			start = rw.tell()

			self.Magic = rw.rw_string(self.Magic, 4, encoding="ascii")
			if rw.is_parselike: # writer
				self.Magic = self.Magic.decode()
			assert self.Magic == "AFS2"

			self.Type = rw.rw_uint8(self.Type)
			self.PositionFieldLength = rw.rw_uint8(self.PositionFieldLength)
			self.IdFieldLength = rw.rw_uint8(self.IdFieldLength)
			self.Padding = rw.rw_uint8(self.Padding)

			self.EntryCount = rw.rw_uint32(self.EntryCount)
			self.Align = rw.rw_uint16(self.Align)
			self.Key = rw.rw_uint16(self.Key)
			assert self.Align == 32

			self.EntryIds = rw.rw_objs(self.EntryIds, AfsValue, self.EntryCount, self.IdFieldLength)
			self.EntryPositions = rw.rw_objs(self.EntryPositions, AfsValue, self.EntryCount, self.PositionFieldLength)

			self.EndPosition = rw.rw_obj(self.EndPosition, AfsValue, self.PositionFieldLength)

			if rw.is_constructlike:
				assert rw.tell() == self.EntryPositions[0].Value

			for i in range(self.EntryCount):
				self.IdToInd[self.EntryIds[i].Value] = i

			if rw.is_constructlike:
				checkpoint = rw.tell()
				rw.seek(self.EndPosition.Value-1, 0)
				notHeaderOnly = rw.peek_bytestream(1)
				rw.seek(checkpoint, 0)
			else:
				notHeaderOnly = (self.EntryData is not None)
			if notHeaderOnly:
				self.get_entries(rw)

	def get_entries(self, rw):

		if rw.is_constructlike: # reader
			self.EntryPads = list()
			self.EntryData = list()

		for i in range(self.EntryCount):

			if rw.is_constructlike: # reader
				self.EntryPads.append(None)
				self.EntryData.append(None)

			if rw.is_parselike:
				self.EntryPositions[i].Value = rw.tell()
			entryPosition = self.EntryPositions[i].Value
			assert rw.tell() == entryPosition

			if rw.is_parselike:
				if entryPosition % self.Align:
					self.EntryPads[i] = b"\x00"*(self.Align - (entryPosition % self.Align))
				else:
					self.EntryPads[i] = None

			if entryPosition % self.Align:
				self.EntryPads[i] = rw.rw_bytestring(self.EntryPads[i], (self.Align - (entryPosition % self.Align)))
				assert len(self.EntryPads[i]) == (self.Align - (entryPosition % self.Align))
				assert all(c == 0 for c in self.EntryPads[i])
				entryPosition += (self.Align - (entryPosition % self.Align))

			if rw.is_parselike:
				if i < self.EntryCount-1:
					self.EntryPositions[i+1].Value = entryPosition + len(self.EntryData[i])
				else:
					self.EndPosition.Value = entryPosition + len(self.EntryData[i])

			if i < self.EntryCount-1:
				nextEntryPosition = self.EntryPositions[i+1].Value
			else:
				nextEntryPosition = self.EndPosition.Value

			self.EntryData[i] = rw.rw_bytestring(self.EntryData[i], nextEntryPosition-entryPosition)

			assert rw.tell() == nextEntryPosition
			assert nextEntryPosition-entryPosition == len(self.EntryData[i])


class AfsValue(Serializable):

	def __init__(self):
		self.FieldLength = None
		self.Value = None

	def __rw_hook__(self, rw, fieldLength):
		self.FieldLength = fieldLength
		if fieldLength == 1:
			self.Value = rw.rw_uint8(self.Value)
		elif fieldLength == 2:
			self.Value = rw.rw_uint16(self.Value)
		elif fieldLength == 4:
			self.Value = rw.rw_uint32(self.Value)
		elif fieldLength == 8:
			self.Value = rw.rw_uint64(self.Value)


class EncodingType(Enum):
	ShiftJis	= 0
	Utf8		= 1


class TypeFlag(Enum):
	UInt8		= 0
	Int8		= 1
	UInt16		= 2
	Int16		= 3
	UInt32		= 4
	Int32		= 5
	UInt64		= 6
	Int64		= 7
	Single		= 8
	Double		= 9
	String		= 10
	Data		= 11
	GUID		= 12


if __name__ == "__main__":
	main()
