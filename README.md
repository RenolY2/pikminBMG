----
pikminBMGtool.py v0.5 by Yoshi2
A tool for converting Pikmin 2 BMG files to text (JSON) and from text (JSON) to BMG.

Requires Python 3 (Recommended: version 3.6 or newer)
On Windows, when installing Python make sure you have "Add Python to PATH" option enabled at the 
start of the installation so that the bat files can work.
---

Example use in command line:
python .\pikminBMGtool.py DUMP pikmin2.bmg pikmin2_messages.txt
python .\pikminBMGtool.py PACK pikmin2_messages.txt pikmin2.bmg 

python .\pikminBMGtool.py PACK --encoding shift-jis pikmin2_messages.txt pikmin2.bmg 
python .\pikminBMGtool.py PACK --encoding latin-1 pikmin2_messages.txt pikmin2.bmg 

if the --encoding option is left out, the encoding defaults to shift-jis, which
is used for the Japanese and English bmg files. latin-1 is used by the remaining
languages (German, French, Italian, ...)

dumpBmg.bat, packBmg.bat and packBmglatin1.bat are included to allow for simple drag and drop.
dumpBmg dumps a bmg to text, packBmg packs a text file to BMG with shift-jis encoding,
packBmg_latin1 packs a text file to BMG with latin-1 encoding.

BMG files are found in mesRes.szs archives in the message folder in the root of Pikmin 2's file system.
Extract and repack them with a tool that supports yaz0-compressed RARC archives, e.g. Lunaboy's RARC tools.