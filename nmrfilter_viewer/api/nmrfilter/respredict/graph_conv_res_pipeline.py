import numpy as np
import pickle
import pandas as pd
from ruffus import * 
from tqdm import  tqdm
from rdkit import Chem
import pickle
import os

from glob import glob
import json 

import time
import util
import nets
import relnets
import grmnets

from rdkit.Chem import AllChem
from rdkit.Chem.Draw import IPythonConsole
from rdkit.Chem import rdMolDescriptors as rdMD

import torch
from torch import nn
from tensorboardX import SummaryWriter

from tqdm import  tqdm
from netdataio import * 
import netdataio
import itertools
import graph_conv_many_nuc_util
from graph_conv_many_nuc_util import move

DATASET_DIR = "graph_conv_many_nuc_pipeline.datasets"
td = lambda x : os.path.join(DATASET_DIR, x)


NUC = '13C'  # "13C_1H"
TENSORBOARD_DIR = f"logs2.{NUC}"

#SPECT_SET = '13C_1HasBonded'
#SPECT_SET = '13C' # '13C_1H' # cbondedasBonded' 
SPECT_SET = '13C'

CHECKPOINT_DIR = "checkpoints" 
MAT_PROPS= 'aromatic'
DATASET_NAME = 'nmrshiftdb_hconfspcl_nmrshiftdb'
#DATASET_NAME = 'qm9'

NUC_LOSS_SCALE = {'13C' : 1.0} # , '1H' : 1.0/20.0}
NUC_STD_SCALE = {'13C' : 1.0} # , '1H' : 10.0} 

# NUC_LOSS_SCALE = {'1H' : 1.0/20.0} # , '1H' : 1.0/20.0}
# NUC_STD_SCALE = {'1H' : 10.0} # , '1H' : 10.0} 

tgt_max_n = 64 # 64
MAX_EPOCHS = 10000

EXP_NAME = f"good_graph_conv_res_{SPECT_SET}"


def create_validate_func(tgt_nucs):
    def val_func(res): # val, mask, truth):
        val = res['pred_res']
        mask = res['pred_mask']
        truth = res['pred_truth']
        res = {}
        for ni, n in enumerate(tgt_nucs):
            delta = (val[:, :, ni] - truth[:, :, ni])[mask[:, :, ni] > 0].flatten()
            res[f"{n}/test_std_err"] = np.std(delta)
            res[f"{n}/test_max_error"] = np.max(np.abs(delta))
            res[f"{n}/test_mean_abs_err"] = np.mean(np.abs(delta))
            res[f"{n}/test_abs_err_90"] = np.percentile(np.abs(delta), 90)
        return res
    return val_func

def create_uncertain_validate_func(tgt_nucs):
    def val_func(res): # val, mask, truth):
        mu = res['pred_mu']
        std = res['pred_std'] 
        mask = res['pred_mask']
        truth = res['pred_truth']
        res = {}
        for ni, n in enumerate(tgt_nucs):
            delta = (mu[:, :, ni] - truth[:, :, ni])[mask[:, :, ni] > 0].flatten()
            masked_std = (std[:, :, ni])[mask[:, :, ni] > 0].flatten()
            res[f"{n}/test_std_err"] = np.std(delta)
            res[f"{n}/test_max_error"] = np.max(np.abs(delta))
            res[f"{n}/test_mean_abs_err"] = np.mean(np.abs(delta))
            res[f"{n}/test_abs_err_90"] = np.percentile(np.abs(delta), 90)
            res[f"{n}/std/mean"] = np.mean(masked_std)
            res[f"{n}/std/min"] = np.min(masked_std)
            res[f"{n}/std/max"] = np.max(masked_std)

        return res
    return val_func


net_params_base = {'init_noise' : 1e-2, 
                   'resnet' : True, 
                   'int_d' : 1024, 
                   'layer_n' : 8, 
                   'GS' : 1, 
                   'agg_func' : 'goodmax', 
                   #'combine_in' : True, 
                   'force_lin_init' : True, 
                   'g_feature_n' : -1, #  ds_test[0][1].shape[-1], 
                   #'extra_lin_int_d' : 512, 
                   #'use_highway' : True, 
                   'grl_res_depth' : 4, 
                   'grl_res_int_d' : 256,
                   'resnet_out' : True, 
                   'out_std' : False, 
                   'graph_dropout' : 0.0, 
                   'resnet_d': 128, 
                   'OUT_DIM' : 1, # update
}

opt_params_base = {'amsgrad' : False, 
                   'lr' : 1e-4,
                   'weight_decay' : 1e-6, # None, # 
                   'scheduler_gamma' : 0.90, 
                   'eps' : 1e-8, 
                   'scheduler_step_size' : 100}


def params():
    for i in range(1):

        infile = td('graph_conv_many_nuc_pipeline.data.{}.{}.{}.{:d}.{:d}.mol_dict.pickle'.format(SPECT_SET, DATASET_NAME, 
                                                                                                  MAT_PROPS, tgt_max_n, 0))
        outfile = f"test_uncertain.{i}.out"
        
        yield infile, outfile, i


