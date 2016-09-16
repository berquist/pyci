#!/bin/python3
import scipy as sp
import scipy.linalg as spla
import scipy.sparse.linalg as splinalg
import numpy as np
from functools import reduce
import pyscf
import itertools
import h5py
from pyscf import gto, scf, ao2mo, fci
import pyscf.tools as pt
import copy
import matplotlib.pyplot as plt
from utils import *
#############
# INPUT
#############
np.set_printoptions(precision=4,suppress=True)
# Molecule Definition
mol = gto.M(
    atom = [['O', (0.000000000000,  -0.143225816552,   0.000000000000)],
            ['H', (1.638036840407,   1.136548822547,  -0.000000000000)],
            ['H', (-1.638036840407,   1.136548822547,  -0.000000000000)]],
    basis = 'STO-3G',
    verbose = 1,
    unit='b',
    symmetry=True
)
#Number of eigenvalues desired
printroots=4
#############
# INITIALIZE
#############
Na,Nb = mol.nelec #nelec is a tuple with (N_alpha, N_beta)
nao=mol.nao_nr()
myhf = scf.RHF(mol)
E = myhf.kernel()
mo_coefficients = myhf.mo_coeff
h1e = reduce(np.dot, (mo_coefficients.T, myhf.get_hcore(), mo_coefficients))
eri = ao2mo.kernel(mol, mo_coefficients)
num_orbs=2*nao
num_occ = mol.nelectron
num_virt = num_orbs - num_occ
fulldetlist_sets=gen_dets_sets(nao,Na,Nb)
ndets=len(fulldetlist_sets)
full_hamiltonian = construct_hamiltonian(ndets,fulldetlist_sets,h1e,eri)

cdets = 50
tdets = 100
E_old = 0
convergence = 1e-10
#why are there only 8 electrons?
coredetlist_sets = [(frozenset([1,2,3,4]),frozenset([1,2,3,4]))]
C = {(frozenset([1,2,3,4]),frozenset([1,2,3,4])):1.0}
coredetlist_sets=gen_dets_sets_truncated(nao,coredetlist_sets)
print(np.shape(coredetlist_sets))
ndets = np.shape(coredetlist_sets)[0]
print("Hartree-Fock Energy: ", E)
print("")
while(np.abs(E - E_old) > convergence):
    print("Core Dets: ",cdets)
    print("Excitation Dets: ",ndets)
    print("Target Dets: ",tdets)
    #step 1
    indices = []
    for i in coredetlist_sets:
        indices.extend(np.where(fulldetlist_sets == i))
    core_ham = get_smaller_hamiltonian(full_hamiltonian,indices)
    #STOPPING HERE FOR NOW BECAUSE I HAVE GROUP MEETING
    A = {}
    for i in range(ndets):
        temp = 0.0
        for j in range(cdets):
            if i!=j:
                try:
                    temp += core_ham[i,j]*C[coredetlist_sets[j]]
                except:
                    pass
                    #print(coredetlist_sets[i], " not in")
        temp /= core_ham[i,i] - E
        try:
            A[coredetlist_sets[i]] = temp
        except:
            pass
            #print(coredetlist_sets[i], " already in")
    print(A[(frozenset([0,1,2,3,4]),frozenset([0,1,2,3,4]))])
    exit()
    #step 2
    targetdetlist_sets = []
    for i in sorted(A, key=A.get, reverse=True)[0:tdets]:
        targetdetlist_sets.append(i)
    hrow = []
    hcol = []
    hval = []
    #step 3
    target_ham=construct_hamiltonian(tdets,targetdetlist_sets,h1e,eri)
    eig_vals,eig_vecs = sp.sparse.linalg.eigsh(target_ham,k=2*printroots)
    eig_vals_sorted = np.sort(eig_vals)[:printroots] + mol.energy_nuc()
    E_old = E
    E = eig_vals_sorted[0]
    print("Iteration Energy: ", E)
    #step 4
    amplitudes = eig_vecs[:,np.argsort(eig_vals)[0]]
    coredetlist_sets = []
    for i in np.argsort(np.abs(amplitudes))[::-1][0:cdets]:
        coredetlist_sets.append(targetdetlist_sets[i])
    C = {}
    for i,j in zip(coredetlist_sets,np.argsort(np.abs(amplitudes))[::-1][0:cdets]):
        C[i] = j
    coredetlist_sets=gen_dets_sets_truncated(nao,Na,Nb,coredetlist_sets)
    ndets = np.shape(coredetlist_sets)[0]
    print("")


eig_vals_gamess = [-75.0129802245,
                   -74.7364625517,
                   -74.6886742417,
                   -74.6531877287]

cisolver = fci.FCI(mol, mo_coefficients)
efci = cisolver.kernel(nroots=printroots)[0] + mol.energy_nuc()
print("first {:} PYCI eigvals vs FCI PYSCF eigvals vs FCI GAMESS eigvals".format(printroots))
for i,j,k in zip(eig_vals_sorted, efci, eig_vals_gamess):
    print(i,j,k)
