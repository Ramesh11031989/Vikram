# Agent notes

Instructions for AI coding agents and anyone scripting this repository.

## Blender

This project uses **Blender 5.2.2 LTS** (portable install). `blender` is not on PATH, so always call the full path to `blender.exe`.

| Shell | Path |
| --- | --- |
| Windows / PowerShell | `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` |
| WSL / bash | `/mnt/d/Tools/Blender/blender-5.2.2-windows-x64/blender.exe` |

Every `blender ...` command in the READMEs means this executable. For example, from the repository root in PowerShell:

```powershell
& 'D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python Blender/tools/build_cast.py
```

From WSL:

```bash
/mnt/d/Tools/Blender/blender-5.2.2-windows-x64/blender.exe --background --factory-startup --python-exit-code 1 --python Blender/tools/build_cast.py
```

Notes:

- Run commands from the repository root so relative script and `.blend` paths resolve.
- Use `--python-exit-code 1` so a failing script returns a non-zero exit code.
- Blender 5.2 prints `DeprecationWarning` for `use_nodes` on worlds and materials. It is expected to be removed in Blender 6.0, so new scripts should plan for that.
- Do not use the incomplete `C:\Program Files\Blender Foundation\Blender 4.3` folder. It has no `blender.exe`.
- Paths contain Devanagari characters. Keep files UTF-8 and quote every path.
- Redirect long Blender output to a log file and read it afterwards, then delete the log.

## Layout

See [README.md](README.md) for the file index, [Production/ART_PASSES.md](Production/ART_PASSES.md) for the art gates, and the per-character READMEs under `Blender/Characters/`.
