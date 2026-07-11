"""Bresenham's line algorithm, ported from the exploratory `psudocode_usage`
branch's hardcoded xl/yl/xr/yr line drawer into the generalized pseudocode
DSL. Inputs are seeded into the interpreter's env before running, instead of
being string-formatted into the source.
"""

NAME = "Bresenham Line"

DEFAULT_INPUTS = {"xl": 2, "yl": 2, "xr": 24, "yr": 11}

SOURCE = """\
dx = abs(xr - xl)
dy = -abs(yr - yl)
sx = 1
if xl > xr:
    sx = -1
sy = 1
if yl > yr:
    sy = -1
err = dx + dy
x = xl
y = yl
done = 0
while done == 0:
    PlotPixel(x, y)
    if x == xr and y == yr:
        done = 1
    else:
        e2 = 2 * err
        if e2 >= dy and x != xr:
            err = err + dy
            x = x + sx
        if e2 <= dx and y != yr:
            err = err + dx
            y = y + sy
"""
