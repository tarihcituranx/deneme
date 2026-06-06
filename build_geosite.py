#!/usr/bin/env python3
import urllib.request, sys, os

def decode_varint(data, pos):
    result = 0; shift = 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80): break
        shift += 7
    return result, pos

def encode_varint(v):
    r = b""
    while True:
        bits = v & 0x7F; v >>= 7
        r += bytes([bits | (0x80 if v else 0)])
        if not v: break
    return r

def read_field(data, pos):
    if pos >= len(data): return None
    tag, pos = decode_varint(data, pos)
    field, wire = tag >> 3, tag & 0x7
    if wire == 2:
        ln, pos = decode_varint(data, pos)
        val = data[pos:pos+ln]; pos += ln
    elif wire == 0:
        val, pos = decode_varint(data, pos)
    elif wire == 1:
        val = data[pos:pos+8]; pos += 8
    elif wire == 5:
        val = data[pos:pos+4]; pos += 4
    else:
        return None
    return field, wire, val, pos

def wrap(field, wire, val):
    tag = encode_varint((field << 3) | wire)
    if wire == 2: return tag + encode_varint(len(val)) + val
    elif wire == 0: return tag + encode_varint(val)
    return tag + val

def get_cc(b):
    pos = 0
    while pos < len(b):
        r = read_field(b, pos)
        if not r: break
        field, wire, val, pos = r
        if field == 1 and wire == 2: return val.decode("utf-8").upper()
    return ""

def parse_list(data):
    entries = []; pos = 0
    while pos < len(data):
        r = read_field(data, pos)
        if not r: break
        field, wire, val, pos = r
        if field == 1 and wire == 2: entries.append((get_cc(val), val))
    return entries

PLAIN=0; REGEX=1; DOMAIN=2; FULL=3

def parse_domains_file(path):
    domains = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if line.startswith("regexp:"): domains.append((REGEX, line[7:]))
            elif line.startswith("full:"): domains.append((FULL, line[5:]))
            elif line.startswith("keyword:"): domains.append((PLAIN, line[8:]))
            else: domains.append((DOMAIN, line))
    return domains

def s(field, text):
    b = text.encode()
    return encode_varint((field<<3)|2) + encode_varint(len(b)) + b

def vi(field, val):
    return encode_varint((field<<3)|0) + encode_varint(val)

def embed(field, data):
    return encode_varint((field<<3)|2) + encode_varint(len(data)) + data

def build_tr(domains):
    body = s(1, "TR")
    for dtype, val in domains:
        body += embed(2, vi(1, dtype) + s(2, val))
    return body

with open("loyalsoldier-geosite.dat","rb") as f: raw = f.read()
entries = parse_list(raw)
domains = parse_domains_file("tr-domains.txt")
custom_tr = build_tr(domains)

merged = b""; tr_done = False
for cc, data in entries:
    if cc == "TR": merged += wrap(1,2,custom_tr); tr_done = True
    else: merged += wrap(1,2,data)
if not tr_done: merged += wrap(1,2,custom_tr)

with open("geosite.dat","wb") as f: f.write(merged)
print(f"✓ geosite.dat üretildi — {len(entries)} kategori, {len(domains)} TR kuralı")