@files(params)
def train(infile, outfile, seed):

    np.random.seed(seed)

    d = pickle.load(open(infile, 'rb'))

    tgt_nucs = d['tgt_nucs']
    MAX_N = d['MAX_N']
    print("TGT_NUCS=", tgt_nucs)
    print("output is", outfile)
    USE_CUDA = True

    mu_scale = []
    std_scale = []
    for tn in tgt_nucs:
        for k, v in NUC_LOSS_SCALE.items():
            if k in tn:
                mu_scale.append(v)
        for k, v in NUC_STD_SCALE.items():
            if k in tn:
                std_scale.append(v)
    assert len(mu_scale) == len(tgt_nucs)
    assert len(std_scale) == len(tgt_nucs)
    print("NUC_LOSS_SCALE=", NUC_LOSS_SCALE)
    print("mu_scale=", mu_scale)
    print("std_scale=", std_scale)
    print("tgt_nucs=", tgt_nucs)

    ### Create datasets and data loaders

    BATCH_SIZE = 16

    dataset_hparams = graph_conv_many_nuc_util.DEFAULT_DATA_HPARAMS

    ds_train, ds_test = graph_conv_many_nuc_util.make_datasets({'filename' : infile}, 
                                                               dataset_hparams)
                                                               
    dl_train = torch.utils.data.DataLoader(ds_train, batch_size=BATCH_SIZE, 
                                           shuffle=True,pin_memory=True)
    dl_test = torch.utils.data.DataLoader(ds_test, batch_size=BATCH_SIZE, 
                                          shuffle=True,pin_memory=True)

    net_params = net_params_base.copy()
    opt_params = opt_params_base.copy()
    #net_params, opt_params = rand_params()

    net_params['g_feature_n'] = ds_test[0][1].shape[-1]
    net_params['OUT_DIM'] =  len(tgt_nucs)

    use_std = False # True ## FIXME where does this go? 
                  
    net = grmnets.GraphVertGRLModel(**net_params)
 
    net = move(net, USE_CUDA)

    for n, p in net.named_parameters():
        print(n, p.shape)
    loss_config = {'std_regularize' : 0.01, 
                   'mu_scale' : mu_scale, 
                   'std_scale' : std_scale}

    if use_std:
        std_regularize = loss_config['std_regularize']
        mu_scale = move(torch.Tensor(loss_config['mu_scale']), USE_CUDA)
        std_scale = move(torch.Tensor(loss_config['std_scale']), USE_CUDA)
        criterion = nets.NormUncertainLoss(mu_scale, 
                                           std_scale,
                                           std_regularize = loss_config['std_regularize'])
        validate_func = create_uncertain_validate_func(tgt_nucs)
    else:
        criterion = nets.MaskedMSELoss()
        validate_func = create_validate_func(tgt_nucs)


    optimizer = torch.optim.Adam(net.parameters(), lr=opt_params['lr'], 
                                 amsgrad=opt_params['amsgrad'], 
                                 eps=opt_params['eps'], 
                                 weight_decay=opt_params['weight_decay'])

    
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, 
                                                step_size=opt_params['scheduler_step_size'], 
                                                gamma=opt_params['scheduler_gamma'])

    MODEL_NAME = "{}.{:08d}".format(EXP_NAME,int(time.time() % 1e8))
    
    checkpoint_filename = os.path.join(CHECKPOINT_DIR, MODEL_NAME + ".{epoch_i:08d}")
    checkpoint_func = graph_conv_many_nuc_util.create_checkpoint_func(10, checkpoint_filename)
                        
    writer = SummaryWriter("{}/{}".format(TENSORBOARD_DIR, MODEL_NAME))

    metadata = {'dataset_hparams' : dataset_hparams, 
                 'net_params' : net_params, 
                 'opt_params' : opt_params, 
                'infile' : infile, 
                'tgt_nucs' : tgt_nucs, 
                'max_n' : MAX_N,
                'loss_params' : loss_config}

    json.dump(metadata, open(os.path.join(CHECKPOINT_DIR, MODEL_NAME + ".json"), 'w'), 
              indent=4)
    print(json.dumps(metadata, indent=4))
    print("checkpoint:", checkpoint_filename)

    pickle.dump(metadata, 
                open(os.path.join(CHECKPOINT_DIR, MODEL_NAME + ".meta"), 'wb'))

    graph_conv_many_nuc_util.generic_runner(net, optimizer, scheduler, criterion, 
                                            dl_train, dl_test, 
                                            MAX_EPOCHS=MAX_EPOCHS, 
                                            USE_CUDA=USE_CUDA, writer=writer, 
                                            validate_func= validate_func, 
                                            checkpoint_func= checkpoint_func)

    pickle.dump({'net_params' : net_params, 
                 'opt_params' : opt_params, 
                 'loss_params' : loss_config}, 
                open(outfile, 'wb'))

if __name__ == "__main__":
    pipeline_run([train])


