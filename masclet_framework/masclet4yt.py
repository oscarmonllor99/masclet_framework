#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MASCLET framework

Provides several functions to read MASCLET outputs and perform basic operations.
Also, serves as a bridge between MASCLET data and the yt package (v 3.5.1).

masclet4yt module
Aims to serve as a user-friendly link between masclet software and the yt
package

David Vallés, 2019
v0.1.0, 30/06/2019
"""
#numpy
import numpy as np

#masclet_framework
from src.masclet_framework import parameters, read_masclet, tools
        
def yt4masclet_load_grids(it,path='',digits=5,verbose=False):
    '''
    This function creates a list of dictionaries containing the information requiered for yt's load_amr_grids
    to build the grid structure of a simulations performed by MASCLET.
    
    PARAMETERS:
    it: iteration number
    path: path of the folder containing the grids file. Don't assign it if it is in the same folder as the script
    digits: no. of digits of iteration number (defaults to 5)
    
    
    verbose: print detailed information (mainly used for debugging)
    
    RETURNS:
    - grid_data: dictionary containing left_edge, right_edge, level and dimensions (num of cells) of each patch
    
    '''
    NMAX, NMAY, NMAZ, NLEVELS, NAMRX, NAMRY, NAMRZ, SIZE = parameters.read_parameters(loadNPALEV = False)
    IRR, T, NL, MAP, ZETA, NPATCH, NPART, PATCHNX, PATCHNY, PATCHNZ, PATCHX, PATCHY, PATCHZ, PARE = read_masclet.read_grids(it,path=path,readpatchposition=False)
    
    grid_data = []
    #l=0 (whole box)
    grid_data.append(dict(left_edge=[-SIZE/2,-SIZE/2,-SIZE/2],
                     right_edge=[SIZE/2,SIZE/2,SIZE/2],
                     level=0,
                     dimensions=[NMAX,NMAY,NMAZ]))
    
    LEVELS = tools.create_vector_levels(NPATCH)
    left = np.array([tools.find_absolute_real_position(i, SIZE, NMAX, NPATCH,PATCHX,PATCHY,PATCHZ,PARE) for i in range(1,LEVELS.size)])
    left = np.vstack([[-SIZE/2,-SIZE/2,-SIZE/2],left])
    right = left + np.array([PATCHNX/2**LEVELS, PATCHNY/2**LEVELS, PATCHNZ/2**LEVELS]).transpose()[:,:]*SIZE/NMAX
    
    for i in range(1,LEVELS.size):
        grid_data.append(dict(left_edge=left[i,:].tolist(),
                         right_edge=right[i,:].tolist(),
                         level = LEVELS[i],
                         dimensions = [PATCHNX[i], PATCHNY[i], PATCHNZ[i]]))
        
    bbox = np.array([[-SIZE/2, SIZE/2], [-SIZE/2, SIZE/2], [-SIZE/2, SIZE/2]])
        
    return grid_data, bbox


def yt4masclet_load_newfield(grid_data,fieldname,fieldl0,field_refined):
    '''
    This function adds a new field to the yt dataset, once created with yt4masclet_load_grids().
    fieldname specifies the name of the field. Then, fieldl0 (base level) and field_refined have
    to be given, as outputted by readclus, readcldm functions.
    
    PARAMETERS:
    - grid_data: dataset [list of dictionaries] where the new field wants to be added
    - fieldname: name of the new field, preferrably as specified in yt's docs
    - fieldl0: NMAXxNMAYxNMAZ matriz with the values of the field at l=0
    - field_refined: values of the field in each refinement level, as conventionally outputted 
    (list of arrays, being the first one 0)
    '''
    grid_data[0][fieldname] = fieldl0
    for g in range(1,len(grid_data)):
        try:
            grid_data[g][fieldname] = field_refined[g]
        except IndexError: #field not provided for this patch
            grid_data[g][fieldname] = np.zeros(grid_data[g]['dimensions'])
    return grid_data