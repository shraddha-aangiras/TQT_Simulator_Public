from tqt.visualization.density_matrix import (
    density_matrix_heatmap,
    density_matrix_bars,
)

# custom style references: https://github.com/hosilva/mplstyle
import matplotlib.pyplot as plt
import seaborn as sns
from cycler import cycler
from itertools import cycle
import pathlib

path = pathlib.Path(__file__).parent.resolve()

# import a common matplotlib style guide, for a consistent figure look
plt.style.use(path.joinpath("computermodernstyle.mplstyle"))

# Waseda colors (a relatively nice color scheme that is easily accessible to use)
wred = "#920527"
wblk = "#252427"
wblu = "#094C90"
wgra = "#757A7D"
wgrn = "#81990B"
wbrw = "#714D2A"
wyel = "#FDD003"
worg = "#D08B16"
wcya = "#02A0DA"
colors = [wred, wblu, wblk, wgra, wgrn, wbrw, wyel, worg, wcya]
plt.rc(
    "axes",
    prop_cycle=(
        cycler("color", [wred, wblu, wblk, wgra, wgrn, wbrw, wyel, worg, wcya])
    ),
)
