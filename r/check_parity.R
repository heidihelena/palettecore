# Cross-language parity check: R implementation vs fixtures/parity.json
# (written by the Python reference). Conversions and distances must match
# within the fixture tolerance; palette HEX codes must match exactly.
#
# Run from the repo root:  Rscript r/check_parity.R

for (f in list.files("r/palettecore/R", pattern = "\\.R$", full.names = TRUE)) source(f)

fx <- jsonlite::fromJSON("fixtures/parity.json", simplifyVector = FALSE)
tol <- fx$tolerance$float
fails <- 0L
max_dev <- 0

check <- function(label, got, want) {
  dev <- max(abs(unlist(got) - unlist(want)))
  max_dev <<- max(max_dev, dev)
  if (dev > tol) {
    cat(sprintf("FAIL %s: max deviation %.3g > %.1g\n", label, dev, tol))
    fails <<- fails + 1L
  }
}

for (cv in fx$conversions) {
  rgb <- hex_to_srgb(cv$hex)
  check(paste("srgb", cv$hex), rgb, cv$srgb)
  lab <- srgb_to_oklab(rgb)
  check(paste("oklab", cv$hex), lab, cv$oklab)
  check(paste("oklch", cv$hex), oklab_to_oklch(lab), cv$oklch)
  check(paste("cielab", cv$hex), srgb_to_cielab(rgb), cv$cielab_d65)
}

for (pr in fx$ciede2000) {
  check(
    paste("dE", pr$a, pr$b),
    ciede2000(hex_to_srgb(pr$a), hex_to_srgb(pr$b)),
    pr$deltaE
  )
}

for (cv in fx$cvd) {
  for (cond in CVD_CONDITIONS) {
    check(paste("cvd", cond, cv$hex), simulate_cvd(hex_to_srgb(cv$hex), cond), cv[[cond]])
  }
}

for (ct in fx$contrast) {
  check(paste("contrast/W", ct$hex), contrast_ratio(hex_to_srgb(ct$hex), hex_to_srgb("#FFFFFF")), ct$vs_white)
  check(paste("contrast/B", ct$hex), contrast_ratio(hex_to_srgb(ct$hex), hex_to_srgb("#000000")), ct$vs_black)
}

pal_fail <- 0L
for (pl in fx$palettes) {
  spec <- pl$spec
  r <- do.call(generate_palette, spec)
  want <- unlist(pl$hexes)
  label <- paste0(spec$seed, "/", spec$kind, "/n", spec$n,
                  if (!is.null(spec$anchor)) paste0("/", spec$anchor) else "",
                  if (!is.null(spec$background)) paste0("/bg", spec$background) else "")
  if (!identical(unname(r$hexes), want)) {
    diff_i <- which(r$hexes != want)
    cat(sprintf("FAIL palette %s: %d/%d stops differ (%s)\n",
                label, length(diff_i), length(want),
                paste(sprintf("%d: R %s vs Py %s", diff_i, r$hexes[diff_i], want[diff_i]), collapse = "; ")))
    pal_fail <- pal_fail + 1L
  }
  if (length(r$warnings) != pl$warnings_count) {
    cat(sprintf("FAIL palette %s: %d warnings vs %d in fixture\n",
                label, length(r$warnings), pl$warnings_count))
    pal_fail <- pal_fail + 1L
  }
}

cat(sprintf(
  "\nNumeric checks: %s (max deviation %.3g, tolerance %.1g)\nPalette checks: %d/%d specs matched exactly\n",
  if (fails == 0) "PASS" else sprintf("%d FAILURES", fails),
  max_dev, tol,
  length(fx$palettes) - pal_fail, length(fx$palettes)
))
if (fails + pal_fail > 0) quit(status = 1)
cat("PARITY PASS\n")
