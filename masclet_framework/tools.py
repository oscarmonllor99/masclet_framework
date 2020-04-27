"""
MASCLET framework

Provides several functions to read MASCLET outputs and perform basic operations.
Also, serves as a bridge between MASCLET data and the yt package (v 3.5.1).

tools module
Contains several useful functions that other modules might need

Created by David Vallés
"""

#  Last update on 27/4/20 1:23

# GENERAL PURPOSE AND SPECIFIC LIBRARIES USED IN THIS MODULE

# numpy
import numpy as np


# from multiprocessing import Pool

# from masclet_framework import cosmo_tools, units

# from scipy import optimize


# FUNCTIONS DEFINED IN THIS MODULE

# SECTION: basic tools
def create_vector_levels(npatch):
    """
    Creates a vector containing the level for each patch. Nothing really important, just for ease

    Args:
        npatch: number of patches in each level, starting in l=0 (numpy vector of NLEVELS integers)

    Returns:
        numpy array containing the level for each patch

    """
    vector = [[0]] + [[i + 1] * x for (i, x) in enumerate(npatch[1:])]
    vector = [item for sublist in vector for item in sublist]
    return np.array(vector)


def clean_field(field, cr0amr, solapst, npatch, up_to_level=1000):
    """
    Receives a field (with its refinement patches) and, using the cr0amr and solapst variables, returns the field
    having "cleaned" for refinements and overlaps. The user can specify the level of refinement required. This last
    level will be cleaned of overlaps, but not of refinements!

    Args:
        field: field to be cleaned
        cr0amr: field containing the refinements of the grid (1: not refined; 0: refined)
        solapst: field containing the overlaps (1: keep; 0: not keep)
        npatch: number of patches in each level, starting in l=0 (numpy vector of NLEVELS integers)
        up_to_level: specify if only cleaning until certain level is desired

    Returns:
        "Clean" version of the field, with the same structure.

    """
    levels = create_vector_levels(npatch)
    up_to_level = min(up_to_level, levels.max())

    cleanfield = []
    if up_to_level == 0:
        cleanfield.append(field[0])
    else:
        cleanfield.append(field[0] * cr0amr[0])  # not overlap in l=0

    for level in range(1, up_to_level):
        for ipatch in range(sum(npatch[0:level]) + 1, sum(npatch[0:level + 1]) + 1):
            cleanfield.append(field[ipatch] * cr0amr[ipatch] * solapst[ipatch])

    # last level: no refinements
    for ipatch in range(sum(npatch[0:up_to_level]) + 1, sum(npatch[0:up_to_level + 1]) + 1):
        cleanfield.append(field[ipatch] * solapst[ipatch])

    return cleanfield


def diagonalize_ascending(matrix):
    """
    Given a squared matrix, finds its eigenvalues and eigenvectors, and returns both order by ascending order (smaller
    first). This function makes use of numpy.linalg.eig() function.

    Args:
        matrix: squared, diagonalizable matrx

    Returns:
        list of eigenvalues and list of their corresponding eigenvectors

    """
    matrix_eigenvalues, matrix_eigenvectors = np.linalg.eig(matrix)
    eigenvalues = []
    eigenvectors = []
    for eigenvalue in sorted(np.unique(matrix_eigenvalues)):
        for index in np.where(matrix_eigenvalues == eigenvalue)[0]:
            eigenvalues.append(eigenvalue)
            eigenvectors.append(matrix_eigenvectors[:, index])

    return eigenvalues, eigenvectors


