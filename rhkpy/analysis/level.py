"""Image leveling: row alignment, plane subtraction, zero offset and stripe removal.

Ported from the spym project by Mirco Panighel
(https://github.com/rescipy-project/spym, MIT license). These functions are
part of the public rhkpy namespace (``rhkpy.align``, ``rhkpy.plane``,
``rhkpy.fixzero``, ``rhkpy.destripe``).
"""

import numpy as np
from scipy import ndimage


def fixzero(image, to_mean=False):
    '''Add a constant to the data, moving its minimum or its mean to zero.

    :param image: image data
    :type image: :py:mod:`numpy` array
    :param to_mean: move the mean to zero instead of the minimum, defaults to False
    :type to_mean: bool, optional

    :return: the shifted data
    :rtype: :py:mod:`numpy` array
    '''
    if to_mean:
        fixed = image - image.mean()
    else:
        fixed = image - image.min()

    return fixed


def destripe(image, min_length=20, hard_threshold=0.4, soft_threshold=0.2, sign='positive', rel_threshold=None):
    '''Find scan stripes and replace them with the average of the neighbouring lines.

    :param image: image data
    :type image: 2D :py:mod:`numpy` array
    :param min_length: only stripes at least this long (in pixels) are removed, defaults to 20
    :type min_length: int, optional
    :param hard_threshold: minimum difference from the neighbouring line to mark a stripe, in units of half the data range, defaults to 0.4
    :type hard_threshold: float, optional
    :param soft_threshold: values differing at least this much can extend a stripe, in units of half the data range, defaults to 0.2
    :type soft_threshold: float, optional
    :param sign: which stripes to mark: 'positive', 'negative' or 'both', defaults to 'positive'
    :type sign: str, optional
    :param rel_threshold: if set, replaces `hard_threshold` with this value times half the data range, defaults to None
    :type rel_threshold: float, optional

    :return: the destriped image and the boolean mask of the stripes
    :rtype: tuple of 2D :py:mod:`numpy` arrays
    '''
    # Normalize image
    rng = (image.max() - image.min()) / 2
    n_image = (image - image.mean())/rng

    # Calculate positive line differences
    d_pos = np.diff(n_image.clip(0, None), axis=0)
    np.clip(d_pos, 0, None, out=d_pos)
    diff_pos = np.empty(image.shape)
    diff_pos[0] = d_pos[0]
    diff_pos[1:] = d_pos

    # Calculate negative line differences
    d_neg = np.diff(n_image.clip(None, 0), axis=0)
    np.clip(d_neg, None, 0, out=d_neg)
    diff_neg = np.empty(image.shape)
    diff_neg[0] = d_neg[0]
    diff_neg[1:] = d_neg

    # Calculate physical threshold
    if rel_threshold:
        hard_threshold = rel_threshold*rng

    # Calculate masks for hard and soft thresholds
    m_hard_pos = False
    m_soft_pos = False
    m_hard_neg = False
    m_soft_neg = False
    if sign in ['positive', 'both']:
        m_hard_pos = diff_pos > hard_threshold
        m_soft_pos = diff_pos > soft_threshold
    if sign in ['negative', 'both']:
        m_hard_neg = diff_neg < -hard_threshold
        m_soft_neg = diff_neg < -soft_threshold

    # Opening (erosion+dilation) of the masks
    m_hard = ndimage.binary_opening(m_hard_pos+m_hard_neg, structure=np.ones((1, min_length), dtype=bool))
    m_soft = ndimage.binary_opening(m_soft_pos+m_soft_neg, structure=np.ones((1, 2*min_length), dtype=bool))

    # Addition of hard and soft mask
    mask = ndimage.binary_opening(m_soft+m_hard, structure=np.ones((1, min_length), dtype=bool))

    # Filter masked values
    filt = ndimage.uniform_filter(image, size=(3, 1))

    filtered = image*np.invert(mask) + filt*mask

    return filtered, mask


def plane(image):
    '''Corrects for image tilting by subtraction of a plane.

    :param image: image data
    :type image: 2D :py:mod:`numpy` array

    :return: flattened image ``planned`` and the subtracted background ``bkg``
    :rtype: tuple: (2D :py:mod:`numpy` array, 2D :py:mod:`numpy` array)

    :Example:

        .. code-block:: python

            import rhkpy

            topo = rhkpy.rhkdata('topography.sm4', loadraw = True)
            # plane-fit the forward scan of the raw topography
            flattened, background = rhkpy.plane(topo.image.topography.sel(scandir = 'forward').data)
    '''

    bkg_x = _poly_bkg(image.mean(axis=0), 1)
    bkg_y = _poly_bkg(image.mean(axis=1), 1)

    bkg_xx = np.apply_along_axis(_fill, 1, image, bkg_x)
    bkg_yy = np.apply_along_axis(_fill, 0, image, bkg_y)

    bkg = bkg_xx + bkg_yy
    planned = image - bkg

    return planned, bkg


def align(image, baseline='mean', axis=1, poly_degree=2):
    '''Align the rows (scan lines) of an image by subtracting a baseline from each.

    :param image: image data
    :type image: 2D :py:mod:`numpy` array
    :param baseline: how the baselines are estimated: 'mean', 'median' or 'poly', defaults to 'mean'
    :type baseline: str, optional
    :param axis: axis along which the baselines are calculated, defaults to 1
    :type axis: int, optional
    :param poly_degree: polynomial degree if ``baseline`` = 'poly', defaults to 2
    :type poly_degree: int, optional

    :return: corrected image ``aligned`` and the subtracted background ``bkg``
    :rtype: tuple: (2D :py:mod:`numpy` array, 2D :py:mod:`numpy` array)
    '''

    if baseline == 'mean':
        bkg = np.apply_along_axis(_mean_bkg, axis, image)
    elif baseline == 'median':
        bkg = np.apply_along_axis(_median_bkg, axis, image)
    elif baseline == 'poly':
        bkg = np.apply_along_axis(_poly_bkg, axis, image, poly_degree)

    aligned = image - bkg

    return aligned, bkg


def _mean_bkg(line):
    return np.full(line.shape[0], line.mean())


def _median_bkg(line):
    return np.full(line.shape[0], np.median(line))


def _poly_bkg(line, poly_degree):
    x = np.linspace(-.5, .5, line.shape[0])
    coefs = np.polyfit(x, line, poly_degree)
    return np.polyval(coefs, x)


def _fill(line, value):
    return value
