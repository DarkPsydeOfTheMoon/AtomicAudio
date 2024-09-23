import argparse
import os

import xml.etree.ElementTree as ET

from pathlib import Path

from ACB import ACB, ExtEncode
from ADX import ADX
from HCA import HCA
from UTFAFS import UTF

def main():

	parser = argparse.ArgumentParser(prog="AtomicAudioTool", description="Basic editing utility for Cri ACB project files.")
	subparsers = parser.add_subparsers(dest="action", help="Specify whether you want to do print_info, to_xml, extract_audio, replace_waveform, or add_simple_cue.")

	info_parser = subparsers.add_parser("print_info", help="Print detailed information about the cues inside the ACB.")
	info_parser.add_argument("--input-acb-path", required=True, help="Path to ACB file to print.")
	info_parser.add_argument("--input-awb-path", required=False, help="Path to streaming AWB file to print.")

	xml_parser = subparsers.add_parser("to_xml", help="Deserialize an ACB or ACF as XML.")
	xml_parser.add_argument("--input-utf", required=True, help="Path to ACB or ACF file to deserialize.")
	xml_parser.add_argument("--output-xml", required=False, help="Path to save output XML to. If not provided, will just print the XML to the console.")

	extract_parser = subparsers.add_parser("extract_audio", help="Extract (and possibly decrypt) the audio files inside the ACB and AWB(s) into a directory.")
	extract_parser.add_argument("--input-acb-path", required=True, help="Path to ACB file to extract from.")
	extract_parser.add_argument("--input-awb-path", required=False, help="Path to streaming AWB file to extract from.")
	extract_parser.add_argument("--output-directory", required=False, help="Optional output directory for extracted audio, which will be created if it doesn't already exist. If not provided, will create a directory of the same base path + name as the input ACB.")
	extract_parser.add_argument("--name-by-cue", action=argparse.BooleanOptionalAction, help="If provided, will name extracted audio files by cue and track numbers. Otherwise, will name by AWB IDs.")
	extract_parser.add_argument("--key-code", type=int, required=False, help="If provided, will decrypt extracted ADX files.")
	#extract_parser.add_argument("--output-format", required=False, help="If provided, will try to convert the extracted files to the specified audio format.")
	extract_parser.add_argument("--print-info", action=argparse.BooleanOptionalAction, help="If provided, will print ACB info alongside extraction")

	wave_parser = subparsers.add_parser("replace_waveform", help="Use the provided audio file to replace the waveform at the given AWB ID. Currently only supports ADX.")
	wave_parser.add_argument("--awb-id", type=int, required=True, help="AWB ID of waveform to be replaced.")
	wave_parser.add_argument("--new-audio-type", required=False, default="ADX", help="Name of the audio format of the new file. Accepted values: {}".format(", ".join(x.name for x in ExtEncode)))
	wave_parser.add_argument("--new-audio-path", required=True, help="Path to audio file that will replace existing one.")
	#wave_parser.add_argument("--convert-input", action=argparse.BooleanOptionalAction, help="If provided, will convert input audio file to ADX.")
	wave_parser.add_argument("--key-code", type=int, required=False, help="If provided, will encrypt input ADX file.") # (whether ADX at source or converted via --convert-input).")
	wave_parser.add_argument("--input-acb-path", required=True, help="Path to ACB file to modify.")
	wave_parser.add_argument("--input-awb-path", required=False, help="Path to streaming AWB file to modify. If provided, will try to add audio to the external (streaming) AWB. Otherwise, will try to add to the in-memory AWB inside the ACB.")
	wave_parser.add_argument("--output-acb-path", required=False, help="Optional path to modified ACB file. If omitted, will modify input ACB in place.")
	wave_parser.add_argument("--output-awb-path", required=False, help="Optional path to modified streaming AWB file. If omitted, will modify input AWB in place.")

	cue_parser = subparsers.add_parser("add_simple_cue", help="Use the provided audio file to create a new AWB entry and a simple cue that points to it.")
	cue_parser.add_argument("--cue-name", required=False, help="Name of cue to be added. If omitted, will default to \"Cue{cue_id}\".")
	cue_parser.add_argument("--cue-id", type=int, required=False, help="Cue ID of new cue. If omitted, will pick next available ID.")
	cue_parser.add_argument("--new-audio-type", required=False, default="ADX", help="Name of the audio format of the new file. Accepted values: {}".format(", ".join(x.name for x in ExtEncode)))
	cue_parser.add_argument("--new-audio-path", required=True, help="Path to audio file that will replace existing one.")
	#cue_parser.add_argument("--convert-input", action=argparse.BooleanOptionalAction, help="If provided, will convert input audio file to ADX.")
	cue_parser.add_argument("--key-code", type=int, required=False, help="If provided, will encrypt input ADX file.") # (whether ADX at source or converted via --convert-input).")
	cue_parser.add_argument("--input-acb-path", required=True, help="Path to ACB file to modify.")
	cue_parser.add_argument("--input-awb-path", required=False, help="Path to streaming AWB file to modify. If provided, will try to add audio to the external (streaming) AWB. Otherwise, will try to add to the in-memory AWB inside the ACB.")
	cue_parser.add_argument("--output-acb-path", required=False, help="Optional path to modified ACB file. If omitted, will modify input ACB in place.")
	cue_parser.add_argument("--output-awb-path", required=False, help="Optional path to modified streaming AWB file. If omitted, will modify input AWB in place.")

	args = parser.parse_args()
	if args.action == "print_info":
		acb = ACB(args.input_acb_path, awbPath=args.input_awb_path)
		acb.PrettyPrint()
	elif args.action == "to_xml":
		utf = UTF()
		utf.read(args.input_utf)
		root = utf.to_xml()
		ET.indent(root, space='  ', level=0)
		if args.output_xml:
			with open(args.output_xml, "w") as f:
				print(ET.tostring(root).decode("utf-8"), file=f)
		else:
			print(ET.tostring(root).decode("utf-8"))
	elif args.action == "extract_audio":
		acb = ACB(args.input_acb_path, awbPath=args.input_awb_path)
		if args.output_directory is None:
			args.output_directory = str(Path(args.input_acb_path).with_suffix(""))
		os.makedirs(args.output_directory, exist_ok=True)
		acb.Extract(args.output_directory, keycode=args.key_code, printing=args.print_info, nameByCue=args.name_by_cue)
	elif args.action == "replace_waveform" or args.action == "add_simple_cue":
		acb = ACB(args.input_acb_path, awbPath=args.input_awb_path)

		if args.output_acb_path is None:
			args.output_acb_path = args.input_acb_path
		if args.output_awb_path is None:
			args.output_awb_path = args.input_awb_path

		streaming = args.input_awb_path is not None
		awb = acb.StreamAwbStruct if streaming else acb.MemoryAwbStruct

		with open(args.new_audio_path, "rb") as f:
			inputBytes = f.read()

		if args.key_code is not None:
			if args.new_audio_type == "ADX":
				adx = ADX()
				adx.frombytes(inputBytes)
				adx.encrypt(args.key_code, codingType=9)
				inputBytes = adx.tobytes()
			elif args.new_audio_type == "HCA":
				hca = HCA()
				hca.frombytes(inputBytes)
				hca.Crypt(args.key_code * ((awb.Key << 16) | ((~awb.Key + 2) + 2**16)))
				inputBytes = hca.tobytes()

		if args.action == "replace_waveform":
			acb.ReplaceWaveform(args.awb_id, streaming, inputBytes, replacementType=ExtEncode[args.new_audio_type].value)
		elif args.action == "add_simple_cue":
			acb.AddWaveformAndCue(streaming, inputBytes, args.new_audio_type, args.cue_name, args.cue_id)

		acb.AcbStruct.write_right(args.output_acb_path)
		if args.output_awb_path is not None:
			acb.StreamAwbStruct.write_right(args.output_awb_path)
	else:
		raise ValueError("Command not recognized. Must be replace_waveform or add_simple_cue.")


if __name__ == "__main__":
	main()
