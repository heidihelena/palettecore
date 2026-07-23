# Perceptual and accessibility metrics — mirrors palettecore/metrics.py.

#' CIEDE2000 colour difference between two sRGB colours
#'
#' Computed via CIELAB under D65 (Sharma et al. 2005 formulation).
#'
#' @param rgb1,rgb2 Numeric vectors of length 3, sRGB channels in \[0, 1\].
#' @return CIEDE2000 distance (0 for identical colours, about 100 for black vs white).
#' @export
ciede2000 <- function(rgb1, rgb2) {
  lab1 <- srgb_to_cielab(rgb1)
  lab2 <- srgb_to_cielab(rgb2)
  L1 <- lab1[1]; a1 <- lab1[2]; b1 <- lab1[3]
  L2 <- lab2[1]; a2 <- lab2[2]; b2 <- lab2[3]

  C1 <- sqrt(a1^2 + b1^2)
  C2 <- sqrt(a2^2 + b2^2)
  C_bar <- (C1 + C2) / 2
  G <- 0.5 * (1 - sqrt(C_bar^7 / (C_bar^7 + 25^7)))
  a1p <- (1 + G) * a1
  a2p <- (1 + G) * a2
  C1p <- sqrt(a1p^2 + b1^2)
  C2p <- sqrt(a2p^2 + b2^2)

  hp <- function(a, b) {
    if (a == 0 && b == 0) return(0)
    (atan2(b, a) * 180 / pi) %% 360
  }
  h1p <- hp(a1p, b1)
  h2p <- hp(a2p, b2)

  dLp <- L2 - L1
  dCp <- C2p - C1p
  if (C1p * C2p == 0) {
    dhp <- 0
  } else {
    dd <- h2p - h1p
    if (dd > 180) dd <- dd - 360 else if (dd < -180) dd <- dd + 360
    dhp <- dd
  }
  dHp <- 2 * sqrt(C1p * C2p) * sin((dhp * pi / 180) / 2)

  Lp_bar <- (L1 + L2) / 2
  Cp_bar <- (C1p + C2p) / 2
  if (C1p * C2p == 0) {
    hp_bar <- h1p + h2p
  } else {
    dd <- abs(h1p - h2p)
    ss <- h1p + h2p
    if (dd <= 180) {
      hp_bar <- ss / 2
    } else if (ss < 360) {
      hp_bar <- (ss + 360) / 2
    } else {
      hp_bar <- (ss - 360) / 2
    }
  }

  rad <- function(x) x * pi / 180
  T_ <- 1 - 0.17 * cos(rad(hp_bar - 30)) + 0.24 * cos(rad(2 * hp_bar)) +
    0.32 * cos(rad(3 * hp_bar + 6)) - 0.20 * cos(rad(4 * hp_bar - 63))
  d_theta <- 30 * exp(-(((hp_bar - 275) / 25)^2))
  R_C <- 2 * sqrt(Cp_bar^7 / (Cp_bar^7 + 25^7))
  S_L <- 1 + 0.015 * (Lp_bar - 50)^2 / sqrt(20 + (Lp_bar - 50)^2)
  S_C <- 1 + 0.045 * Cp_bar
  S_H <- 1 + 0.015 * Cp_bar * T_
  R_T <- -sin(rad(2 * d_theta)) * R_C

  sqrt((dLp / S_L)^2 + (dCp / S_C)^2 + (dHp / S_H)^2 +
    R_T * (dCp / S_C) * (dHp / S_H))
}

relative_luminance <- function(rgb) {
  lin <- srgb_to_linear(rgb)
  0.2126 * lin[1] + 0.7152 * lin[2] + 0.0722 * lin[3]
}

#' WCAG 2.x contrast ratio between two sRGB colours
#'
#' @param rgb1,rgb2 Numeric vectors of length 3, sRGB channels in \[0, 1\].
#' @return Contrast ratio between 1 and 21.
#' @export
contrast_ratio <- function(rgb1, rgb2) {
  y1 <- relative_luminance(rgb1)
  y2 <- relative_luminance(rgb2)
  (max(y1, y2) + 0.05) / (min(y1, y2) + 0.05)
}

greyscale_values <- function(rgbs) {
  apply(rgbs, 1, relative_luminance)
}

is_monotonic <- function(values, tol = 1e-4) {
  d <- diff(values)
  all(d <= tol) || all(d >= -tol)
}
