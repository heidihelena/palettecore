# Colour space conversions: hex, sRGB, linear RGB, XYZ, CIELAB, OKLab, OKLCH.
#
# Mirrors the Python reference implementation (palettecore/convert.py) —
# validated against fixtures/parity.json. sRGB is interpreted under D65
# throughout; no chromatic adaptation to any other white point occurs.

.cbrt <- function(x) sign(x) * abs(x)^(1 / 3)
.clip01 <- function(x) pmin(pmax(x, 0), 1)

hex_to_srgb <- function(hex_str) {
  s <- sub("^#", "", trimws(hex_str))
  if (nchar(s) == 3) s <- paste0(strsplit(s, "")[[1]], strsplit(s, "")[[1]], collapse = "")
  if (nchar(s) != 6 || grepl("[^0-9A-Fa-f]", s)) {
    stop(sprintf("Not a HEX colour: '%s'", hex_str))
  }
  vapply(c(1, 3, 5), function(i) strtoi(substr(s, i, i + 1), 16L) / 255, numeric(1))
}

srgb_to_hex <- function(rgb) {
  v <- as.integer(round(.clip01(rgb) * 255))
  sprintf("#%02X%02X%02X", v[1], v[2], v[3])
}

srgb_to_linear <- function(rgb) {
  ifelse(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055)^2.4)
}

linear_to_srgb <- function(lin) {
  lin <- pmax(lin, 0)
  ifelse(lin <= 0.0031308, lin * 12.92, 1.055 * lin^(1 / 2.4) - 0.055)
}

.M1 <- matrix(c(
  0.4122214708, 0.5363325363, 0.0514459929,
  0.2119034982, 0.6806995451, 0.1073969566,
  0.0883024619, 0.2817188376, 0.6299787005
), nrow = 3, byrow = TRUE)
.M2 <- matrix(c(
  0.2104542553, 0.7936177850, -0.0040720468,
  1.9779984951, -2.4285922050, 0.4505937099,
  0.0259040371, 0.7827717662, -0.8086757660
), nrow = 3, byrow = TRUE)
.M1_inv <- solve(.M1)
.M2_inv <- solve(.M2)

linear_to_oklab <- function(lin) {
  as.vector(.M2 %*% .cbrt(.M1 %*% lin))
}

oklab_to_linear <- function(lab) {
  as.vector(.M1_inv %*% ((.M2_inv %*% lab)^3))
}

srgb_to_oklab <- function(rgb) linear_to_oklab(srgb_to_linear(rgb))
oklab_to_srgb <- function(lab) linear_to_srgb(oklab_to_linear(lab))

oklab_to_oklch <- function(lab) {
  h <- (atan2(lab[3], lab[2]) * 180 / pi) %% 360
  c(lab[1], sqrt(lab[2]^2 + lab[3]^2), h)
}

oklch_to_oklab <- function(lch) {
  h <- lch[3] * pi / 180
  c(lch[1], lch[2] * cos(h), lch[2] * sin(h))
}

hex_to_oklch <- function(hex_str) oklab_to_oklch(srgb_to_oklab(hex_to_srgb(hex_str)))
oklch_to_hex <- function(lch) srgb_to_hex(oklab_to_srgb(oklch_to_oklab(lch)))

.M_XYZ <- matrix(c(
  0.4124564, 0.3575761, 0.1804375,
  0.2126729, 0.7151522, 0.0721750,
  0.0193339, 0.1191920, 0.9503041
), nrow = 3, byrow = TRUE)
.WHITE_D65 <- c(0.95047, 1.00000, 1.08883)

srgb_to_cielab <- function(rgb) {
  xyz <- as.vector(.M_XYZ %*% srgb_to_linear(rgb))
  t <- xyz / .WHITE_D65
  delta <- 6 / 29
  f <- ifelse(t > delta^3, .cbrt(t), t / (3 * delta^2) + 4 / 29)
  c(116 * f[2] - 16, 500 * (f[1] - f[2]), 200 * (f[2] - f[3]))
}

in_srgb_gamut <- function(lch, eps = 1e-6) {
  lin <- oklab_to_linear(oklch_to_oklab(lch))
  all(lin >= -eps & lin <= 1 + eps)
}

max_chroma <- function(L, H, c_hi = 0.4, tol = 1e-4) {
  if (!in_srgb_gamut(c(L, 0, H))) return(0)
  lo <- 0
  hi <- c_hi
  while (hi - lo > tol) {
    mid <- (lo + hi) / 2
    if (in_srgb_gamut(c(L, mid, H))) lo <- mid else hi <- mid
  }
  lo
}
