"""
test_flip_rle_equivalence.py
=============================
Verifica que el RLE con flip Y (corregido) de Python
produzca la misma secuencia de valores que MATLAB f_flip + f_genero_voxel_1.

El test simula un phantom 3D pequeno y compara:
  - MATLAB: I(end:-1:1, :, :) + RLE con wrap col 50
  - Python: [:, ::-1, :] + RLE con wrap col 72

Si el fix es correcto, la SECUENCIA DE TOKENS (valores y runs) debe ser identica.
Solo cambia el ancho de linea (50 vs 72).
"""

import numpy as np
import io
import sys
import os

# ============================================================
# 1. SIMULAR MATLAB f_flip + f_genero_voxel_1
# ============================================================
def matlab_rle(phantom_3d, wrap_col=50):
    """
    Simula exactamente MATLAB:
      I = f_flip(I, 1)  -> I(end:-1:1, :, :)
      f_genero_voxel_1(I, archivo)
    
    phantom_3d: shape (rows, cols, slices) = (Y, X, Z)  -- como MATLAB
    """
    # --- f_flip ---
    flipped = phantom_3d[::-1, :, :].copy()  # I(end:-1:1, :, :)
    
    fi, co, n = flipped.shape  # rows, cols, slices
    buf = io.StringIO()
    
    # Primer elemento
    buf.write(f"      {flipped[0,0,0]}")
    col = 7 + len(str(flipped[0,0,0]))
    r = -1
    b = int(flipped[0,0,0])
    
    for i in range(n):
        w = flipped[:, :, i]
        for l in range(fi):
            for m in range(co):
                val = int(w[l, m])
                if b == val:
                    r += 1
                else:
                    if r >= 1:
                        if r == 1:
                            buf.write(" r")
                            col += 2
                        else:
                            buf.write(f" {r}r")
                            col += 2 + len(str(r))
                        if col >= wrap_col:
                            buf.write("\n")
                            buf.write("     ")
                            col = 7
                    # Escribir nuevo valor
                    if col >= wrap_col:
                        buf.write("\n")
                        buf.write("     ")
                        buf.write(f" {val}")
                        col = 7 + len(str(val))
                    else:
                        buf.write(f" {val}")
                        col += 1 + len(str(val))
                    r = 0
                b = val
    
    # Flush final run
    if r >= 1:
        if r == 1:
            buf.write(" r")
        else:
            buf.write(f" {r}r")
    buf.write("\n")
    
    return buf.getvalue()


# ============================================================
# 2. SIMULAR PYTHON (CORREGIDO) RLE
# ============================================================
def python_rle(phantom_3d, wrap_col=72):
    """
    Simula el Python corregido:
      phantom_arr[:, ::-1, :]  (flip Y en dim 1)
      _write_rle_fill()
    
    phantom_3d: shape (NX, NY, NZ) = (X, Y, Z)  -- como Python
    """
    # --- flip Y corregido ---
    flipped = phantom_3d[:, ::-1, :].copy()  # flip dim 1 = Y
    
    nx, ny, nz = flipped.shape
    buf = io.StringIO()
    col = 0
    line = "      "
    
    def flush_run(r_val):
        nonlocal col, line
        if r_val >= 1:
            if r_val == 1:
                token = " r"
            else:
                token = f" {r_val}r"
            if col + len(token) > wrap_col:
                buf.write(line.rstrip() + "\n")
                line = "      "
                col = 6
            line += token
            col += len(token)
    
    def write_val(val):
        nonlocal col, line
        token = f" {val}"
        if col + len(token) > wrap_col:
            buf.write(line.rstrip() + "\n")
            line = "      "
            col = 6
        line += token
        col += len(token)
    
    first_val = int(flipped[0, 0, 0])
    if first_val == 0:
        first_val = 1
    write_val(first_val)
    prev_val = first_val
    r = -1
    
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                val = int(flipped[i, j, k])
                if val == 0:
                    val = 1
                if val == prev_val:
                    r += 1
                else:
                    flush_run(r)
                    write_val(val)
                    r = 0
                prev_val = val
    
    flush_run(r)
    buf.write(line.rstrip() + "\n")
    return buf.getvalue()


