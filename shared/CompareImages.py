import os
import numpy as np
from PIL import Image

# Sprite exports that show the same art are no longer identical byte for byte. 
# Ultimately this is a low impact feature so best effort to deduplicate is good enough.
#
# The game reuses the same drawing under several atlas region names (Eimi's animations 00 and 02 both
# show the face art, as 00_default and 02_respond). 
# Android assets hid this with lower resolution; PC spritesheets started deviating when compared per-pixel.
#
# Considering abandoning this entirely if attempts to differentiate duplicates vs minimal-changes art still fail.
#
# Four scenarios:
#   - a few stray pixels land far off. Same art stored twice reaches a difference of 53 on a single
#     pixel (Toki (School Uniform) 00 and 01), and so do the subtlest changes found: Mine (Idol) S2
#     05's mouth tip and Cruise Operations Staff 05's mouth peak at 53 and 55.
#   - a genuine change can be tiny in area. Those mouths cover 8 to 10 pixels above HOTSPOT_LEVEL,
#     the same art stored twice up to 12, its difference being scattered speckle along edges.
#   - a blush added over the cheeks is soft and spread out: every pixel moves only a little (Mika
#     (Swimsuit) 26 against 04 peaks at 33), so it slips under both limits above. However it shifts
#     a whole area the *same* way, darker and redder, where speckle and sub-pixel
#     edge shifts alternate lighter and darker from one pixel to the next. Averaging the signed
#     difference over TINT_WINDOW pixels cancels the speckle and keeps the blush: the blushes land
#     at 12.5, the faint shine on Nagisa (Swimsuit) 17's sunglasses at 4.8, same art up to 4.6.
#   - a line drawn elsewhere passes all three when it is faint, as Niko 12's eyebrows behind the
#     hair. An edge shifted by less than a pixel still comes close to some value within one pixel
#     of it in the other image, a moved line does not: Niko 02 and 12 have 128 pixels further than
#     MISMATCH_LEVEL from all of them, same art up to 49, as resampled thin lines lose some darkness.
#
# An image counts as the same when all four hold: 
# - nothing differs by more than TOLERANCE, 
# - no more than HOTSPOT_LIMIT pixels differ by more than HOTSPOT_LEVEL, 
# - no TINT_WINDOW patch has shifted colour by more than TINT_LIMIT on average, 
# - no more than MISMATCH_LIMIT pixels lie further than MISMATCH_LEVEL from every value within one pixel of them in the other image.

TOLERANCE = 48
HOTSPOT_LEVEL = 32
HOTSPOT_LIMIT = 6
TINT_WINDOW = 16
TINT_LIMIT = 3
MISMATCH_LEVEL = 16
MISMATCH_LIMIT = 24


def premultiplied(image):
    """Float channels with colour premultiplied by alpha, so whatever colour sits under fully
    transparent pixels cannot count."""
    channels = image.astype(np.float32)
    if channels.ndim == 2: return channels[..., None]
    if channels.shape[-1] == 4: channels[..., :3] = channels[..., :3] * channels[..., 3:] / 255
    return channels


