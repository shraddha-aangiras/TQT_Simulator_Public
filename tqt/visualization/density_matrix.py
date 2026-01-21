import matplotlib.pyplot as plt
import seaborn as sns
import qutip as qt
import numpy as np

cmap_uni = sns.color_palette("crest", as_cmap=True)
cmap_div = sns.diverging_palette(220, 20, as_cmap=True)


def density_matrix_heatmap(rho):
    """
    Plots a two-qubit density matrix as 2D heatmap, one for the real components and one for the imaginary

    Parameters
    ----------
    rho: a 4x4 complex numpy array representing the two-qubit density matrix

    Returns
    -------
    fig: figure handle
    axs: list of axes handles
    """
    if type(rho) is qt.Qobj:
        rho = rho.full()

    fig, axs = plt.subplots(nrows=1, ncols=2, figsize=[10, 4])

    kwargs = dict(vmin=-1, vmax=1, cmap=cmap_div, linewidths=0.5, square=True)
    axs[0].set(title="Real")
    axs[1].set(title="Imaginary")

    sns.heatmap(rho.real, ax=axs[0], **kwargs)
    sns.heatmap(rho.imag, ax=axs[1], **kwargs)

    return fig, axs


def density_matrix_bars(rho):
    """
    Plots a two-qubit density matrix as 3D bar plots, one for the real components and one for the imaginary

    Parameters
    ----------
    rho: a 4x4 complex numpy array representing the two-qubit density matrix

    Returns
    -------
    fig: figure handle
    axs: list of axes handles
    """

    def bar_plot(dz, ax, basis="HV"):
        N = dz.shape[0]
        X, Y = np.meshgrid(np.arange(N), np.arange(N))
        x, y = X.flatten() - 0.5, Y.flatten() - 0.5
        z = 1
        dx, dy = 0.8, 0.8
        dz = dz.flatten()
        max_height = 0.25  # get range of colorbars so we can normalize
        min_height = -0.25
        colors = cmap_div(dz.ravel() * 0.8, alpha=1 - dz.ravel())
        ax.bar3d(x, y, z, dx, dy, dz, color=colors)
        ax.set(zlim=[1 + min_height, 2 - max_height])

        if basis == "HV":
            ket = lambda s: r"$\vert " + str(s) + r" \rangle$"
            ax.set(xticks=[0, 1, 2, 3], yticks=[0, 1, 2, 3], zticklabels=[])
            ax.set_xticklabels([ket("HH"), ket("HV"), ket("VH"), ket("VV")], rotation=0)
            ax.set_yticklabels([ket("HH"), ket("HV"), ket("VH"), ket("VV")], rotation=0)
        return ax

    if type(rho) is qt.Qobj:
        rho = rho.full()

    # kwargs = dict(vmin=-1, vmax=1, cmap=cmap, linewidths=.5, square=True)

    fig = plt.figure()  # create a canvas, tell matplotlib it's 3d
    axs = [fig.add_subplot(1, 2, k, projection="3d") for k in range(1, 3)]

    dz = rho.real
    bar_plot(dz, ax=axs[0])
    axs[0].set(title="Real")

    dz = rho.imag
    bar_plot(dz, ax=axs[1])
    axs[1].set(title="Imaginary")

    return fig, axs


if __name__ == "__main__":
    from tqt.utils.constants import states

    state = (qt.ket2dm(states["phi+"]) + qt.ket2dm(states["psi+"])).unit()
    fig, ax = density_matrix_bars(state)
    fig, ax = density_matrix_heatmap(state)
    plt.show()