# SECTION: grid geometry
def find_absolute_grid_position(ipatch, npatch, patchx, patchy, patchz, pare):
    """
    Given a patch in a certain iteration, finds the grid (natural) coordinates of its left corner.
    Written as a recursive function this time.

    Args:
        ipatch: number of the patch (in the given iteration)
        npatch: number of patches in each level, starting in l=0 (numpy vector of NLEVELS integers)
        patchx: vector containing the X-position of the leftmost corner of all the patches (numpy vector of integers)
        patchy: vector containing the Y-position of the leftmost corner of all the patches (numpy vector of integers)
        patchz: vector containing the Z-position of the leftmost corner of all the patches (numpy vector of integers)
        pare: vector containing the ipatch of each patch progenitor (numpy vector of integers)

    Returns:
        tuple with the patches left-corner NX, NY, NZ values

    """
    level = create_vector_levels(npatch)[ipatch]
    if ipatch < patchx.size:
        if level == 1:
            return patchx[ipatch], patchy[ipatch], patchz[ipatch]
        else:
            parevalues = find_absolute_grid_position(pare[ipatch], npatch, patchx, patchy, patchz, pare)
            return (patchx[ipatch] / 2 ** (level - 1) + parevalues[0],
                    patchy[ipatch] / 2 ** (level - 1) + parevalues[1],
                    patchz[ipatch] / 2 ** (level - 1) + parevalues[2])
    else:
        raise ValueError('Provide a valid patchnumber (ipatch)')


def find_absolute_real_position(ipatch, side, nmax, npatch, patchx, patchy, patchz, pare):
    """
    Given a patch in a certain iteration, finds the real coordinates of its left corner with no numerical error.
    This function depends on find_absolute_grid_position, which must be also loaded.

    Args:
        ipatch: number of the patch (in the given iteration) (int)
        side: side of the simulation box in the chosen units (typically Mpc or kpc) (float)
        nmax: number of cells along each directions at level l=0 (can be loaded from masclet_parameters; NMAX = NMAY =
        = NMAZ is assumed) (int)
        npatch: number of patches in each level, starting in l=0 (numpy vector of NLEVELS integers)
        patchx: vector containing the X-position of the leftmost corner of all the patches (numpy vector of integers)
        patchy: vector containing the Y-position of the leftmost corner of all the patches (numpy vector of integers)
        patchz: vector containing the Z-position of the leftmost corner of all the patches (numpy vector of integers)
        pare: vector containing the ipatch of each patch progenitor (numpy vector of integers)

    Returns:
    numpy array with the patches left corner X, Y and Z values (assuming box centered in 0; same units than SIDE)

    """
    return (np.asarray(
        find_absolute_grid_position(ipatch, npatch, patchx, patchy, patchz, pare)) - nmax / 2) * side / nmax


def patch_vertices(level, nx, ny, nz, rx, ry, rz, size, nmax):
    """
    Returns, for a given patch, the comoving coordinates of its 8 vertices.

    Args:
        level: refinement level of the given patch
        nx, ny, nz: extension of the patch (in cells at level n)
        rx, ry, rz: comoving coordinates of the center of the leftmost cell of the patch
        size: comoving box side (preferred length units)
        nmax: cells at base level

    Returns:
        List containing 8 tuples, each one containing the x, y, z coordinates of the vertex.

    """

    cellsize = size / nmax / 2 ** level

    leftmost_x = rx - cellsize
    leftmost_y = ry - cellsize
    leftmost_z = rz - cellsize

    vertices = []

    for i in range(2):
        for j in range(2):
            for k in range(2):
                x = leftmost_x + i * nx * cellsize
                y = leftmost_y + j * ny * cellsize
                z = leftmost_z + k * nz * cellsize

                vertices.append((x, y, z))

    return vertices


