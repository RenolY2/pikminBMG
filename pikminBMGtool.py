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
def read_uint32(f, bigendian=True):
    return struct.unpack(">I" if bigendian else "I", f.read(4))[0]
def read_uint16(f, bigendian=True):
    return struct.unpack(">H" if bigendian else "H", f.read(2))[0]
def read_uint8(f):
    return struct.unpack("B", f.read(1))[0]
def read_uint24(f, bigendian):
    upperval = read_uint8(f)
    lowerval = read_uint16(f, bigendian)
    return (upperval << 16) | lowerval  

def read_magic(f, bigendian=True):
    if bigendian:
        return f.read(4)
    else:
        return bytes(reversed(f.read(4)))
        

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
        if magic != b"MESGbmg1" and magic != b"MESG1gmb":
            raise RuntimeError(
                "Input file not a BMG file. Encountered magic {0}".format(magic)
                )
                
        bigendian = True 
        if magic == b"MESG1gmb":
            print("BMG detected as Little Endian (Switch)")
            bigendian = False 
            
        filesize = read_uint32(f, bigendian)
        sectioncount = read_uint32(f, bigendian)
        encodingval = read_uint32(f)
        if encodingval == 0x03000000:
            print("Got encoding value {0:x}, assuming Shift-JIS encoding".format(encodingval))
            encoding = "shift-jis"
        else:
            print("Got encoding value {0:x}, assuming latin-1 encoding".format(encodingval))
            encoding = "latin-1"#"iso8859-15" #latin-9
        
        padding = f.read(0x0C)
        
        print(magic)
        print("filesize:", hex(filesize))
        print("sections:", sectioncount)
        
        sections = []
        
        for i in range(sectioncount):  
            sectionstart = f.tell()
            magic = read_magic(f, bigendian)
            sectionsize = read_uint32(f, bigendian)
            print("found section", magic, "with size", hex(sectionsize))
            data = f.read(sectionsize - 8)
            
            
            
            sections.append((sectionstart, magic, sectionsize, data))
            
        print("reached end of file")
        print(hex(f.tell()))
        
        #INF1
        inf_start, magic, size, data = sections[0]
        assert magic == b"INF1"
        
        f.seek(inf_start+8) # skipping magic and filesize
        messagecount = read_uint16(f, bigendian)
        itemlength = read_uint16(f, bigendian)
        
        #assert itemlength == 8
        f.read(4) #padding 
        inf_items = []
        for i in range(messagecount):
            dat1_offset = read_uint32(f, bigendian)
            attributes = f.read(itemlength-4)
            #print(hex(i), attributes)
            inf_items.append((dat1_offset, attributes))
        print(messagecount, "entries in inf1 read")
        print(hex(f.tell()), hex(inf_start+size))
        
        messages = []
        dat_start, dat_magic, dat_size, dat_data = sections[1]
        assert dat_magic == b"DAT1"
        
        mid_start, mid_magic, mid_size, mid_data = sections[2]
        assert mid_magic == b"MID1"
        
        additional_sections = []
        if len(sections) > 3:
            for i in range(3, len(sections)):
                additional_sections.append(sections[i])
        
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
            msgid = (read_uint24(f, bigendian), read_uint8(f)) # the uint24 is the message id, the uint8 is some sort of sub id?
            msgobj.msgid = msgid 
            
            messages.append(msgobj)
            
            i += 1
        f.seek(mid_start+0xA)
        unknown_mid_value = read_uint16(f, bigendian)
        
        messages_json = [{"Attribute Length": itemlength, 
                        "Unknown MID1 Value": "{:x}".format(unknown_mid_value)}]
                        
        for i, msg in enumerate(messages):
            messages_json.append({
                "ID": ", ".join(str(x) for x in msg.msgid), 
                "index": hex(i),
                "attributes": msg.attributes.decode("ascii"), 
                "text": msg.as_string_newline(encoding=encoding)
            })
        
        for _, magic, _, data in additional_sections:
            
            messages_json.append({"Section": str(magic, encoding="ascii"),
                                    "Data": str(hexlify(data), encoding="ascii")})
    
    #with io.open(output, "w", encoding="utf-8") as f:
    with output as f:
        json.dump(messages_json, f, indent="    ", ensure_ascii=False)
        
# --------------------
# Code for packing BMG
# -------------------- 

def write_uint32(f, val, bigendian=True):
    f.write(struct.pack(">I" if bigendian else "I", val)) 
    
def write_uint24(f, val, bigendian=True):
    if bigendian:
        upper = val >> 8
        lower = val & 0xFF
        f.write(struct.pack(">HB", upper, lower))
    else:
        upper = val >> 16
        lower = val & 0xFFFF
        write_uint8(f, upper)
        write_uint16(f, lower, bigendian)
        #f.write(struct.pack("HB", upper, lower))
    