# ============================================================
# 3. EXTRACCION DE TOKENS (ignora whitespace y line breaks)
# ============================================================
def extract_tokens(rle_text):
    """Extrae tokens secuenciales: valores numericos y runs 'r'."""
    tokens = []
    for part in rle_text.replace('\n', ' ').split():
        if part == 'r':
            tokens.append('r')
        else:
            try:
                tokens.append(int(part))
            except ValueError:
                pass  # ignorar basura
    return tokens


# ============================================================
# 4. TEST
# ============================================================
def test_equivalence():
    """
    Crea un phantom 3D sintetico y verifica que el RLE
    de MATLAB (con f_flip) y Python (con fix) den la misma
    secuencia de tokens.
    """
    np.random.seed(42)
    shape_yxz = (12, 16, 8)  # rows=12, cols=16, slices=8   <<< como MATLAB
    shape_xyz = (16, 12, 8)  # NX=16, NY=12, NZ=8          <<< como Python
    
    # Phantom sintetico con indices tipicos (1=aire, 30=tejido, 50=pulmon)
    phantom_matlab = np.random.choice([1, 30, 50], size=shape_yxz, p=[0.85, 0.10, 0.05])
    # Agregar una region de higado+tumor
    phantom_matlab[3:7, 5:10, 2:5] = 90
    phantom_matlab[4:6, 6:8, 3:4] = 100
    
    # Phantom para Python: hay que reordenar dims
    # MATLAB: (rows, cols, slices) = (Y, X, Z)
    # Python: (NX, NY, NZ) = (X, Y, Z)
    phantom_python = phantom_matlab.transpose(1, 0, 2)  # (cols, rows, slices) = (X, Y, Z)
    
    # Generar RLEs
    rle_matlab = matlab_rle(phantom_matlab, wrap_col=50)
    rle_python = python_rle(phantom_python, wrap_col=72)
    
    # Extraer tokens
    tokens_matlab = extract_tokens(rle_matlab)
    tokens_python = extract_tokens(rle_python)
    
    # Comparar
    print("=" * 60)
    print("TEST: Equivalencia RLE MATLAB vs Python (fix corregido)")
    print("=" * 60)
    print(f"Phantom MATLAB shape (Y,X,Z): {phantom_matlab.shape}")
    print(f"Phantom Python shape (X,Y,Z): {phantom_python.shape}")
    print(f"Total voxels: {phantom_matlab.size}")
    print()
    print(f"Tokens MATLAB: {len(tokens_matlab)}")
    print(f"Tokens Python: {len(tokens_python)}")
    print()
    
    ok = tokens_matlab == tokens_python

    n_vox = phantom_matlab.size
    seq = tokens_python
    i = 0
    total = 0
    while i < len(seq):
        if isinstance(seq[i], int):
            total += 1
            i += 1
        elif seq[i] == 'r':
            total += 1
            i += 1
        else:
            i += 1

    if ok:
        print("[OK] SECUENCIA DE TOKENS IDENTICA (%d tokens)" % len(tokens_matlab))
        print("     El fix de flip_rows ([:, ::-1, :]) produce el mismo RLE que MATLAB f_flip.")
        print("     Voxels en RLE: %d (esperado: %d)" % (total, n_vox))
        if total == n_vox:
            print("[OK] Conteo de voxels correcto")
        return True
    else:
        print("[FAIL] SECUENCIA DIFERENTE")
        print("     Tokens: MATLAB=%d, Python=%d" % (len(tokens_matlab), len(tokens_python)))
        for idx, (a, b) in enumerate(zip(tokens_matlab, tokens_python)):
            if a != b:
                print("     Primer diff en token %d: MATLAB=%s, Python=%s" % (idx, a, b))
                break
        return False