def patch_is_inside_sphere(R, clusrx, clusry, clusrz, level, nx, ny, nz, rx, ry, rz, size, nmax):
    """

    Args:
        R: radius of the considered sphere
        clusrx, clusry, clusrz: comoving coordinates of the center of the sphere
        level: refinement level of the given patch
        nx, ny, nz: extension of the patch (in cells at level n)
        rx, ry, rz: comoving coordinates of the center of the leftmost cell of the patch
        size: comoving box side (preferred length units)
        nmax: cells at base level

    Returns:
        Returns True if the patch should contain cells within a sphere of radius r of the (clusrx, clusry, clusrz)
        point; False otherwise.

    """
    isinside = False

    vertices = patch_vertices(level, nx, ny, nz, rx, ry, rz, size, nmax)
    xmin = vertices[0][0]
    ymin = vertices[0][1]
    zmin = vertices[0][2]
    xmax = vertices[-1][0]
    ymax = vertices[-1][1]
    zmax = vertices[-1][2]

    if xmin < clusrx < xmax and ymin < clusry < ymax and zmin < clusrz < zmax:
        return True

    cell_l0_size = size / nmax
    max_side = max([nx, ny, nz]) * cell_l0_size / 2 ** level
    upper_bound_squared = R ** 2 + max_side ** 2 / 4
    for vertex in vertices:
        distance_squared = (vertex[0] - clusrx) ** 2 + (vertex[1] - clusry) ** 2 + (vertex[2] - clusrz) ** 2
        if distance_squared <= upper_bound_squared:
            isinside = True
            break

    return isinside


def which_patches_inside_sphere(R, clusrx, clusry, clusrz, patchnx, patchny, patchnz, patchrx, patchry, patchrz, npatch,
                                size, nmax):
    """
    Finds which of the patches will contain cells within a radius r of a certain point (clusrx, clusry, clusrz) being
    its comoving coordinates.

    Args:
        R: radius of the considered sphere
        clusrx, clusry, clusrz: comoving coordinates of the center of the sphere
        patchnx, patchny, patchnz: x-extension of each patch (in level l cells) (and Y and Z)
        patchrx, patchry, patchrz: physical position of the center of each patch first ¡l-1! cell
        (and Y and Z)
        npatch: number of patches in each level, starting in l=0
        size: comoving size of the simulation box
        nmax: cells at base level

    Returns:
        List containing the ipatch of the patches which should contain cells inside the considered radius.

    """
    levels = create_vector_levels(npatch)
    which_ipatch = [0]
    for ipatch in range(1, len(patchnx)):
        if patch_is_inside_sphere(R, clusrx, clusry, clusrz, levels[ipatch], patchnx[ipatch], patchny[ipatch],
                                  patchnz[ipatch],
                                  patchrx[ipatch], patchry[ipatch], patchrz[ipatch], size, nmax):
            which_ipatch.append(ipatch)
    return which_ipatch


def patch_left_edge_comoving(rx, ry, rz, level, size, nmax):
    """
    Computes comoving coordinates of the left edge of a patch, given its rx, ry, rz.

    Args:
        rx, ry, rz: physical coordinate of the center of the leftmost parent cell (as read from patchrx, patchry, ...)
        level: level of the considered patch
        size: comoving side of the simulation box
        nmax: number of cells per dimension on the base level

    Returns:
        tuple containing the x, y, z physical coordinates of the patch left corner.
    """
    cellsize = size / nmax / 2 ** level
    x = rx - cellsize
    y = ry - cellsize
    z = rz - cellsize
    return x, y, z


def patch_left_edge_natural(rx, ry, rz, level, size, nmax):
    """
        Computes natural coordinates (0 being the left corner of the box, nmax being the right corner) of the left edge
        of a patch, given its rx, ry, rz.

        Args:
            rx, ry, rz: physical coordinate of the center of the leftmost parent cell (as read from patchrx, patchry,
                    ...)
            level: level of the considered patch
            size: comoving side of the simulation box
            nmax: number of cells per dimension on the base level

        Returns:
            tuple containing the x, y, z physical coordinates of the patch left corner.
        """
    x, y, z = patch_left_edge_comoving(rx, ry, rz, level, size, nmax)

    xg = x * nmax / size + nmax / 2
    yg = y * nmax / size + nmax / 2
    zg = z * nmax / size + nmax / 2

    # avoid numerical error
    xg = round(xg * 2 ** (level - 1)) / 2 ** (level - 1)
    yg = round(yg * 2 ** (level - 1)) / 2 ** (level - 1)
    zg = round(zg * 2 ** (level - 1)) / 2 ** (level - 1)

    return xg, yg, zg


