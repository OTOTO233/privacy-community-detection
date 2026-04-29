from __future__ import annotations

import matplotlib.pyplot as plt


SONGTI_SMALL_FIVE_PT = 16


def apply_songti_small5() -> None:
    plt.rcParams["font.family"] = ["SimSun"]
    plt.rcParams["font.sans-serif"] = ["SimSun"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = SONGTI_SMALL_FIVE_PT
    plt.rcParams["axes.titlesize"] = SONGTI_SMALL_FIVE_PT
    plt.rcParams["axes.labelsize"] = SONGTI_SMALL_FIVE_PT
    plt.rcParams["xtick.labelsize"] = SONGTI_SMALL_FIVE_PT
    plt.rcParams["ytick.labelsize"] = SONGTI_SMALL_FIVE_PT
    plt.rcParams["legend.fontsize"] = SONGTI_SMALL_FIVE_PT
    plt.rcParams["figure.titlesize"] = SONGTI_SMALL_FIVE_PT
