import os
import numpy as np
from PIL import Image

# Sprite exports that show the same art are no longer identical byte for byte. 
# Ultimately this is a low impact feature so best effort to deduplicate is good enough.
#
# The game reuses the same drawing under several atlas region names (Eimi's animations 00 and 02 both
# show the face art, as 00_default and 02_respond). 
# The Android spritesheets hid this with lower resolution; PC spritesheets started deviating bytewise.
#
# Three scenarios:
#   - a few stray pixels land far off. Pairs that are plainly the same art reach a difference of 48
#     on a single pixel, so a limit on the largest difference alone has to sit above that, and the
#     subtlest genuine change found - a mouth drawn as a dot instead of a line - peaks at only 72.
#   - a genuine change can be tiny in area. That mouth covers 21 pixels above HOTSPOT_LEVEL, while
#     the same art stored twice never exceeded 11, its difference being scattered speckle along
#     edges rather than a solid patch.
#   - a blush added over the cheeks is soft and spread out: every pixel moves only a little (Mika
#     (Swimsuit) 26 against 04 peaks at 33), so it slips under both limits above. However it shifts
#     a whole area the *same* way, darker and redder, where speckle and sub-pixel
#     edge shifts alternate lighter and darker from one pixel to the next. Averaging the signed
#     difference over TINT_WINDOW pixels cancels the speckle and keeps the blush: same art stays
#     under 3.5, the blushes land at 12.5.
#
# So an image counts as the same when all three hold: nothing differs by more than TOLERANCE, no
# more than HOTSPOT_LIMIT pixels differ by more than HOTSPOT_LEVEL, and no TINT_WINDOW patch has
# shifted colour by more than TINT_LIMIT on average.
#
# The *share* of differing pixels is no use here: expressions differ in well under 1% of pixels,
# because only the face changes.
TOLERANCE = 56
HOTSPOT_LEVEL = 32
HOTSPOT_LIMIT = 12
TINT_WINDOW = 16
TINT_LIMIT = 6


def largest_tint(image1, image2, window = TINT_WINDOW):
    """Largest average colour shift over any window x window patch, with the sign kept so that noise
    which goes both ways cancels. Colour is premultiplied by alpha, so whatever colour sits under
    fully transparent pixels cannot count."""
    a = image1.astype(np.float32)
    b = image2.astype(np.float32)
    if a.ndim == 2:
        channels = (a - b,)
    elif a.shape[-1] == 4:
        channels = [a[..., c] * a[..., 3] / 255 - b[..., c] * b[..., 3] / 255 for c in range(3)]
    else:
        channels = [a[..., c] - b[..., c] for c in range(a.shape[-1])]

    largest = 0.0
    for signed in channels:
        if min(signed.shape) < window:
            continue
        # window x window means of the whole image at once, from an integral image
        total = np.pad(signed, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        sums = total[window:, window:] - total[:-window, window:] - total[window:, :-window] + total[:-window, :-window]
        largest = max(largest, float(np.abs(sums).max()) / (window * window))
    return largest


def identical_images(image1, image2, tolerance = TOLERANCE, hotspot_limit = HOTSPOT_LIMIT, tint_limit = TINT_LIMIT):
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
                # the dearest check last, and only for pairs that already look like the same art
                if tint_limit is None or largest_tint(image1, image2) <= tint_limit:
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
