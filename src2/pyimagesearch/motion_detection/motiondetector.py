import numpy as np
import imutils
import cv2

import typing as t


class CVImage(np.ndarray):
    pass


class SingleMotionDetector:

    def __init__(self, accumWeight: float = 0.5) -> None:
        # store the accumulated weight factor
        self.accumWeight = accumWeight
        # initialize the background model
        self.bg: t.Optional[CVImage] = None

    def update(self, image: CVImage) -> None:
        # if the background model is None, initialize it
        if self.bg is None:
            self.bg = image.copy().astype("float")
            return None
        else:
            # update the background model by accumulating the weighted average
            cv2.accumulateWeighted(image, self.bg, self.accumWeight)

    def detect(self, image: CVImage, tVal: int = 25) -> t.Optional[t.Tuple[CVImage, t.Tuple[float, float, float, float]]]:
        """compute the absolute difference between the background model
        # and the image passed in, then threshold the delta image"""

        # Any pixel locations that have a difference > tVal: set to white, else: black
        if self.bg is None:
            # if bg is none, first delta should be image (all moved) or blank (no move?)
            self.update(image)
            self.detect(image)
            # delta = image.copy()
        else:
            delta = cv2.absdiff(self.bg.astype("uint8"), image)

        thresh = cv2.threshold(delta, tVal, 255, cv2.THRESH_BINARY)[1]

        # perform a series of erosions and dilations to remove small blobs
        eroded: CVImage = cv2.erode(thresh, None, iterations=2)
        dilated: CVImage = cv2.dilate(eroded, None, iterations=2)

        # find contours in the thresholded image and initialize the
        # minimum and maximum bounding box regions for motion
        cnts = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(cnts)
        (minX, minY) = (np.inf, np.inf)
        (maxX, maxY) = (-np.inf, -np.inf)

        # if no contours were found, return None
        if len(contours) == 0:
            return None
        # otherwise, loop over the contours
        else:
            for c in contours:
                # compute the bounding box of the contour and use it to
                # update the minimum and maximum bounding box regions
                (x, y, w, h) = cv2.boundingRect(c)
                (minX, minY) = (min(minX, x), min(minY, y))
                (maxX, maxY) = (max(maxX, x + w), max(maxY, y + h))
            # return a tuple of the thresholded image along with bounding box
            return (dilated, (minX, minY, maxX, maxY))
