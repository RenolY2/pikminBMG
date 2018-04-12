import argparse
import struct 
import io 
import json 
import codecs
from binascii import hexlify, unhexlify

"""
pikminBMGtool.py by Yoshi2
Feel free to do with the code whatever, but please credit me :D
I'm not liable for any bugs caused by modifications to the code that weren't done by me.
"""

# --------------------
# Code for dumping BMG
# -------------------- 

def pretty_hex(string):
    return " ".join("{:02X}".format(char) for char in string)
def pretty_hex_no_space(string):
    return "".join("{:02X}".format(char) for char in string)
def read_uint32(f):
    return struct.unpack(">I", f.read(4))[0]
def read_uint16(f):
    return struct.unpack(">H", f.read(2))[0]
def read_uint8(f):
    return struct.unpack("B", f.read(1))[0]
def read_uint24(f):
    upperval = read_uint8(f)
    lowerval = read_uint16(f)
    
    return (upperval << 16) | lowerval 

    
class Message(object):
    def __init__(self):
        self.attributes = ""
        self.message = []
        self.msgid = None 
        
    def as_string_newline(self, encoding="shift-jis"):#encoding="iso8859-15"):
        msg = ""
        
        for part in self.message:
            if len(part) == 0:
                continue
            elif part[0] == 0x1A:
                msg += (b"{"+hexlify(part) +b"}").decode(encoding)
            else:
                part = part.decode(encoding)
                part = part.replace("{", "\\{")
                part = part.replace("}", "\\}")
                msg += part 
        #print(msg)
        #msg = msg.decode("iso8859-15")
        #msg = msg.decode(encoding)
        #print(msg)
        return msg.split("\n")
        
def dump_bmg_to_jsontxt(inputBMG, output):
    #with open(inputBMG, "rb") as f:
    with inputBMG as f:
        magic = f.read(0x08)
        if magic != b"MESGbmg1":
            raise RuntimeError(
                "Input file not a BMG file. Encountered magic {0}".format(magic)
                )
                                
        filesize = read_uint32(f)
        sectioncount = read_uint32(f)
        encodingval = read_uint32(f)
        if encodingval == 0x03000000:
            encoding = "shift-jis"
        else:
            encoding = "latin-1"#"iso8859-15" #latin-9
        
        padding = f.read(0x0C)
        
        print(magic)
        print("filesize:", hex(filesize))
        print("sections:", sectioncount)
        
        sections = []
        
        for i in range(sectioncount):  
            sectionstart = f.tell()
            magic = f.read(4)
            sectionsize = read_uint32(f)
            print("found section", magic, "with size", hex(sectionsize))
            data = f.read(sectionsize - 8)
            
            
            
            sections.append((sectionstart, magic, sectionsize, data))
            
        print("reached end of file")
        print(hex(f.tell()))
        
        #INF1
        inf_start, magic, size, data = sections[0]
        assert magic == b"INF1"
        
        f.seek(inf_start+8) # skipping magic and filesize
        messagecount = read_uint16(f)
        itemlength = read_uint16(f)
        
        assert itemlength == 8
        f.read(4) #padding 
        inf_items = []
        for i in range(messagecount):
            dat1_offset = read_uint32(f)
            attributes = f.read(itemlength-4)
            
            inf_items.append((dat1_offset, attributes))
        print(messagecount, "entries in inf1 read")
        print(hex(f.tell()), hex(inf_start+size))
        
        messages = []
        dat_start, dat_magic, dat_size, dat_data = sections[1]
        assert dat_magic == b"DAT1"
        
        mid_start, mid_magic, mid_size, mid_data = sections[2]
        assert mid_magic == b"MID1"
        
        i = 0
        
        for offset, attribs in inf_items:
            f.seek(dat_start+offset+8)
            
            char = f.read(1)
            
            text = []
            
            out_text = b""
            
            while char != b"\x00":
                if char == b"\x1A":
                    text.append(out_text)
                    arglen = f.read(1)
                    
                    arglenval = struct.unpack(">B", arglen)[0]
                    
                    #arglen = read_uint8(f)
                    
                    text.append(char + arglen + f.read(arglenval-2))
                    
                    out_text = b""
                else:
                    out_text += char
                
                char = f.read(1)
            
            
            text.append(out_text)
            
            msgobj = Message()
            msgobj.attributes = hexlify(attribs)
            msgobj.message = text 
            
            f.seek(mid_start+0x10+i*4)
            msgid = (read_uint24(f), read_uint8(f)) # the uint24 is the message id, the uint8 is some sort of sub id?
            msgobj.msgid = msgid 
            
            messages.append(msgobj)
            
            i += 1
        
        messages_json = []
        for msg in messages:
            messages_json.append({
                "ID": ", ".join(str(x) for x in msg.msgid), 
                "attributes": msg.attributes.decode("ascii"), 
                "text": msg.as_string_newline(encoding=encoding)
            })
    
    
    #with io.open(output, "w", encoding="utf-8") as f:
    with output as f:
        json.dump(messages_json, f, indent="    ", ensure_ascii=False)
        