def patch_is_inside_box(box_limits, level, nx, ny, nz, rx, ry, rz, size, nmax):
    """
    See "Returns:"

    Args:
        box_limits: a tuple in the form (xmin, xmax, ymin, ymax, zmin, zmax)
        level: refinement level of the given patch
        nx, ny, nz: extension of the patch (in cells at level n)
        rx, ry, rz: comoving coordinates of the center of the leftmost cell of the patch
        size: comoving box side (preferred length units)
        nmax: cells at base level

    Returns:
        Returns True if the patch should contain cells within a sphere of radius r of the (clusrx, clusry, clusrz)
        point; False otherwise.

    """
    vertices = patch_vertices(level, nx, ny, nz, rx, ry, rz, size, nmax)
    pxmin = vertices[0][0]
    pymin = vertices[0][1]
    pzmin = vertices[0][2]
    pxmax = vertices[-1][0]
    pymax = vertices[-1][1]
    pzmax = vertices[-1][2]

    bxmin = box_limits[0]
    bxmax = box_limits[1]
    bymin = box_limits[2]
    bymax = box_limits[3]
    bzmin = box_limits[4]
    bzmax = box_limits[5]

    overlap_x = (pxmin <= bxmax) and (bxmin <= pxmax)
    overlap_y = (pymin <= bymax) and (bymin <= pymax)
    overlap_z = (pzmin <= bzmax) and (bzmin <= pzmax)

    return overlap_x and overlap_y and overlap_z


def which_patches_inside_box(box_limits, patchnx, patchny, patchnz, patchrx, patchry, patchrz, npatch, size, nmax):
    """
    Finds which of the patches will contain cells within a box of defined vertices.

    Args:
        box_limits: a tuple in the form (xmin, xmax, ymin, ymax, zmin, zmax)
        patchnx, patchny, patchnz: x-extension of each patch (in level l cells) (and Y and Z)
        patchrx, patchry, patchrz: physical position of the center of each patch first ¡l-1! cell
        (and Y and Z)
        npatch: number of patches in each level, starting in l=0
        size: comoving size of the simulation box
        nmax: cells at base level

    Returns:
        List containing the ipatch of the patches which should contain cells inside the considered radius.

    """
    levels = create_vector_levels(npatch)
    which_ipatch = [0]
    for ipatch in range(1, len(patchnx)):
        if patch_is_inside_box(box_limits, levels[ipatch], patchnx[ipatch], patchny[ipatch], patchnz[ipatch],
                               patchrx[ipatch], patchry[ipatch], patchrz[ipatch], size, nmax):
            which_ipatch.append(ipatch)
    return which_ipatch


