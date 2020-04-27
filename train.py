import random
import os

import torch
import torch.nn as nn
import torch.nn.functional as F

from sentence_parser import STYPE_SEC, STYPE_AUX, PRIM_GL, SEC_GL, AUX_GL
from network import device, Encoder, Decoder, into_one_hot, generate_batch, load_from_save, save


def display_tokens(toklist, gl):
    out = ""
    last = 0 # 0 = any char, 1 = end, 2 = end after another end
    for tidx in toklist:
        tok = gl.bpe_to_str([tidx])
        if tok != "<EOF>":
            out += "/" + tok
            last = 0
        else:
            if last == 0:
                out += "/<EOF>"
                last += 1
            elif last == 1:
                out += "..."
                last += 1
    return out[1:]

enc, sec_dec, aux_dec, opt = load_from_save()

EPSILON = 1e-8

if __name__ == "__main__":
    torch.autograd.set_detect_anomaly(True)
    crit = nn.CrossEntropyLoss()

    epoch = 0
    while True:
        epoch += 1

        sec_losses = []
        aux_losses = []

        sec_info = ("sec", sec_losses, sec_dec, STYPE_SEC)
        aux_info = ("aux", aux_losses, aux_dec, STYPE_AUX)

        for batch_nr in range(16):
            print(hex(batch_nr)[2:], end=" ")
            for name, losses, dec, stype in [sec_info, aux_info]:
                print(name, end=":")
                xs, ys = generate_batch(2048, stype)

                print("l={:2d}/{:2d};".format(xs.size(1), ys.size(1)), end=" ", flush=True)

                enc.zero_grad()
                dec.zero_grad()

                print("z", end="", flush=True)

                hids = enc(xs)
                print("e", end="", flush=True)
                y_hat, _ = dec(hids, ys)
                print("d", end="", flush=True)

                pred = y_hat.argmax(axis=2)
                acc = (pred == ys).type(torch.FloatTensor).mean()

                print("a", end=" ", flush=True)

                loss = crit(EPSILON + y_hat.view(-1, SEC_GL.n_tokens()), ys.view(-1) % SEC_GL.n_tokens())

                print("L={:.3f}; a={:.3f}%".format(loss, acc*100), end=" ")
                loss.backward()
                print("b", end=" ")
                opt.step()
                print("s", end=";")

                losses.append(loss.item())
            print()

        save(enc, sec_dec, aux_dec, opt)

        print("Epoch", epoch, "done")

        for name, losses, dec, stype in [sec_info, aux_info]:
            print(f"For {name}")
            xs, ys = generate_batch(4, stype, max_length=10)
            gl = SEC_GL if stype == STYPE_SEC else AUX_GL

            hids = enc(xs)
            y_hat, _ = dec(hids, ys, teacher_forcing_prob=0)

            # Display
            for i in range(len(xs)):
                print()
                print(f"> {display_tokens(xs[i], PRIM_GL)} (= {display_tokens(ys[i], gl)})")
                gen = y_hat[i].argmax(dim=1)
                print("≈", display_tokens(gen, gl))

            print("Loss:", sum(losses) / len(losses))
