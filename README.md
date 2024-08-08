# Atomic Audio

*WIP tools and libraries for parsing, editing, and creating CRI audio formats, including cuesheets (ACB), wavebanks (AWB), materials (ADX), and hopefully-soon-to-be more.*

There will eventually be several interfaces for the tooling, including:
- An Avalonia-based GUI
- A C#/.NET (NuGet) library
- A Python CLI tool

The Python CLI tool is the only part that's currently included as a prototype/proof-of-concept, but an early draft of the C# version can be found in the [EVTUI repo](https://github.com/DarkPsydeOfTheMoon/EVTUI/tree/main/src/EVTUI/Core/FileIO/Formats/ACB).

## Getting Started

- [AtomicAudioGUI](https://github.com/DarkPsydeOfTheMoon/AtomicAudio/tree/main/src/AtomicAudioGUI/README.md) (Avalonia-based GUI)
- [AtomicAudioLib](https://github.com/DarkPsydeOfTheMoon/AtomicAudio/tree/main/src/AtomicAudioLib/README.md) (C#/.NET library)
- [AtomicAudioPy](https://github.com/DarkPsydeOfTheMoon/AtomicAudio/tree/main/src/AtomicAudioPy/README.md) (Python CLI tool)

## Credits

For the C# library/GUI:

- [AvaloniaUI](https://github.com/AvaloniaUI)'s [Avalonia](https://github.com/AvaloniaUI/Avalonia) (License: MIT)
- [VideoLAN](https://github.com/videolan)'s [LibVLCSharp](https://github.com/videolan/libvlcsharp) (License: LGPL-2.1)

All of the parsing code was heavily based on the good work of several existing libraries:

- [LazyBone152](https://github.com/LazyBone152)'s [XV2-Tools](https://github.com/LazyBone152/XV2-Tools) (License: MIT)
- [Thealexbarney](https://github.com/Thealexbarney)'s [VGAudio](https://github.com/Thealexbarney/VGAudio) (License: MIT)
- [vgmstream](https://github.com/vgmstream)'s [vgmstream](https://github.com/vgmstream/vgmstream) (License: custom)

Finally, none of the binary reading or writing would happen without the `Serialization` C# library and `exbip` Python library. `Serialization` is a port of the forthcoming `exbip` package — both original and port created and generously provided by [Pherakki](https://github.com/Pherakki).
