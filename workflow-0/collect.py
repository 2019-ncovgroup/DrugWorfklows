#!/usr/bin/env python3

import os
import sys
import glob
import time

data = dict()
sids = sys.argv[1:]

if len(sids) == 1 and os.path.isfile(sids[0]):
    data[sids[0][:-4]] = set()

print()
for sid in sids:
  # print(sid)
    oeb = None
    smi = None
    for task in sorted(glob.glob('%s/pilot.*/unit.*/unit.*.sh' % sid)):
        uid = os.path.basename(task)[:-3]
        with open(task, 'r') as fin:
            for line in fin.readlines():
                idx1 = line.find('theta_dock')
                idx2 = line.find('>')
                if idx1 < 0: continue
                if idx2 < 0: idx2 = len(line)
                try:
                    elems = line[idx1:idx2].split()
                    smi, oeb             = elems[2], elems[3]
                    idx_start, idx_count = elems[5], elems[6]
                except:
                    print(line[idx1:idx2])
                    raise
                break
        if not oeb:
          # print('skip %s' % task)
            continue
        oeb = oeb.strip('"')
        smi = smi.strip('"')
        oeb = os.path.basename(oeb)
        smi = os.path.basename(smi)
        oeb = oeb[:-4]
        smi = smi[:-4]

        idx_start = idx_start.strip('"')
        idx_count = idx_count.strip('"')
        idx_start = int(idx_start)
        idx_count = int(idx_count)

        if oeb not in data:
            data[oeb] = set()

        cnt = 0
        with open('%s/STDOUT' % os.path.dirname(task), 'r') as fin:
            for line in fin.readlines():
                if 'test,pl_pro' not in line:
                  # print('skip line:', line.strip())
                    continue
                data[oeb].add(line)
                cnt += 1
      # print('    ', uid, oeb, smi, idx_start, idx_count, cnt)
    if not oeb: print(sid)
    else      : print(sid, oeb, len(data[oeb]))

print()
for oeb in data:
    fname = '%s.out' % oeb
    if os.path.exists(fname):
        print('+ %s' % fname)
        with open(fname, 'r') as fin:
            for line in fin.readlines():
                data[oeb].add(line)

print()
for oeb in data:
    tname = '%s.tmp' % oeb
    fname = '%s.out' % oeb
    print('write %s' % tname)
    with open(tname, 'a') as fout:
        valid = list()
        for line in list(data[oeb]):
            if 'SMILES invalid' not in line:
                try:
                    cnt = int(line.split()[0])
                except:
                    continue
                valid.append([cnt, line])

        for entry in sorted(valid, key=lambda x: x[0]):
            fout.write(entry[1])
    os.system('mv %s %s' % (tname, fname))

print()

