"""
Two-qubit quantum state tomography code using the MLE method.
"""

import qutip as qt
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize

from tqt.utils.io import IO
import tqt.utils.constants as constants


def two_qubit_state_tomography(
    io=None, data=None, filename=None, target=None, resample=False, verbose=False
):
    """
    State tomography function using the maximum likelihood method.

    This follows the method as outlined in
        Daniel James, et al. "Measurement of qubits" Phys. Rev. A, 64, 052312 (2001)
    Some variables follow the mathematical notation in this paper, but not all

    The experimental data can either be passed in as a path to the saved data (requires an IO object and filename) or
    by passing in the data (as a pd.Dataframe) directly.

    For this to work, the measurement label attached to each finite-count photon count measurement must be a valid
    state that is in tqt.utils.constants.states (e.g., H, V, D, A, L, R, etc.)

    target: str or Qobj representing the target qubit state

    Input:
        io: an IO class instance that will handle all the loading of the data (should be initialized to the target folder)
        data:
        filename: absolute path to the coincidence counts for each measurement

        resample: if True, will redraw the coincidence count from a Poissonian distribution, useful for bootstrapping
    Output:
        rho_opt: maximum likelihood quantum state
    """
    # load the text file which contains the projection measurements and associated coincidence counts
    if data is None and filename is not None:
        data = io.load_dataframe(filename)
    elif data is None and filename is None:
        raise AssertionError(
            "Please provide the filename to the data or the data object directly."
        )

    # Creates a list of the projection measurement operators (matrices) that correspond to each measurement
    projection_operators = []
    coincidence_counts = []
    for index, measurement_k in data.iterrows():
        # create the pure state and associated operator for the measurement corresponding to this row in the data
        pure_state = qt.tensor(
            constants.states[measurement_k["Projection 1"]],
            constants.states[measurement_k["Projection 2"]],
        )
        operator = pure_state * pure_state.dag()
        projection_operators.append(operator.full())
        coincidence_counts.append(measurement_k["Coincidences"])

    if resample:  # should only be used for bootstrapping
        coincidence_counts = [np.random.poisson(c) for c in coincidence_counts]

    # %%
    def get_projection_coincidence(data, proj1, proj2):
        # ATTN: ensure that the column names here are the same as when saving the experimental data
        tmp = (data["Projection 1"] == proj1) & (data["Projection 2"] == proj2)
        assert (
            sum(tmp) == 1
        )  # need to make sure there is only one row that applies this projection
        val = data.loc[tmp]["Coincidences"]
        return val.values[
            0
        ]  # pass back out just the coincidence value for the projection measurement

    # total number of counts (curly N in the paper)
    total_counts = sum(
        [
            get_projection_coincidence(data, proj1, proj2)
            for (proj1, proj2) in [("H", "H"), ("V", "V"), ("H", "V"), ("V", "H")]
        ]
    )

    # %%
    num_parameters = 16
    t_initial = np.random.uniform(0, 1, num_parameters)

    def make_physical_density_matrix(t):
        T = np.array(
            [
                [t[0], 0, 0, 0],
                [t[4] + 1j * t[5], t[1], 0, 0],
                [t[10] + 1j * t[11], t[6] + 1j * t[7], t[2], 0],
                [t[14] + 1j * t[15], t[12] + 1j * t[13], t[8] + 1j * t[9], t[3]],
            ]
        )
        rho_p = np.conjugate(T.T) @ T
        rho_p = rho_p / np.trace(rho_p)
        return rho_p

    # %%
    def maximum_likelihood_error(
        t, total_counts, projection_operators, coincidence_counts
    ):
        rho_p = make_physical_density_matrix(t)
        ell = 0.0  # initialize a variable for the likelihood term and iterate over each measurement, adding to it
        for i in range(16):
            expect = np.real(
                total_counts * np.trace(np.matmul(rho_p, projection_operators[i]))
            )
            ell += (expect - coincidence_counts[i]) ** 2 / (2 * expect)
        return ell

    # %% Minimize the likelihood
    # Check out scipy minimize documentation to see what you can pull from the result.
    res = minimize(
        maximum_likelihood_error,
        t_initial,
        method="Powell",
        args=(total_counts, projection_operators, coincidence_counts),
    )

    rho_opt = qt.Qobj(make_physical_density_matrix(res.x), dims=[[2, 2], [2, 2]])
    # print("\tMaximum likelihood estimation of the quantum state finished")

    # do comparison between the reconstructed state, rho_opt, and the target state
    if target is not None and verbose is True:
        print(f"Target state: {target}")

        if type(target) is str and target in ["phi+", "phi-", "psi+", "psi-"]:
            target = constants.states[
                target
            ]  # get QObj of the target state from definition of constants

        if type(target) is qt.Qobj:
            print(f"\tFidelity with target: {qt.fidelity(rho_opt, target)}")
            print(f"\tConcurrence: {qt.concurrence(rho_opt)}")
            print(f"\tLinear entropy: {qt.entropy_linear(rho_opt)}")

    return rho_opt, res


def bootstrap_two_qubit_state_tomography(
    n_bootstrap=100, data=None, target=None, verbose=False
):
    fids = []
    for b in range(n_bootstrap):
        rho_opt, res = two_qubit_state_tomography(
            data=data, target=target, resample=True, verbose=False
        )

        fids.append(qt.fidelity(rho_opt, target))
    np.array(fids)
    return fids


if __name__ == "__main__":

    from tqt.visualization.density_matrix import density_matrix_bars

    plt.close("all")

    io = IO(path=IO.default_path.joinpath("example_data"))
    data = io.load_dataframe("state_tomography_data.txt")

    fids = bootstrap_two_qubit_state_tomography(
        n_bootstrap=10, data=data, target=constants.states["psi+"]
    )
    print(fids)