# SECTION: uniform grids
def uniform_grid_zoom(field, box_limits, up_to_level, npatch, patchnx, patchny, patchnz, patchrx, patchry, patchrz,
                      size, nmax, verbose=False):
    """
    Builds a uniform grid, zooming on a box specified by box_limits, at level up_to_level, containing the most refined
    data at each region.

    Args:
        field: field to be computed at the uniform grid. Must be already cleaned from refinements and overlaps (check
                clean_field() function).
        box_limits: a tuple in the form (xmin, xmax, ymin, ymax, zmin, zmax). Limits should correspond to l=0 cell
                    boundaries
        up_to_level: level up to which the fine grid wants to be obtained
        npatch: number of patches in each level, starting in l=0 (numpy vector of NLEVELS integers)
        patchnx, patchny, patchnz: x-extension of each patch (in level l cells) (and Y and Z)
        patchrx, patchry, patchrz: physical position of the center of each patch first ¡l-1! cell
                                   (and Y and Z)
        size: comoving side of the simulation box
        nmax: cells at base level
        verbose: if True, prints the patch being opened at a time

    Returns:
        Uniform grid as described

    """
    uniform_cellsize = size / nmax / 2 ** up_to_level

    bxmin = box_limits[0]
    bxmax = box_limits[1]
    bymin = box_limits[2]
    bymax = box_limits[3]
    bzmin = box_limits[4]
    bzmax = box_limits[5]

    # BASE GRID
    uniform_size_x = int(round(nmax * (bxmax - bxmin) / size * 2 ** up_to_level))
    uniform_size_y = int(round(nmax * (bymax - bymin) / size * 2 ** up_to_level))
    uniform_size_z = int(round(nmax * (bzmax - bzmin) / size * 2 ** up_to_level))
    uniform = np.zeros((uniform_size_x, uniform_size_y, uniform_size_z))

    reduction = 2 ** up_to_level

    starting_x = (bxmin + size / 2) * nmax / size
    # ending_x = (bxmax + size/2) * nmax / size
    starting_y = (bymin + size / 2) * nmax / size
    # ending_y = (bymax + size / 2) * nmax / size
    starting_z = (bzmin + size / 2) * nmax / size
    # ending_z = (bzmax + size / 2) * nmax / size

    for i in range(uniform_size_x):
        for j in range(uniform_size_y):
            for k in range(uniform_size_z):
                I = int(starting_x + i / reduction)
                J = int(starting_y + j / reduction)
                K = int(starting_z + k / reduction)
                uniform[i, j, k] = field[0][I, J, K]

    # REFINEMENT LEVELS

    levels = create_vector_levels(npatch)
    # up_to_level_patches = npatch[0:up_to_level + 1].sum()
    relevantpatches = which_patches_inside_box(box_limits, patchnx, patchny, patchnz, patchrx, patchry, patchrz, npatch,
                                               size, nmax)[1:]  # we ignore the 0-th relevant patch (patch 0, base
    # level). By construction, the 0th element is always the l=0 patch.
    relevantpatches = [i for i in relevantpatches if i <= npatch[0:up_to_level + 1].sum()]

    for ipatch in relevantpatches:
        if verbose:
            print('Covering patch {}'.format(ipatch))

        reduction = 2 ** (up_to_level - levels[ipatch])
        ipatch_cellsize = uniform_cellsize * reduction
        round_digits = max(int(np.log10(reduction)) + 1, 3)  # avoids tiny numerical errors which generated void regions

        vertices = patch_vertices(levels[ipatch], patchnx[ipatch], patchny[ipatch], patchnz[ipatch], patchrx[ipatch],
                                  patchry[ipatch], patchrz[ipatch], size, nmax)
        pxmin = vertices[0][0]
        pymin = vertices[0][1]
        pzmin = vertices[0][2]
        pxmax = vertices[-1][0]
        pymax = vertices[-1][1]
        pzmax = vertices[-1][2]

        # fix left corners
        if pxmin <= bxmin:
            imin = 0
            Imin = round((bxmin - pxmin) / ipatch_cellsize, round_digits)
        else:
            imin = int(round((pxmin - bxmin) / uniform_cellsize))
            Imin = 0

        if pymin <= bymin:
            jmin = 0
            Jmin = round((bymin - pymin) / ipatch_cellsize, round_digits)
        else:
            jmin = int(round((pymin - bymin) / uniform_cellsize))
            Jmin = 0

        if pzmin <= bzmin:
            kmin = 0
            Kmin = round((bzmin - pzmin) / ipatch_cellsize, round_digits)
        else:
            kmin = int(round((pzmin - bzmin) / uniform_cellsize))
            Kmin = 0

        # fix right corners
        if bxmax <= pxmax:
            imax = uniform_size_x
        else:
            # imax = int(round(patchnx[ipatch]*reduction))
            Imax = patchnx[ipatch] - 1
            imax = int(round(imin + (Imax - Imin + 1) * reduction))

        if bymax <= pymax:
            jmax = uniform_size_y
        else:
            # jmax = int(round(patchny[ipatch]*reduction))
            Jmax = patchny[ipatch] - 1
            jmax = int(round(jmin + (Jmax - Jmin + 1) * reduction))

        if bzmax <= pzmax:
            kmax = uniform_size_z
        else:
            # kmax = int(round(patchnz[ipatch]*reduction))
            Kmax = patchnz[ipatch] - 1
            kmax = int(round(kmin + (Kmax - Kmin + 1) * reduction))

        for i in range(imin, imax):
            for j in range(jmin, jmax):
                for k in range(kmin, kmax):
                    I = int(Imin + (i - imin) / reduction)
                    J = int(Jmin + (j - jmin) / reduction)
                    K = int(Kmin + (k - kmin) / reduction)
                    uniform[i, j, k] += field[ipatch][I, J, K]

    return uniform


