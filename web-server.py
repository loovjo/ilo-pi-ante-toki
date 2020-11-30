import sys
import json
import asyncio

from aiohttp import web
import logging

import torch
import numpy as np

import matplotlib.pyplot as plt

from sentence_parser import STYPE_SEC, STYPE_AUX, PRIM_GL, SEC_GL, AUX_GL
from network import into_one_hot, generate_batch, load_from_save


enc, sec_dec, aux_dec, *_ = load_from_save()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("web.log"),
        logging.StreamHandler()
    ]
)


logging.info("started")

def make_json_response(data, status=200):
    return web.Response(
        body=json.dumps(data),
        content_type='application/json',
        status=status,
    )


class WebInterface:
    def __init__(self, app):
        self.app = app

        app.router.add_post("/api/translate", self.translate)

        app.router.add_get("/", self.index)

        app.router.add_static("/", 'static')

        self.currently_blocked_users = set()

    async def index(self, req):
        return web.Response(
            body=open("static/index.html", "r").read(),
            content_type='text/html',
            status=200,
        )

    async def translate(self, req):
        ip, port = req.transport.get_extra_info("peername")
        if ip in self.currently_blocked_users:
            logging.info(f"Too many requests for {ip}")
            return make_json_response({"error": "too many requests"}, status=400)

        self.currently_blocked_users.add(ip)
        try:
            await asyncio.sleep(1)

            data = await req.json()
            logging.info(f"Translating {repr(data)}")

            bpe = PRIM_GL.str_to_bpe(data["input"])
            xs = torch.LongTensor([bpe])

            eof_idx = -1
            did_cuttof = False
            for e in range(5):
                ylen = 5 * 2 ** e
                ys = torch.LongTensor([[-1] * ylen])

                hid = enc(xs)
                outs, atts = sec_dec(hid, ys, 0)
                out, att = outs[0], atts[0]

                hard_out = out.argmax(axis=1)

                hout_eofs = (hard_out == SEC_GL.n_tokens() - 1).nonzero()
                if len(hout_eofs) == 0:
                    eof_idx = ylen
                    continue
                eof_idx = hout_eofs[0]
                did_cuttof = True


            out = out[:eof_idx]
            hard_out = hard_out[:eof_idx]
            att = att[:eof_idx]

            hy_words = [SEC_GL.bpe_to_str([word]) for word in hard_out]

            if did_cuttof:
                out = "".join(hy_words)
            else:
                out = "".join(hy_words) + "..."

            logging.info(f"Got {repr(out)}")
            return make_json_response({"result": out})
        finally:
            self.currently_blocked_users.remove(ip)

    def run(self, port):
        web.run_app(self.app, port=port)


app = web.Application()

WEB_STATE = WebInterface(app)

if len(sys.argv) == 2:
    WEB_STATE.run(port=int(sys.argv[1]))
else:
    WEB_STATE.run(port=8080)