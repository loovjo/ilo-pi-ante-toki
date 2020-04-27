import os

from abc import ABC, abstractmethod
import struct

class Gram(ABC):
    @abstractmethod
    def parse_one(tag_byte, inp_file):
        pass

    @abstractmethod
    def __str__(self):
        pass

    def __repr__(self):
        return str(self)

class Orig(Gram):
    def __init__(self, char):
        self.char = char

    def parse_one(tag_byte, inp_file):
        if tag_byte == 0:
            return None

        n_utf8_bytes = tag_byte
        utf8 = inp_file.read(n_utf8_bytes)
        char = utf8.decode('utf-8')
        inp_file.read(8 - n_utf8_bytes) # Skip padding

        return Orig(char)

    def __str__(self):
        return f"Orig({self.char})"

class Composition(Gram):
    def __init__(self, a, b):
        # Indicies into gram list
        self.a = a
        self.b = b

    def parse_one(tag_byte, inp_file):
        if tag_byte != 0:
            return None

        a, = struct.unpack("<I", inp_file.read(4))
        b, = struct.unpack("<i", inp_file.read(4))

        return Composition(a, b)

    def __str__(self):
        return f"Composition({self.a}, {self.b})"

bpe_list = [Orig, Composition]

class GramList:
    def __init__(self, gram_list):
        self.gram_list = gram_list

    def from_file(inp_file):
        gram_list = []
        while True:
            tag_lst = inp_file.read(1)
            if len(tag_lst) == 0:
                break
            tag = tag_lst[0]

            found_any = False
            for target_class in bpe_list:
                parsed = target_class.parse_one(tag, inp_file)
                if parsed == None:
                    continue

                gram_list.append(parsed)
                found_any = True
                break

            if not found_any:
                raise Exception(f"invalid tag: {tag}")


        return GramList(gram_list)

    def bpe_to_str(self, bpe):
        while True:
            all_are_origs = True
            new_bpe = []
            for token in bpe:
                pointed_gram = self.gram_list[token]

                if isinstance(pointed_gram, Orig):
                    new_bpe.append(token)
                if isinstance(pointed_gram, Composition):
                    new_bpe.append(pointed_gram.a)
                    new_bpe.append(pointed_gram.b)
                    all_are_origs = False

            if all_are_origs:
                break

            bpe = new_bpe

        return "".join(self.gram_list[x].char for x in bpe)

    def str_to_bpe(self, st):
        # convert into tokens
        bpe = []
        for ch in st:
            found = False
            for i, gram in enumerate(self.gram_list):
                if isinstance(gram, Orig) and gram.char == ch:
                    bpe.append(i)
                    found = True
                    break
            if not found:
                print(f"character {ch} not found!")

        # because gram_list is toposorted, we just need to apply all compositions in order
        for i, gram in enumerate(self.gram_list):
            if not isinstance(gram, Composition):
                continue

            new_bpe = []

            skip_next = False
            for token_here, next_token in zip(bpe, bpe[1:] + [None]):
                if skip_next:
                    skip_next = False
                    continue

                if token_here == gram.a and next_token == gram.b:
                    new_bpe.append(i)
                    skip_next = True
                else:
                    new_bpe.append(token_here)

            bpe = new_bpe

        return bpe


    def __str__(self):
        return f"GramList({self.gram_list})"

STYPE_PRIM = 0
STYPE_SEC = 1
STYPE_AUX = 2


sec_links = open(os.path.expanduser("~/.cache/ilo-pi-ante-toki/sec-links.bin"), "rb")
aux_links = open(os.path.expanduser("~/.cache/ilo-pi-ante-toki/aux-links.bin"), "rb")

sents_prim = open(os.path.expanduser("~/.cache/ilo-pi-ante-toki/sentences-prim.bin"), "rb")
sents_sec = open(os.path.expanduser("~/.cache/ilo-pi-ante-toki/sentences-sec.bin"), "rb")
sents_aux = open(os.path.expanduser("~/.cache/ilo-pi-ante-toki/sentences-aux.bin"), "rb")

def load_one_pair(other_stype):
    pass

if __name__ == "__main__":
    gl = GramList.from_file(open(os.path.expanduser("~/.cache/ilo-pi-ante-toki/ngrams-prim.bin"), "rb"))

    enc = gl.str_to_bpe("Besides the above method, any other way to find out whether is fp is already at the eof?")
    print(enc)
    print(", ".join("'" + gl.bpe_to_str([x]) + "'" for x in enc))
