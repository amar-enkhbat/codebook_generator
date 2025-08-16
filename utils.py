import time
import numpy as np
import logging
import glob

def load_codebook(filepath: str) -> np.ndarray:
    codebook = np.load(filepath).T
    return codebook

def load_codebooks_block_1(path: str='./codebooks/condition_1') -> np.ndarray:
    """Block 1 aka Henrich's codebook"""
    codebooks = []
    fpaths = sorted(glob.glob(f'{path}/codebook_obj_*.npy'))
    for fpath in fpaths:
        codebook = load_codebook(fpath)
        codebooks.append(codebook)
    codebooks = np.array(codebooks)
    logging.info(f'Codebooks loaded. shape: {np.array(codebooks).shape}')
    return codebooks
    
def load_codebooks_block_2(path: str='./codebooks/condition_2') -> np.ndarray:
    """Block 2 aka custom codebook"""
    codebooks = []
    fpaths = sorted(glob.glob(f'{path}/codebook_obj_*.npy'))
    for fpath in fpaths:
        codebook = load_codebook(fpath)
        codebooks.append(codebook)
    codebooks = np.array(codebooks)
    logging.info(f'Codebooks loaded. shape: {np.array(codebooks).shape}')
    return codebooks

def load_codebooks_block_3(fpath: str='./codebooks/condition_3/mseq_61_shift_8.npy', n_reps: int=12, n_objs: int=8) -> np.ndarray:
    """Block 2 aka custom cVEP"""
    codebooks = []
    codebook = load_codebook(fpath)
    # Select 8 codebooks
    codebook = np.vstack([codebook] * n_reps)
    codebooks = np.array([codebook] * n_objs)
    logging.info(f'Codebooks loaded. shape: {np.array(codebooks).shape}')
    return codebooks

def perf_sleep(t: float) -> None:
    t1 = time.perf_counter() + t
    while time.perf_counter() <= t1:
        pass

def random_wait(low: float, high: float):
    """Do nothing for low to high seconds. Duration is random. Between low and high values"""
    val = round(np.random.uniform(low, high), 2)
    perf_sleep(val)