def largest_tint(image1, image2, window = TINT_WINDOW):
    """Largest average colour shift over any window x window patch, with the sign kept so that noise
    which goes both ways cancels."""
    difference = premultiplied(image1) - premultiplied(image2)

    largest = 0.0
    for c in range(min(difference.shape[-1], 3)): #colour, alpha is in the premultiplied colour
        signed = difference[..., c]
        if min(signed.shape) < window:
            continue
        # window x window means of the whole image at once, from an integral image
        total = np.pad(signed, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        sums = total[window:, window:] - total[:-window, window:] - total[window:, :-window] + total[:-window, :-window]
        largest = max(largest, float(np.abs(sums).max()) / (window * window))
    return largest


def mismatched_pixels(image1, image2, level = MISMATCH_LEVEL):
    """Pixels further than level from every value within one pixel of them in the other image, either way"""
    differs = image1 != image2
    if differs.ndim > 2: differs = differs.any(axis = -1)
    ys, xs = np.nonzero(differs)
    if len(ys) == 0: return 0
    # only the box around the differing pixels can mismatch, elsewhere a pixel finds its own value
    box = (slice(max(ys.min() - 1, 0), ys.max() + 2), slice(max(xs.min() - 1, 0), xs.max() + 2))
    a, b = premultiplied(image1[box]), premultiplied(image2[box])

    mismatched = np.zeros(a.shape[:2], bool)
    for pixels, other in ((a, b), (b, a)):
        padded = np.pad(other, ((1, 1), (1, 1), (0, 0)), mode = 'edge')
        near = np.stack([padded[y:y + other.shape[0], x:x + other.shape[1]] for y in range(3) for x in range(3)])
        mismatched |= ((near.min(axis = 0) - pixels > level) | (pixels - near.max(axis = 0) > level)).any(axis = -1)
    return int(mismatched.sum())


def identical_images(image1, image2, tolerance = TOLERANCE, hotspot_limit = HOTSPOT_LIMIT, tint_limit = TINT_LIMIT, mismatch_limit = MISMATCH_LIMIT):
    try:
        # Check if the shape of the images is the same
        if image1.shape != image2.shape:
            #print(f"Images have different dimensions.")
            return False

        # Compare pixel values
        if np.array_equal(image1, image2):
            #print(f"Images have IDENTICAL pixels.")
            return True

        if tolerance:
            # per channel difference, kept in uint8 so a large image costs no extra memory
            difference = np.maximum(image1, image2) - np.minimum(image1, image2)
            # hotspots are counted per pixel, not per channel, or one pixel counts up to four times
            hotspots = difference.max(axis = -1) if difference.ndim > 2 else difference
            if difference.max() <= tolerance and (hotspots > HOTSPOT_LEVEL).sum() <= hotspot_limit:
                # the dearer checks last, and only for pairs that already look like the same art
                if tint_limit is None or largest_tint(image1, image2) <= tint_limit:
                    if mismatch_limit is None or mismatched_pixels(image1, image2) <= mismatch_limit:
                        #print(f"Images differ only as the same art stored twice does.")
                        return True

        #print(f"Images have different pixels.")
    except Exception as e:
        print(f"Error: {e}")

    return False



def compare_images(files, tolerance = TOLERANCE, hotspot_limit = HOTSPOT_LIMIT):
    #duplicate_list = {}
    duplicate_map = {}

    for path in files.keys():
        fileset = files[path]
        data = []
        #duplicate_list[path] = []
        duplicate_map[path] = {}
        for file in fileset:
            data.append(np.array(Image.open(os.path.join(path, file))))

        for index,file in enumerate(fileset):
            # Duplicates only ever point at an original: a file an earlier original took is neither
            # compared as one nor taken again. Matching within tolerance is not transitive, so a file
            # that resembles only a duplicate stays in the gallery rather than hiding behind it.
            if file in duplicate_map[path]: continue
            for i in range(index+1,len(fileset)):
                if fileset[i] not in duplicate_map[path] and identical_images(data[index], data[i], tolerance, hotspot_limit):
                    #print(f"{fileset[i]} is a duplicate of {fileset[index]}")
                    #duplicate_list[path].append(fileset[i])
                    duplicate_map[path][fileset[i]] = fileset[index]

    #print(duplicate_list)
    #print(duplicate_map)
    return duplicate_map



def deduplicate_list(files:list, tolerance = TOLERANCE, hotspot_limit = HOTSPOT_LIMIT):
    duplicate_map = {}
    data = []

    files = list(set(files))

    for file in files:
        if not os.path.isfile(file):
            raise FileNotFoundError(f"File not found: {file}")
        data.append(np.array(Image.open(file)))

    for index,file in enumerate(files):
        for i in range(index+1,len(files)):
            if files[i] not in duplicate_map and identical_images(data[index], data[i], tolerance, hotspot_limit):
                print(f"{files[i]} is a duplicate of {files[index]}")
                duplicate_map[files[i]] = files[index]
                files[i] = files[index]
    return duplicate_map
