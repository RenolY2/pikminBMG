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

if the --encoding option is left out, the encoding for the created bmg defaults to shift-jis, which
is used for the Japanese and English bmg files. latin-1 is used by the remaining languages
(German, French, Italian, ...)

For the input txt file, the tool attempts to detect the encoding by the BOM (Byte Order Mark)
and otherwise defaults to utf-8. This way the following encodings are supported:
utf-8, utf-8-bom (used by Windows Notepad), utf-16 and utf-32.


dumpBmg.bat, packBmg.bat and packBmglatin1.bat are included to allow for simple drag and drop.
dumpBmg dumps a bmg to text, packBmg packs a text file to BMG with shift-jis encoding,
packBmg_latin1 packs a text file to BMG with latin-1 encoding.

BMG files are found in mesRes.szs archives in the message folder in the root of Pikmin 2's file system.
Extract and repack them with a tool that supports yaz0-compressed RARC archives, e.g. Lunaboy's RARC tools.


=== Information about BMG 

When dumping a BMG file to text you receive a JSON text file.
Each entry is a message that has an identification number, a secondary number 
that is 0 most of the time except for some treasure names, attributes that are full of zeros
most of the time, and the text itself.

New lines can be added to the text which will be intepreted as line breaks. 
Values inside { } are special sequences that cause special effects ingame, such as changing
color, text size or adding button graphics.

{1a05020000} signals end of a message page, used in Pikmin 2 for messages in which
you press a button to close it or to continue to the next part of a message.
