import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import random
from tqdm import tqdm
from scipy.signal import convolve2d
from scipy.signal import max_len_seq
import numpy as np


random.seed(42)
np.random.seed(42)

def gen_row(n_objs: int, prev_rows: np.ndarray, n_highlights: int, n_tries: int=1000) -> np.ndarray:
    # Add a row with minimal horizontal distance
    used_idc = []
    for prev_row in prev_rows:
        used_idc += np.where(prev_row == 1)[0].tolist()
    if len(used_idc) == n_objs:
        return np.ones(n_objs) * 99
    
    idc = np.arange(n_objs)
    idc = np.setdiff1d(idc, used_idc)
    for _ in range(n_tries):
        new_idc = np.sort(np.random.choice(idc, size=n_highlights, replace=False))
        idc_diffs = np.abs(np.diff(new_idc))
        row = np.zeros(n_objs)
        row[new_idc] = 1
        if 1 not in idc_diffs:    
            break
        # if i == n_tries - 1:
        #     print('Warning: couldnt find horizontally spaced row!')
    return row



def gen_codebook(init_codebook: np.ndarray, n_objs, n_obj_highlights, n_off_intervals, n_min_highlights):
    assert n_off_intervals < n_objs // n_obj_highlights
    codebook = init_codebook
    while True:
        if n_off_intervals == 0:
            prev_rows = np.zeros((0, n_objs))
        else:
            prev_rows = codebook[-n_off_intervals:].copy()
        new_row = gen_row(n_objs, prev_rows, n_obj_highlights)
        if 99 not in new_row:
            codebook = np.vstack((codebook, new_row))
        if codebook[init_codebook.shape[0]:].sum(axis=0).min() == n_min_highlights:
            break
        
    codebook = codebook[1:]
    codebook = [i for i in codebook.tolist() if i != [2] * n_objs]
    codebook = np.array(codebook)
    return codebook

def exist_spatial_neighbors(codebook):
    for i in range(codebook.shape[0]):
        for j in range(codebook.shape[1] - 1):
            if codebook[i, j:j+2].dot(np.array([1, 1])) == 2:
                return True
    return False

def compute_diag_neighbors(codebook: np.ndarray, kernel_size=(3, 3)) -> int:
    kernel_1 = np.zeros(kernel_size)
    np.fill_diagonal(kernel_1, 1)
    kernel_2 = np.zeros(kernel_size)
    np.fill_diagonal(kernel_2, 1)
    kernel_2 = np.flip(kernel_2, axis=1)

    conved_1 = convolve2d(codebook, kernel_1, mode='same')
    conved_2 = convolve2d(codebook, kernel_2, mode='same')
    
    vals_1, cnts_1 = np.unique(conved_1, return_counts=True)
    vals_2, cnts_2 = np.unique(conved_2, return_counts=True)
    
    n_matches = 0
    
    if kernel_size[0] not in vals_1 and kernel_size[0] not in vals_2:
        return n_matches
    else:
        return (cnts_1[vals_1 == kernel_size[0]].sum() + cnts_2[vals_2 == kernel_size[0]].sum()).item()

def generate_single_trial(n_reps=12) -> np.ndarray:
    best_codebooks = None
    best_diag_val = np.inf
    init_codebook = np.zeros((1, 8))
    
    for _ in tqdm(range(10000)):
        codebooks = []
        init_codebook = gen_codebook(
            init_codebook = init_codebook,
            n_objs=8, n_obj_highlights=2, n_off_intervals=3, n_min_highlights=1
        )
        for _ in range(n_reps):
            while True:
                codebook = gen_codebook(
                    init_codebook = np.zeros((1, 8)),
                    n_objs=8, n_obj_highlights=2, n_off_intervals=3, n_min_highlights=1
                )
                prev_idc = np.where(init_codebook[-1] == 1)[0]
                if codebook[0, prev_idc[0]] == 0 and codebook[0, prev_idc[1]] == 0:
                    if not exist_spatial_neighbors(codebook):
                        break
                
            codebooks.append(codebook)
            init_codebook = codebook

        codebooks = np.vstack(codebooks).T
        
        diag_val = compute_diag_neighbors(codebooks, kernel_size=(3, 3))
        if diag_val < best_diag_val:
            best_codebooks = codebooks
            best_diag_val = diag_val
            if diag_val == 0:
                break
    print('Lest diag neighbors:', best_diag_val)
    return best_codebooks


def main():
    # Condition 1
    for i in range(8):
        codebook = np.repeat(np.eye(8), 12, axis=1)
        idc = np.random.permutation(np.arange(8)) # randomly shift rows
        codebook = codebook[idc]

        # Save stimulus as image
        plt.figure(figsize=(10, 7))
        plt.imshow(codebook)
        plt.tight_layout()
        plt.savefig(f'./images/codebook_condition_1/codebook_obj_{i}.png', format='png')
        plt.clf()
        plt.cla()
        plt.close()

        # Save stimulus as npy file
        np.save(f'./codebooks/condition_1/codebook_obj_{i}.npy', codebook)

    # Condition 2
    for i in range(8):
        trial_stim = generate_single_trial()
        
        # Save stimulus as image
        plt.figure(figsize=(10, 7))
        plt.imshow(trial_stim)
        plt.tight_layout()
        plt.savefig(f'./images/condition_2/codebook_obj_{i}.png', format='png')
        plt.clf()
        plt.cla()
        plt.close()
        
        # Save stimulus as npy file
        np.save(f'./codebooks/condition_2/codebook_obj_{i}.npy', trial_stim)


main()