# --------------------
# Code for packing BMG
# -------------------- 

def write_uint32(f, val):
    f.write(struct.pack(">I", val)) 
    
def write_uint24(f, val):
    upper = val >> 8
    lower = val & 0xFF 
    
    f.write(struct.pack(">HB", upper, lower))
    
def write_uint16(f, val):
    f.write(struct.pack(">H", val))
    
def write_uint8(f, val):
    f.write(struct.pack(">B", val))

class Section(object):
    def __init__(self, magic):
        self.magic = magic 
        #self.size = 0
        self.data = io.BytesIO()
    
    def write_section(self, f):
        data = self.data.getvalue()
        
        f.write(self.magic)
        sizepos = f.tell()
        write_uint32(f, 0xFF00FF00) # placeholder 
        f.write(data)
        pos = f.tell()
        if pos % 32 != 0:
            padding = 32 - (pos % 32) 
        else:
            padding = 0
        f.write(b"\x00"*padding)
        
        now = f.tell()
        f.seek(sizepos)
        write_uint32(f, 8 + len(data) + padding)
        f.seek(now)
        
def pack_json_to_bmg(inputJSONfile, outputBMG, encoding="shift-jis"):
    #with io.open(inputJSONfile, "r", encoding="utf-8") as f:
    #    messages = json.load(f)
    
    messages = json.load(inputJSONfile)
    
    inf_section = Section(b"INF1")
    dat_section = Section(b"DAT1")
    mid_section = Section(b"MID1")

    # INF1 header
    write_uint16(inf_section.data, len(messages))   # message count 
    write_uint16(inf_section.data, 0x08)            # length of each item
    write_uint32(inf_section.data, 0x00000000)      # padding

    # DAT1 has no real header
    dat_section.data.write(b"\x00") # write the empty string  

    # MID1 header 
    write_uint16(mid_section.data, len(messages))   # message count 
    write_uint16(mid_section.data, 0x1001)          # unknown but always this value 
    write_uint32(mid_section.data, 0x00000000)      # padding 

    written = 1
    encoding = encoding #"shift-jis" #"iso8859-15"
    for inm, msg in enumerate(messages):
        attributes = unhexlify(msg["attributes"])
        if len(msg["text"]) == 1 and len(msg["text"][0]) == 0:
            offset = 0
        else: 
            offset = written 
        
        # Write INF1 data (offset+attributes table)
        write_uint32(inf_section.data, offset)
        inf_section.data.write(attributes)
        
        if offset > 0:
            # Write DAT1 data (string)
            text = "\x0A".join(msg["text"])
            string = io.StringIO(text)
            
            textsection = dat_section.data 
            start = textsection.tell()
            
            while string.tell() < len(text):
                letter = string.read(1)
                if letter == "\\":  
                    curr = string.tell()
                    
                    next = string.read(1)
                    if next == "{":
                        textsection.write(b"{")
                    elif next == "}":
                        textsection.write(b"}")
                    else:
                        string.seek(curr)
                        textsection.write(b"\\")
                elif letter == "{":
                    escapesequence = b""
                    letter = string.read(1)
                    
                    while letter != "}":
                        hexval = letter+string.read(1)
                        escapesequence += unhexlify(hexval)
                        letter = string.read(1)
                        
                    textsection.write(escapesequence)
                else:
                    try:
                        encodedletter = letter.encode(encoding)
                    except:
                        encodedletter = letter.encode(encoding, 'replace')
                        print("Warning for Message ID {0}: Unsupported character '{1}' replaced with '{2}'".format(msg["ID"], letter, encodedletter.decode()))
                        text = textsection.getvalue()
                        lastindex = len(text)
                        start = lastindex - 20
                        if start < 0: start = 0
                        
                        print("Context:", text[start:-1])
                    
                    textsection.write(encodedletter)
                    
            textsection.write(b"\x00")
            written += (textsection.tell() - start)
                    
            
        # Write MID1 data (message IDs)
        id, num = msg["ID"].split(",")
        
        id = int(id.strip())
        num = int(num.strip()) # unknown, most of the time 0 but sometimes 1, e.g. with duplicate strings 
        
        write_uint24(mid_section.data, id)
        write_uint8(mid_section.data, num)
        
    #with open(outputBMG, "wb") as f:
    with outputBMG as f:
        f.write(b"MESGbmg1")
        write_uint32(f, 0xFF00FF00) # placeholder for later 
        write_uint32(f, 0x3) # section count
        
        if encoding == "shift-jis":
            write_uint32(f, 0x03000000) # Used for US and Jpn, so possibly encoding?
        elif encoding == "latin-1":
            write_uint32(f, 0x01000000) # Used for Ger, Fra, and probably the other languages too
        else:
            raise RuntimeError("unknown encoding: {}".format(encoding))
            
        f.write(b"\x00"*12)
        
        inf_section.write_section(f)
        dat_section.write_section(f)
        mid_section.write_section(f)
        end = f.tell()
        
        f.seek(0x08)
        write_uint32(f, end) # write file length 
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["dump", "pack"], type=lambda s: s.lower(),
                        help=(  
                            "Action to take. Can be 'dump' to create a json-formatted text file out of a BMG, "
                            "or 'pack' to make a BMG out of a json-formatted text file"
                            )
                        )
                        
    parser.add_argument("--encoding", choices=["shift-jis", "latin-1"], default="shift-jis", type=lambda s: s.lower(),
                        help=(
                            "Encoding to be used when packing a text file into a BMG. Can either be 'shift-jis' "
                            "(japanese and latin characters, used for Jpn and Eng BMGs) or 'latin-1' "
                            "(latin characters and various European language characters, used for Ger, Fra and others)."
                            "Default is shift-jis."
                            )
                        )
                        
    parser.add_argument("input",
                        help=(
                            "When using 'dump', file path to Pikmin 2's BMG file goes here. "
                            "When using 'pack', file path to a dumped text file goes here."
                            )
                        )
    
    parser.add_argument("output", default=None, nargs = '?',
                        help=(
                            "Optional.\n"
                            "When using 'dump', the destination file path to which the text file should be written goes here."
                            "When using 'pack', the destination file path to which the BMG file should be written goes here.\n"
                            "If left out, '.txt' or '.bmg' will be appended to the input file path to create the output path."
                            )
                        )
    
    args = parser.parse_args()
    
    input = args.input 
    
    if args.action == "dump": # Read a BMG and create a TXT 
        if args.output is None:
            output = input + ".txt"
        else:
            output = args.output 
        
        print("input:", input)
        print("output:", output)
        with open(input, "rb") as bmgfile:
            with io.open(output, "w", encoding="utf-8") as txtfile:
                dump_bmg_to_jsontxt(bmgfile, txtfile)
        print("json-formatted txt file created")
        
    elif args.action == "pack": # Read a TXT and create a BMG 
        if args.output is None:
            output = input + ".bmg"
        else:
            output = args.output 
            
        print("input:", input)
        print("output:", output)
        print("encoding:", args.encoding)
        
        # Detect BOM of input file
        with open(input, "rb") as f:
            bom = f.read(4)
        
        if bom.startswith(codecs.BOM_UTF8):
            encoding = "utf-8-sig"
        elif bom.startswith(codecs.BOM_UTF32_LE) or bom.startswith(codecs.BOM_UTF32_BE):
            encoding = "utf-32"
        elif bom.startswith(codecs.BOM_UTF16_LE) or bom.startswith(codecs.BOM_UTF16_BE):
            encoding = "utf-16"
        else:
            encoding = "utf-8"
        
        print("Assuming encoding of input file:", encoding)
        
        with io.open(input, "r", encoding=encoding) as txtfile:
            with open(output, "wb") as bmgfile:
                pack_json_to_bmg(txtfile, bmgfile, encoding=args.encoding)
        print("bmg file created")