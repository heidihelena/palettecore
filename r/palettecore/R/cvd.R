# Colour-vision deficiency simulation — mirrors palettecore/cvd.py.
#
# Machado, Oliveira & Fernandes (2009) matrices at severity 1.0 on the
# paper's [0, 1] scale (complete dichromacy; anomalous trichromacy is not
# modelled). Simulated colours are clamped channel-wise in linear RGB —
# the clamped colour is what a display shows. Matrices used as published;
# no fixture-level parity with other packages has been established.

MACHADO_10 <- list(
  protanopia = matrix(c(
    0.152286, 1.052583, -0.204868,
    0.114503, 0.786281, 0.099216,
    -0.003882, -0.048116, 1.051998
  ), nrow = 3, byrow = TRUE),
  deuteranopia = matrix(c(
    0.367322, 0.860646, -0.227968,
    0.280085, 0.672501, 0.047413,
    -0.011820, 0.042940, 0.968881
  ), nrow = 3, byrow = TRUE),
  tritanopia = matrix(c(
    1.255528, -0.076749, -0.178779,
    -0.078411, 0.930809, 0.147602,
    0.004733, 0.691367, 0.303900
  ), nrow = 3, byrow = TRUE)
)

CVD_CONDITIONS <- names(MACHADO_10)

.simulate_linear <- function(rgb, condition) {
  as.vector(MACHADO_10[[condition]] %*% srgb_to_linear(rgb))
}

#' Simulate colour-vision deficiency (complete dichromacy)
#'
#' Machado et al. (2009) matrices at severity 1.0 on the paper's \[0, 1\]
#' scale, applied in linear RGB and clamped to the displayable range.
#'
#' @param rgb Numeric vector of length 3, sRGB channels in \[0, 1\].
#' @param condition One of "protanopia", "deuteranopia", "tritanopia".
#' @return Simulated sRGB colour, clamped to \[0, 1\].
#' @export
simulate_cvd <- function(rgb, condition) {
  lin <- .clip01(.simulate_linear(rgb, condition))
  .clip01(linear_to_srgb(lin))
}

#' Pre-clamp gamut excursion of a CVD simulation
#'
#' Largest linear-RGB excursion outside \[0, 1\] before clamping. 0 means the
#' simulated colour was displayable as-is; larger values mean clamping
#' altered the colour and measured separations involving it should be read
#' with that in mind.
#'
#' @inheritParams simulate_cvd
#' @return Non-negative excursion magnitude in linear RGB.
#' @export
out_of_gamut_excursion <- function(rgb, condition) {
  lin <- .simulate_linear(rgb, condition)
  max(0, max(lin - 1), max(-lin))
}