def write_uint16(f, val, bigendian=True):
    f.write(struct.pack(">H" if bigendian else "H", val))
    
def write_uint8(f, val):
    f.write(struct.pack("B", val))
    
def write_magic(f, magic, bigendian=True):
    if bigendian:
        f.write(magic)
    else:
        f.write(bytes(reversed(magic)))
        

class Section(object):
    def __init__(self, magic, bigendian=True):
        self.magic = magic 
        #self.size = 0
        self.data = io.BytesIO()
        self._bigendian=bigendian
    
    def write_section(self, f, pad=True):
        data = self.data.getvalue()
        
        write_magic(f, self.magic, self._bigendian)
        sizepos = f.tell()
        write_uint32(f, 0xFF00FF00, self._bigendian) # placeholder 
        f.write(data)
        if pad:
            pos = f.tell()
            if pos % 32 != 0:
                padding = 32 - (pos % 32) 
            else:
                padding = 0
            f.write(b"\x00"*padding)
        else:
            padding = 0
        
        now = f.tell()
        f.seek(sizepos)
        write_uint32(f, 8 + len(data) + padding, self._bigendian)
        f.seek(now)
        
def pack_json_to_bmg(inputJSONfile, outputBMG, encoding="shift-jis", bigendian=True):
    #with io.open(inputJSONfile, "r", encoding="utf-8") as f:
    #    messages = json.load(f)
    print("Big endian?", bigendian)
    messages = json.load(inputJSONfile)
    
    inf_section = Section(b"INF1", bigendian)
    dat_section = Section(b"DAT1", bigendian)
    mid_section = Section(b"MID1", bigendian)

    # INF1 header
    unk_mid1_val = 0x1001
    attrlen = messages.pop(0)
    if "Attribute Length" in attrlen:
        attrlength = int(attrlen["Attribute Length"])
        if "Unknown MID1 Value" in attrlen:
            unk_mid1_val = int(attrlen["Unknown MID1 Value"], 16)

    else:
        messages.insert(0, attrlen)
        attrlength = 8
        
    

    additional_sections = []
    tmp = []
    for message in messages:
        if "Section" not in message:
            tmp.append(message)
        else:
            section = Section(bytes(message["Section"], encoding="ascii"))
            section.data.write(unhexlify(message["Data"]))
            additional_sections.append(section)
    
    messages = tmp 
    write_uint16(inf_section.data, len(messages), bigendian)   # message count 
    write_uint16(inf_section.data, attrlength, bigendian)
    write_uint32(inf_section.data, 0x00000000, bigendian)      # padding
    # DAT1 has no real header
    dat_section.data.write(b"\x00") # write the empty string  

    # MID1 header 
    write_uint16(mid_section.data, len(messages), bigendian)   # message count 
    write_uint16(mid_section.data, unk_mid1_val, bigendian)          # unknown but always this value 
    write_uint32(mid_section.data, 0x00000000, bigendian)      # padding 

    written = 1
    encoding = encoding #"shift-jis" #"iso8859-15"
    for inm, msg in enumerate(messages):
        attributes = unhexlify(msg["attributes"])
        if len(msg["text"]) == 1 and len(msg["text"][0]) == 0:
            offset = written
        else: 
            offset = written 
        
        # Write INF1 data (offset+attributes table)
        write_uint32(inf_section.data, offset, bigendian)
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
                    tmpstart=string.tell()
                    letter = string.read(1)
                    
                    while letter != "}":
                        if letter == "":
                            curr = string.tell()
                            string.seek(tmpstart)
                            data = string.read(curr-tmpstart)
                            raise RuntimeError("Hit end of string while reading command sequence: {0} in message ID {1}".format(data, msg["ID"])) 
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
        
        write_uint24(mid_section.data, id, bigendian)
        write_uint8(mid_section.data, num)
        
    #with open(outputBMG, "wb") as f:
    with outputBMG as f:
        if bigendian:
            f.write(b"MESGbmg1")
        else:
            f.write(b"MESG1gmb")
        write_uint32(f, 0xFF00FF00, bigendian) # placeholder for later 
        write_uint32(f, 0x3+len(additional_sections), bigendian) # section count
        
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
        
        for section in additional_sections:
            section.write_section(f)
        
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
    
    parser.add_argument("--switch", default=False, action="store_true",
                        help=(
                            "If set, will output a BMG for the Switch version of Pikmin 2 (Values stored as Little Endian)"
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
                pack_json_to_bmg(txtfile, bmgfile, encoding=args.encoding, bigendian=not args.switch)
        print("bmg file created")