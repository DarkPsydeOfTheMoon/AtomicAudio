# Atomic Audio Tool

*A WIP Python tool for parsing, editing, and creating CRI audio formats.*

## Dependencies

You should only need a relatively recent version of Python 3. There are currently no additional packages required.

## Getting Started

The tool is run through `AtomicAudioTool.py` with several available commands.

For more details, run `python AtomicAudioTool.py --help`.

### `print_info`

Print the detailed structure of each cue in a provided ACB, with the option of providing a streaming AWB for additional details. For example:

```
python -u AtomicAudioTool.py print_info \
  --input-acb-path /PATH/TO/MY.ACB \
  --input-awb-path /PATH/TO/MY.AWB
```

**TODO:**
- More complete representation of commands/settings and their arguments

For more details, run `python AtomicAudioTool.py print_info --help`.

### `to_xml`

Deserialize a provided UTF-formatted file (ACB and ACF tested, but in theory CPK could also work) to XML format, either to stdout or optionally to a provided XML output path. For example:

```
python -u AtomicAudioTool.py to_xml \
  --input-utf /PATH/TO/MY.{ACF|ACB} \
  --output-xml /PATH/TO/MY.xml
```

**TODO:**
- Represent AWB contents... better?
- Custom deserialization for ACF- and ACB- specific abstractions, not just general UTF

For more details, run `python AtomicAudioTool.py to_xml --help`.

### `from_xml`

Coming soon...?

### `extract_audio`

Extract the audio waveforms from the in-memory and (optionally) streamed AWBs associated with a provided ACB. Also optionally decrypt the extracted audio if in ADX format. For example:

```
python -u AtomicAudioTool.py extract_audio \
  --input-acb-path /PATH/TO/MY/P5RPC.ACB \
  --input-awb-path /PATH/TO/MY/P5RPC.AWB \
  --adx-key 9923540143823782 \
  --name-by-cue
```

**TODO:**
- Allow extraction from AWB without associated ACB
- Add decryption for HCA files
- Add option for direct conversion to WAV in output folder

For more details, run `python AtomicAudioTool.py extract_audio --help`.

### `replace_waveform`

Replace the audio file with a given AWB ID with a provided file. Optionally encrypt the file if it's an ADX. For example:

```
python -u AtomicAudioTool.py replace_waveform \
  --input-acb-path /PATH/TO/MY/P5RPC/VANILLA.ACB \
  --input-awb-path /PATH/TO/MY/P5RPC/VANILLA.AWB \
  --output-acb-path /PATH/TO/MY/P5RPC/MODDED.ACB \
  --output-awb-path /PATH/TO/MY/P5RPC/MODDED.AWB \
  --adx-key 9923540143823782 \
  --awb-id 5 \
  --new-audio-path /PATH/TO/MY/NEW.ADX
```

**TODO:**
- Add encryption for HCA files
- Add option for WAV (etc.) input with built-in conversion

For more details, run `python AtomicAudioTool.py replace_waveform --help`.

### `add_simple_cue`

Extremely simplified way of adding a simple cue that's just a single waveform containing the provided audio file. For example:

```
python -u AtomicAudioTool.py add_simple_cue \
  --input-acb-path /PATH/TO/MY/P5RPC/VANILLA.ACB \
  --input-awb-path /PATH/TO/MY/P5RPC/VANILLA.AWB \
  --output-acb-path /PATH/TO/MY/P5RPC/MODDED.ACB \
  --output-awb-path /PATH/TO/MY/P5RPC/MODDED.AWB \
  --adx-key 9923540143823782 \
  --cue-id 25 \
  --cue-name MyNewCue \
  --new-audio-path /PATH/TO/MY/NEW.ADX
```

**TODO:**
- Add more customization re: the type of cue and extra settings for it
- Add option to copy the style of an existing cue (to recreate the basic settings)

For more details, run `python AtomicAudioTool.py add_simple_cue --help`.

## Credits

All of the parsing code was heavily based on the good work of several existing libraries:

- [LazyBone152](https://github.com/LazyBone152)'s [XV2-Tools](https://github.com/LazyBone152/XV2-Tools) (License: MIT)
- [Thealexbarney](https://github.com/Thealexbarney)'s [VGAudio](https://github.com/Thealexbarney/VGAudio) (License: MIT)
- [vgmstream](https://github.com/vgmstream)'s [vgmstream](https://github.com/vgmstream/vgmstream) (License: custom)

Finally, none of the binary reading or writing would happen without the `exbip` Python library / forthcoming package — both original and port created and generously provided by [Pherakki](https://github.com/Pherakki).