def uniform_grid(field, up_to_level, npatch, patchnx, patchny, patchnz, patchrx, patchry, patchrz, size, nmax,
                 verbose=False):
    """
    Builds a uniform grid at level up_to_level, containing the most refined data at each region.

    Args:
        field: field to be computed at the uniform grid. Must be already cleaned from refinements and overlaps (check
                clean_field() function).
        up_to_level: level up to which the fine grid wants to be obtained
        npatch: number of patches in each level, starting in l=0 (numpy vector of NLEVELS integers)
        patchnx, patchny, patchnz: x-extension of each patch (in level l cells) (and Y and Z)
        patchrx, patchry, patchrz: physical position of the center of each patch first ¡l-1! cell
        (and Y and Z)
        size: comoving side of the simulation box
        nmax: cells at base level
        verbose: if True, prints the patch being opened at a time

    Returns:
        Uniform grid as described

    """
    box_limits = [-size / 2, size / 2, -size / 2, size / 2, -size / 2, size / 2]
    return uniform_grid_zoom(field, box_limits, up_to_level, npatch, patchnx, patchny, patchnz, patchrx, patchry,
                             patchrz, size, nmax, verbose=verbose)


def uniform_grid_zoom_several(fields, box_limits, up_to_level, npatch, patchnx, patchny, patchnz, patchrx, patchry,
                              patchrz, size, nmax, verbose=False):
    """
    Builds a uniform grid, zooming on a box specified by box_limits, at level up_to_level, containing the most refined
    data at each region.

    Args:
        fields: fields to be computed at the uniform grid. Must be already cleaned from refinements and overlaps (check
                clean_field() function). To be passed as a list of fields.
        box_limits: a tuple in the form (xmin, xmax, ymin, ymax, zmin, zmax). Limits should correspond to l=0 cell
                    boundaries
        up_to_level: level up to which the fine grid wants to be obtained
        npatch: number of patches in each level, starting in l=0 (numpy vector of NLEVELS integers)
        patchnx, patchny, patchnz: x-extension of each patch (in level l cells) (and Y and Z)
        patchrx, patchry, patchrz: physical position of the center of each patch first ¡l-1! cell
                                   (and Y and Z)
        size: comoving side of the simulation box
        nmax: cells at base level
        verbose: if True, prints the patch being opened at a time

    Returns:
        Uniform grid as described

    """
    numfields = len(fields)

    uniform_cellsize = size / nmax / 2 ** up_to_level

    bxmin = box_limits[0]
    bxmax = box_limits[1]
    bymin = box_limits[2]
    bymax = box_limits[3]
    bzmin = box_limits[4]
    bzmax = box_limits[5]

    # BASE GRID
    uniform_size_x = int(round(nmax * (bxmax - bxmin) / size * 2 ** up_to_level))
    uniform_size_y = int(round(nmax * (bymax - bymin) / size * 2 ** up_to_level))
    uniform_size_z = int(round(nmax * (bzmax - bzmin) / size * 2 ** up_to_level))
    uniforms = [np.zeros((uniform_size_x, uniform_size_y, uniform_size_z)) for _ in range(numfields)]

    reduction = 2 ** up_to_level

    starting_x = (bxmin + size / 2) * nmax / size
    # ending_x = (bxmax + size/2) * nmax / size
    starting_y = (bymin + size / 2) * nmax / size
    # ending_y = (bymax + size / 2) * nmax / size
    starting_z = (bzmin + size / 2) * nmax / size
    # ending_z = (bzmax + size / 2) * nmax / size

    for i in range(uniform_size_x):
        for j in range(uniform_size_y):
            for k in range(uniform_size_z):
                I = int(starting_x + i / reduction)
                J = int(starting_y + j / reduction)
                K = int(starting_z + k / reduction)
                for ifield in range(numfields):
                    uniforms[ifield][i, j, k] = fields[ifield][0][I, J, K]

    # REFINEMENT LEVELS

    levels = create_vector_levels(npatch)
    # up_to_level_patches = npatch[0:up_to_level + 1].sum()
    relevantpatches = which_patches_inside_box(box_limits, patchnx, patchny, patchnz, patchrx, patchry, patchrz, npatch,
                                               size, nmax)[1:]  # we ignore the 0-th relevant patch (patch 0, base
    # level). By construction, the 0th element is always the l=0 patch.
    relevantpatches = [i for i in relevantpatches if i <= npatch[0:up_to_level + 1].sum()]

    for ipatch in relevantpatches:
        if verbose:
            print('Covering patch {}'.format(ipatch))

        reduction = 2 ** (up_to_level - levels[ipatch])
        ipatch_cellsize = uniform_cellsize * reduction
        round_digits = max(int(np.log10(reduction)) + 1, 3)  # avoids tiny numerical errors which generated void regions

        vertices = patch_vertices(levels[ipatch], patchnx[ipatch], patchny[ipatch], patchnz[ipatch], patchrx[ipatch],
                                  patchry[ipatch], patchrz[ipatch], size, nmax)
        pxmin = vertices[0][0]
        pymin = vertices[0][1]
        pzmin = vertices[0][2]
        pxmax = vertices[-1][0]
        pymax = vertices[-1][1]
        pzmax = vertices[-1][2]

        # fix left corners
        if pxmin <= bxmin:
            imin = 0
            Imin = round((bxmin - pxmin) / ipatch_cellsize, round_digits)
        else:
            imin = int(round((pxmin - bxmin) / uniform_cellsize))
            Imin = 0

        if pymin <= bymin:
            jmin = 0
            Jmin = round((bymin - pymin) / ipatch_cellsize, round_digits)
        else:
            jmin = int(round((pymin - bymin) / uniform_cellsize))
            Jmin = 0

        if pzmin <= bzmin:
            kmin = 0
            Kmin = round((bzmin - pzmin) / ipatch_cellsize, round_digits)
        else:
            kmin = int(round((pzmin - bzmin) / uniform_cellsize))
            Kmin = 0

        # fix right corners
        if bxmax <= pxmax:
            imax = uniform_size_x
        else:
            # imax = int(round(patchnx[ipatch]*reduction))
            Imax = patchnx[ipatch] - 1
            imax = int(round(imin + (Imax - Imin + 1) * reduction))

        if bymax <= pymax:
            jmax = uniform_size_y
        else:
            # jmax = int(round(patchny[ipatch]*reduction))
            Jmax = patchny[ipatch] - 1
            jmax = int(round(jmin + (Jmax - Jmin + 1) * reduction))

        if bzmax <= pzmax:
            kmax = uniform_size_z
        else:
            # kmax = int(round(patchnz[ipatch]*reduction))
            Kmax = patchnz[ipatch] - 1
            kmax = int(round(kmin + (Kmax - Kmin + 1) * reduction))

        for i in range(imin, imax):
            for j in range(jmin, jmax):
                for k in range(kmin, kmax):
                    I = int(Imin + (i - imin) / reduction)
                    J = int(Jmin + (j - jmin) / reduction)
                    K = int(Kmin + (k - kmin) / reduction)
                    for ifield in range(numfields):
                        uniforms[ifield][i, j, k] += fields[ifield][ipatch][I, J, K]

    return tuple(uniforms)


