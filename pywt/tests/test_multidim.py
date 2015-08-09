#!/usr/bin/env python

from __future__ import division, print_function, absolute_import

import numpy as np
from itertools import combinations
from numpy.testing import (run_module_suite, assert_allclose, assert_,
                           assert_raises, assert_equal)

import pywt


def test_dwtn_input():
    # Array-like must be accepted
    pywt.dwtn([1, 2, 3, 4], 'haar')
    # Others must not
    data = dict()
    assert_raises(TypeError, pywt.dwtn, data, 'haar')
    # Must be at least 1D
    assert_raises(ValueError, pywt.dwtn, 2, 'haar')


def test_3D_reconstruct():
    data = np.array([
        [[0, 4, 1, 5, 1, 4],
         [0, 5, 26, 3, 2, 1],
         [5, 8, 2, 33, 4, 9],
         [2, 5, 19, 4, 19, 1]],
        [[1, 5, 1, 2, 3, 4],
         [7, 12, 6, 52, 7, 8],
         [2, 12, 3, 52, 6, 8],
         [5, 2, 6, 78, 12, 2]]])

    wavelet = pywt.Wavelet('haar')
    for mode in pywt.MODES.modes:
        d = pywt.dwtn(data, wavelet, mode=mode)
        assert_allclose(data, pywt.idwtn(d, wavelet, mode=mode),
                        rtol=1e-13, atol=1e-13)


def test_stride():
    wavelet = pywt.Wavelet('haar')

    for dtype in ('float32', 'float64'):
        data = np.array([[0, 4, 1, 5, 1, 4],
                         [0, 5, 6, 3, 2, 1],
                         [2, 5, 19, 4, 19, 1]],
                        dtype=dtype)

        for mode in pywt.MODES.modes:
            expected = pywt.dwtn(data, wavelet)
            strided = np.ones((3, 12), dtype=data.dtype)
            strided[::-1, ::2] = data
            strided_dwtn = pywt.dwtn(strided[::-1, ::2], wavelet)
            for key in expected.keys():
                assert_allclose(strided_dwtn[key], expected[key])


def test_byte_offset():
    wavelet = pywt.Wavelet('haar')
    for dtype in ('float32', 'float64'):
        data = np.array([[0, 4, 1, 5, 1, 4],
                         [0, 5, 6, 3, 2, 1],
                         [2, 5, 19, 4, 19, 1]],
                        dtype=dtype)

        for mode in pywt.MODES.modes:
            expected = pywt.dwtn(data, wavelet)
            padded = np.ones((3, 6), dtype=np.dtype([('data', data.dtype),
                                                     ('pad', 'byte')]))
            padded[:] = data
            padded_dwtn = pywt.dwtn(padded['data'], wavelet)
            for key in expected.keys():
                assert_allclose(padded_dwtn[key], expected[key])


def test_idwtn_idwt2():
    data = np.array([
        [0, 4, 1, 5, 1, 4],
        [0, 5, 6, 3, 2, 1],
        [2, 5, 19, 4, 19, 1]])

    wavelet = pywt.Wavelet('haar')

    LL, (HL, LH, HH) = pywt.dwt2(data, wavelet)
    d = {'aa': LL, 'da': HL, 'ad': LH, 'dd': HH}

    for mode in pywt.MODES.modes:
        assert_allclose(pywt.idwt2((LL, (HL, LH, HH)), wavelet, mode=mode),
                        pywt.idwtn(d, wavelet, mode=mode),
                        rtol=1e-14, atol=1e-14)


def test_idwtn_missing():
    # Test to confirm missing data behave as zeroes
    data = np.array([
        [0, 4, 1, 5, 1, 4],
        [0, 5, 6, 3, 2, 1],
        [2, 5, 19, 4, 19, 1]])

    wavelet = pywt.Wavelet('haar')

    coefs = pywt.dwtn(data, wavelet)

    # No point removing zero, or all
    for num_missing in range(1, len(coefs)):
        for missing in combinations(coefs.keys(), num_missing):
            missing_coefs = coefs.copy()
            for key in missing:
                del missing_coefs[key]
            LL = missing_coefs.get('aa', None)
            HL = missing_coefs.get('da', None)
            LH = missing_coefs.get('ad', None)
            HH = missing_coefs.get('dd', None)

            assert_allclose(pywt.idwt2((LL, (HL, LH, HH)), wavelet),
                            pywt.idwtn(missing_coefs, 'haar'), atol=1e-15)


def test_ignore_invalid_keys():
    data = np.array([
        [0, 4, 1, 5, 1, 4],
        [0, 5, 6, 3, 2, 1],
        [2, 5, 19, 4, 19, 1]])

    wavelet = pywt.Wavelet('haar')

    LL, (HL, LH, HH) = pywt.dwt2(data, wavelet)
    d = {'aa': LL, 'da': HL, 'ad': LH, 'dd': HH,
         'foo': LH, 'a': HH}

    assert_allclose(pywt.idwt2((LL, (HL, LH, HH)), wavelet),
                    pywt.idwtn(d, wavelet), atol=1e-15)


def test_error_mismatched_size():
    data = np.array([
        [0, 4, 1, 5, 1, 4],
        [0, 5, 6, 3, 2, 1],
        [2, 5, 19, 4, 19, 1]])

    wavelet = pywt.Wavelet('haar')

    LL, (HL, LH, HH) = pywt.dwt2(data, wavelet)

    # Pass/fail depends on first element being shorter than remaining ones so
    # set 3/4 to an incorrect size to maximize chances. Order of dict items
    # is random so may not trigger on every test run. Dict is constructed
    # inside idwtn function so no use using an OrderedDict here.
    LL = LL[:, :-1]
    LH = LH[:, :-1]
    HH = HH[:, :-1]
    d = {'aa': LL, 'da': HL, 'ad': LH, 'dd': HH}

    assert_raises(ValueError, pywt.idwtn, d, wavelet)


def test_dwt2_idwt2_dtypes():
    # Check that float32 is preserved.  Other types get converted to float64.
    dtypes_in = [np.int8, np.float32, np.float64]
    dtypes_out = [np.float64, np.float32, np.float64]
    wavelet = pywt.Wavelet('haar')
    for dt_in, dt_out in zip(dtypes_in, dtypes_out):
        x = np.ones((4, 4), dtype=dt_in)
        errmsg = "wrong dtype returned for {0} input".format(dt_in)

        cA, (cH, cV, cD) = pywt.dwt2(x, wavelet)
        assert_(cA.dtype == cH.dtype == cV.dtype == cD.dtype,
                "dwt2: " + errmsg)

        x_roundtrip = pywt.idwt2((cA, (cH, cV, cD)), wavelet)
        assert_(x_roundtrip.dtype == dt_out, "idwt2: " + errmsg)


def test_dwtn_idwtn_dtypes():
    # Check that float32 is preserved.  Other types get converted to float64.
    dtypes_in = [np.int8, np.float32, np.float64]
    dtypes_out = [np.float64, np.float32, np.float64]
    wavelet = pywt.Wavelet('haar')
    for dt_in, dt_out in zip(dtypes_in, dtypes_out):
        x = np.ones((4, 4), dtype=dt_in)
        errmsg = "wrong dtype returned for {0} input".format(dt_in)

        coeffs = pywt.dwtn(x, wavelet)
        for k, v in coeffs.items():
            assert_(v.dtype == dt_out, "dwtn: " + errmsg)

        x_roundtrip = pywt.idwtn(coeffs, wavelet)
        assert_(x_roundtrip.dtype == dt_out, "idwtn: " + errmsg)


if __name__ == '__main__':
    run_module_suite()