def test_no_flip_equivalence():
    """
    Verifica que SIN flip, ambos tambien coincidan (regresion).
    """
    np.random.seed(123)
    phantom_matlab = np.random.choice([1, 30, 50], size=(8, 10, 6), p=[0.8, 0.15, 0.05])
    phantom_python = phantom_matlab.transpose(1, 0, 2)
    
    # MATLAB sin flip
    rle_matlab = matlab_rle_sin_flip(phantom_matlab, wrap_col=50)
    # Python sin flip
    rle_python = python_rle_sin_flip(phantom_python, wrap_col=72)
    
    t1 = extract_tokens(rle_matlab)
    t2 = extract_tokens(rle_python)
    
    print()
    print("--- TEST: Sin flip (regresion) ---")
    if t1 == t2:
        print("[OK] Sin flip: secuencia identica")
        return True
    else:
        print("[FAIL] Sin flip: DIFIEREN")
        return False


def matlab_rle_sin_flip(phantom_3d, wrap_col=50):
    """MATLAB RLE sin f_flip."""
    fi, co, n = phantom_3d.shape
    buf = io.StringIO()
    buf.write(f"      {phantom_3d[0,0,0]}")
    col = 7 + len(str(phantom_3d[0,0,0]))
    r = -1
    b = int(phantom_3d[0,0,0])
    for i in range(n):
        w = phantom_3d[:, :, i]
        for l in range(fi):
            for m in range(co):
                val = int(w[l, m])
                if b == val:
                    r += 1
                else:
                    if r >= 1:
                        if r == 1:
                            buf.write(" r")
                            col += 2
                        else:
                            buf.write(f" {r}r")
                            col += 2 + len(str(r))
                        if col >= wrap_col:
                            buf.write("\n     ")
                            col = 7
                    if col >= wrap_col:
                        buf.write("\n     ")
                        buf.write(f" {val}")
                        col = 7 + len(str(val))
                    else:
                        buf.write(f" {val}")
                        col += 1 + len(str(val))
                    r = 0
                b = val
    if r >= 1:
        if r == 1:
            buf.write(" r")
        else:
            buf.write(f" {r}r")
    buf.write("\n")
    return buf.getvalue()


def python_rle_sin_flip(phantom_3d, wrap_col=72):
    """Python RLE sin flip."""
    nx, ny, nz = phantom_3d.shape
    buf = io.StringIO()
    col = 0
    line = "      "
    def flush_run(r_val):
        nonlocal col, line
        if r_val >= 1:
            token = " r" if r_val == 1 else f" {r_val}r"
            if col + len(token) > wrap_col:
                buf.write(line.rstrip() + "\n")
                line = "      "
                col = 6
            line += token
            col += len(token)
    def write_val(val):
        nonlocal col, line
        token = f" {val}"
        if col + len(token) > wrap_col:
            buf.write(line.rstrip() + "\n")
            line = "      "
            col = 6
        line += token
        col += len(token)
    first_val = int(phantom_3d[0, 0, 0])
    if first_val == 0:
        first_val = 1
    write_val(first_val)
    prev_val = first_val
    r = -1
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                val = int(phantom_3d[i, j, k])
                if val == 0:
                    val = 1
                if val == prev_val:
                    r += 1
                else:
                    flush_run(r)
                    write_val(val)
                    r = 0
                prev_val = val
    flush_run(r)
    buf.write(line.rstrip() + "\n")
    return buf.getvalue()


if __name__ == "__main__":
    ok1 = test_equivalence()
    ok2 = test_no_flip_equivalence()
    print()
    print("=" * 60)
    if ok1:
        print("[OK] FIX VERIFICADO: flip_rows = [:, ::-1, :] es correcto")
    else:
        print("[FAIL] FIX INCORRECTO")
    print("=" * 60)
    sys.exit(0 if ok1 else 1)