def mask_gas_clumps(shell_mask, gas_density, fcut=3.5, mode='zhuravleva13'):
    """
    Given a radial shell mask and the gas density field, this routine yields a new mask where the substructures
     (clumps) are indicated.

    Args:
        shell_mask: bool field, where cells belonging to the shell are marked as "True"
        gas_density: gas density field (normalization should be unimportant)
        fcut: cells with log gas density at more than fcut standard deviations from the median log gas density are
            removed. Defaults to 3.5.
        mode: specifies the algorithm applied. Defaults to 'zhuravleva13'

    Returns:
        A mask containing the cells which must be eliminated.

    """
    # densities inside the shell
    masked_density = [d * m for d, m in zip(gas_density, shell_mask)]

    if mode == 'zhuravleva13':
        # median and std of the logdensities in the shell
        logdensities = np.log10(np.concatenate([d[d > 0] for d in masked_density]))
        median = np.median(logdensities)
        sigma = np.std(logdensities)

        # upper bound according to Zhuravleva13
        upper_bound = 10 ** (median + fcut * sigma)

        mask_substructures = [m > upper_bound for m in masked_density]

    return mask_substructures


def mask_gas_filaments(shell_mask, gas_density, gas_vr, fcut_low=1, fcut_high=3.5, mode='lau15'):
    """
    Given a radial shell mask, a gas density field and a gas radial (clustercentric) velocity field,
    this routine yields a new mask where the filamentary substructures are indicated.

    Args:
        shell_mask: bool field, where cells belonging to the shell are marked as "True"
        gas_density: gas density field (normalization should be unimportant)
        gas_vr: gas radial velocity field
        fcut_low, fcut_high: infalling cells with log gas density between [fcut_low, fcut_high] above the median are
                            marked as filamentary structures
        mode: specifies the algorithm applied. Defaults to 'lau15'

    Returns:
        A mask containing the cells which must be eliminated.

    """
    # densities inside the shell
    masked_density = [d * m for d, m in zip(gas_density, shell_mask)]

    if mode == 'lau15':
        # median and std of the logdensities in the shell
        logdensities = np.log10(np.concatenate([d[d > 0] for d in masked_density]))
        median = np.median(logdensities)
        sigma = np.std(logdensities)

        # lower and upper bounds according to Lau15
        lower_bound = 10 ** (median + fcut_low * sigma)
        upper_bound = 10 ** (median + fcut_high * sigma)

        mask_substructures = [(m > lower_bound) * (m < upper_bound) * (vr < 0) for m, vr in zip(masked_density, gas_vr)]

    return mask_substructures


def remove_gas_substructures(gas_density, mask_substructures, shell_mask, refill='median'):
    """
    Given a radial shell mask and the gas density field, this routine yields the density where the substructures
        (clumps or filaments) have been substracted and replaced by some value.

    Args:
        gas_density: gas density field (normalization should be unimportant)
        mask_substructures: mask containing the identified clumps or filaments for this radial bin
                            (see mask_gas_clumps() and mask_gas_filaments() functions in this module)
        shell_mask: bool field, where cells belonging to the shell are marked as "True"
        refill: clumps are refilled with the 'median' or 'mean' density, according to the specified parameter

    Returns:
        The gas density field, where the clumps have been removed

    """
    masked_density = [d * m for d, m in zip(gas_density, shell_mask)]
    bindensities = np.concatenate([d[d > 0] for d in masked_density])

    if refill == 'median':
        refill_value = np.median(bindensities)
    elif refill == 'mean':
        refill_value = np.mean(bindensities)

    for ipatch in range(len(gas_density)):
        gas_density[ipatch][mask_substructures[ipatch]] = refill_value

    return gas_density
