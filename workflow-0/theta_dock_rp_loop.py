#!/usr/bin/env python3

import os
import sys
import math
import pandas as pd

import radical.pilot as rp
import radical.utils as ru


# ------------------------------------------------------------------------------
#
if __name__ == '__main__':


    target     =     sys.argv[1]
    smi_fname  =     sys.argv[2]
    tgt_fname  =     sys.argv[3]

    idx_start  = int(sys.argv[4])
    n_pilots   = int(sys.argv[5])
    n_tasks    = int(sys.argv[6])  # tasks per pilot
    n_samples  = int(sys.argv[7])  # samples per task
    specfile   = ''

    if len(sys.argv) > 8:
        n_samples = 0
        specfile  = sys.argv[8]

    cfg        = ru.read_json('config.json')
    model      = '%s/Model-generation' % os.getcwd()
    conda      = cfg[target]['conda']
    cpn        = cfg[target]['cpn']

    idx        = idx_start
    smiles     = pd.read_csv('%s/%s' % (model, smi_fname), sep=' ', header=None)
    assert(idx_start < smiles.shape[0]), [idx_start, smiles.shape[0]]

    session    = rp.Session()
    try:
        pmgr   = rp.PilotManager(session=session)
        umgr   = rp.UnitManager(session=session)
        pdinit = cfg[target]['pilot']

        # pilot cores are agent cores configured in config.json, + worker nodes
        cores  = pdinit['cores'] + (n_tasks * cpn)

        pdinit["cores"]         = cores
        pdinit["exit_on_error"] = True
        pdinit["input_staging"] = [
                model,
                'smi.sh',
                'theta_dock.sh',
                'theta_dock.py',
                'oe_license.txt'
               ]

        if specfile:
            pdinit["input_staging"].append(specfile)

        print('%d pilots: %d cores on %d nodes' % (n_pilots, cores, cores/cpn))

        pdescs = [rp.ComputePilotDescription(pdinit) for i in range(n_pilots)]
        pilots = pmgr.submit_pilots(pdescs)

        umgr.add_pilots(pilots)

        uids = n_pilots * n_tasks
        for p in range(n_pilots):

            cuds = list()

            for t in range(n_tasks):

                uid = p * n_tasks + t

                idx = idx_start \
                    + (p * n_tasks * n_samples) \
                    + (t * n_samples)
                print(p, t, idx, n_samples)

                cud = rp.ComputeUnitDescription()
                cud.cpu_processes  = 1
                cud.cpu_threads    = cpn
                cud.executable     = './theta_dock.sh'
                cud.arguments      =  [conda, smi_fname, tgt_fname,
                                       cpn, idx, n_samples, uid, uids, specfile]
                cud.environment    =  {'OE_LICENSE': 'oe_license.txt'}
                cud.input_staging  = [{'source': 'pilot:///Model-generation/input',
                                       'target': 'unit:///input',
                                       'action': rp.LINK},
                                      {'source': 'pilot:///Model-generation/impress_md',
                                       'target': 'unit:///impress_md',
                                       'action': rp.LINK},
                                      {'source': 'pilot:///oe_license.txt',
                                       'target': 'unit:///oe_license.txt',
                                       'action': rp.LINK},
                                      {'source': 'pilot:///theta_dock.sh',
                                       'target': 'unit:///theta_dock.sh',
                                       'action': rp.LINK},
                                      {'source': 'pilot:///theta_dock.py',
                                       'target': 'unit:///theta_dock.py',
                                       'action': rp.LINK},
                                      {'source': 'pilot:///smi.sh',
                                       'target': 'unit:///smi.sh',
                                       'action': rp.LINK},
                                      ]
                if specfile:
                    cud.input_staging.append({
                        'source': 'pilot:///%s' % specfile,
                        'target': 'unit:///specfile',
                        'action': rp.LINK})

                cuds.append(cud)

            # chunk defined for pilot
            print('submit %d tasks as chunk %d' % (len(cuds), p))
            umgr.submit_units(cuds)

        # all chunks submitted to pilots
        print('wait all')
        umgr.wait_units()

    finally:
        session.close(download=True)
        pass


# ------------------------------------------------------------------------------

