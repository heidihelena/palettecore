# Palette generation and audit — mirrors palettecore/generate.py.
#
# Deterministic: no random state anywhere. Thresholds are package-default
# design rules, not established accessibility cut-offs.

DEFAULT_THRESHOLDS <- list(
  normal = 8.0,
  protanopia = 6.0,
  deuteranopia = 6.0,
  tritanopia = 6.0
)

.sequential_path <- function(seed_lch, n, background_rgb, samples = 512L) {
  C_seed <- seed_lch[2]
  H_seed <- seed_lch[3]

  bg_is_light <- mean(background_rgb) > 0.5
  if (bg_is_light) {
    L_hi <- 0.955; L_lo <- 0.30
  } else {
    L_hi <- 0.90; L_lo <- 0.22
  }

  t <- seq(0, 1, length.out = samples)
  L <- L_hi + (L_lo - L_hi) * t
  envelope <- sin(pi * pmin(pmax(t * 0.82 + 0.09, 0), 1))^0.8
  C_target <- C_seed * (0.25 + 0.95 * envelope)

  rgbs <- matrix(0, nrow = samples, ncol = 3)
  for (i in seq_len(samples)) {
    c_max <- max_chroma(L[i], H_seed)
    cc <- min(C_target[i], c_max)
    rgbs[i, ] <- .clip01(oklab_to_srgb(oklch_to_oklab(c(L[i], cc, H_seed))))
  }

  d <- numeric(samples)
  for (i in 2:samples) {
    d[i] <- d[i - 1] + ciede2000(rgbs[i - 1, ], rgbs[i, ])
  }
  targets <- seq(0, d[samples], length.out = n)
  idx <- vapply(targets, function(x) which.min(abs(d - x)), integer(1))
  rgbs[idx, , drop = FALSE]
}

.categorical <- function(seed_lch, n) {
  L_seed <- seed_lch[1]; C_seed <- seed_lch[2]; H_seed <- seed_lch[3]
  L_band <- min(max(L_seed, 0.55), 0.78)

  hues <- seq(0, 356, by = 4)
  levels <- c(L_band - 0.06, L_band, L_band + 0.06)
  cand_list <- list()
  k <- 0L
  for (h in hues) {
    for (L in levels) {
      cc <- min(max(C_seed, 0.09), max_chroma(L, h)) * 0.92
      k <- k + 1L
      cand_list[[k]] <- .clip01(oklab_to_srgb(oklch_to_oklab(c(L, cc, h))))
    }
  }
  candidates <- do.call(rbind, cand_list)

  seed_rgb <- .clip01(oklab_to_srgb(oklch_to_oklab(c(L_seed, C_seed, H_seed))))
  chosen <- list(seed_rgb)

  score <- function(cand, current) {
    s <- Inf
    for (x in current) {
      s <- min(s, ciede2000(cand, x))
      for (cond in CVD_CONDITIONS) {
        s <- min(s, ciede2000(simulate_cvd(cand, cond), simulate_cvd(x, cond)))
      }
    }
    s
  }

  while (length(chosen) < n) {
    scores <- vapply(
      seq_len(nrow(candidates)),
      function(i) score(candidates[i, ], chosen),
      numeric(1)
    )
    chosen[[length(chosen) + 1L]] <- candidates[which.max(scores), ]
  }

  sub_idx <- seq(1, nrow(candidates), by = 3)
  for (pass in 1:2) {
    for (i in 2:n) {
      rest <- chosen[-i]
      best_rgb <- chosen[[i]]
      best_s <- score(chosen[[i]], rest)
      for (j in sub_idx) {
        s <- score(candidates[j, ], rest)
        if (s > best_s) {
          best_rgb <- candidates[j, ]
          best_s <- s
        }
      }
      chosen[[i]] <- best_rgb
    }
  }

  do.call(rbind, chosen)
}

.diverging <- function(seed_lch, n, background_rgb) {
  L <- seed_lch[1]; C <- seed_lch[2]; H <- seed_lch[3]
  opp <- c(L, C, (H + 180) %% 360)
  half <- (n + 1L) %/% 2L
  a <- .sequential_path(seed_lch, half, background_rgb)
  b <- .sequential_path(opp, half, background_rgb)
  rev_b <- b[half:1, , drop = FALSE]
  if (n %% 2L == 1L) {
    rbind(rev_b[1:(half - 1), , drop = FALSE], a)
  } else {
    rbind(
      rev_b[1:(n %/% 2L), , drop = FALSE],
      a[(half - n %/% 2L + 1L):half, , drop = FALSE]
    )
  }
}

.audit <- function(rgbs, kind, background_rgb, use, thresholds) {
  n <- nrow(rgbs)
  diag <- list()
  warnings <- character(0)

  sims <- lapply(CVD_CONDITIONS, function(cond) {
    t(apply(rgbs, 1, simulate_cvd, condition = cond))
  })
  names(sims) <- CVD_CONDITIONS

  if (kind %in% c("sequential", "diverging")) {
    adjacent <- list(
      normal = vapply(1:(n - 1), function(i) ciede2000(rgbs[i, ], rgbs[i + 1, ]), numeric(1))
    )
    for (cond in CVD_CONDITIONS) {
      adjacent[[cond]] <- vapply(
        1:(n - 1),
        function(i) ciede2000(sims[[cond]][i, ], sims[[cond]][i + 1, ]),
        numeric(1)
      )
    }
    diag$adjacent_deltaE <- lapply(adjacent, function(v) round(v, 1))
    diag$min_adjacent_deltaE <- lapply(adjacent, function(v) round(min(v), 1))
    for (cond in names(thresholds)) {
      if (min(adjacent[[cond]]) < thresholds[[cond]]) {
        warnings <- c(warnings, sprintf(
          "%s: minimum adjacent dE %.1f is below the %.0f threshold - adjacent classes may merge for some readers.",
          cond, min(adjacent[[cond]]), thresholds[[cond]]
        ))
      }
    }
  } else {
    pairwise <- c(list(normal = Inf), stats::setNames(as.list(rep(Inf, length(CVD_CONDITIONS))), CVD_CONDITIONS))
    for (i in 1:(n - 1)) {
      for (j in (i + 1):n) {
        pairwise$normal <- min(pairwise$normal, ciede2000(rgbs[i, ], rgbs[j, ]))
        for (cond in CVD_CONDITIONS) {
          pairwise[[cond]] <- min(pairwise[[cond]], ciede2000(sims[[cond]][i, ], sims[[cond]][j, ]))
        }
      }
    }
    diag$min_pairwise_deltaE <- lapply(pairwise, function(v) round(v, 1))
    for (cond in names(thresholds)) {
      if (pairwise[[cond]] < thresholds[[cond]]) {
        warnings <- c(warnings, sprintf(
          "%s: minimum pairwise dE %.1f is below the %.0f threshold - pair categories with shape or direct labels.",
          cond, pairwise[[cond]], thresholds[[cond]]
        ))
      }
    }
  }

  grey <- greyscale_values(rgbs)
  diag$greyscale_luminance <- round(grey, 3)
  if (kind == "sequential") {
    diag$lightness_monotonic <- is_monotonic(grey)
    if (!is_monotonic(grey)) {
      warnings <- c(warnings, "Greyscale luminance is not monotonic - order is lost in print.")
    }
  } else if (kind == "categorical") {
    spread <- max(grey) - min(grey)
    diag$greyscale_spread <- round(spread, 3)
    if (spread > 0.45) {
      warnings <- c(warnings, "Large lightness spread - one category may look more important than others.")
    }
  }

  contrasts <- round(apply(rgbs, 1, contrast_ratio, rgb2 = background_rgb), 2)
  diag$contrast_vs_background <- contrasts
  if (use == "text") {
    bad <- which(contrasts < 4.5)
    if (length(bad) > 0) {
      warnings <- c(warnings, sprintf(
        "Swatches %s fall below WCAG AA 4.5:1 for normal text on this background.",
        paste(bad, collapse = ", ")
      ))
    }
  } else if (use %in% c("line", "UI")) {
    bad <- which(contrasts < 3.0)
    if (length(bad) > 0) {
      warnings <- c(warnings, sprintf(
        "Swatches %s fall below 3:1 against the background - thin marks may vanish.",
        paste(bad, collapse = ", ")
      ))
    }
  }

  diag$srgb_gamut <- "all in gamut (chroma clamped where needed)"
  excursions <- lapply(CVD_CONDITIONS, function(cond) {
    round(max(apply(rgbs, 1, out_of_gamut_excursion, condition = cond)), 4)
  })
  names(excursions) <- CVD_CONDITIONS
  diag$cvd_gamut <- list(
    policy = "distances measured after clamping simulated colours to displayable sRGB - the colour a viewer actually sees",
    max_linear_excursion_before_clamp = excursions
  )
  diag$thresholds_used <- c(thresholds, list(
    note = "package-default design rules (or user overrides), not established accessibility cut-offs"
  ))

  list(diagnostics = diag, warnings = warnings)
}

#' Generate an audited palette from one seed colour
#'
#' @param seed Seed colour as HEX, e.g. "#8B6FC9".
#' @param n Number of colours (2-24).
#' @param kind "sequential", "diverging" or "categorical".
#' @param background Intended background as HEX.
#' @param use "data_fill", "text", "line" or "UI".
#' @param thresholds Named list overriding the default dE floors.
#' @param anchor "path" or "exact" (categorical always contains the seed).
#' @return List with hexes, diagnostics and warnings.
#' @export
generate_palette <- function(seed, n = 8L, kind = "sequential",
                             background = "#FFFFFF", use = "data_fill",
                             thresholds = NULL, anchor = "path") {
  if (!kind %in% c("sequential", "diverging", "categorical")) {
    stop(sprintf("Unknown palette kind: '%s'", kind))
  }
  if (!anchor %in% c("path", "exact")) {
    stop(sprintf("Unknown anchor policy: '%s'", anchor))
  }
  if (length(n) != 1 || is.na(n) || n != as.integer(n) || n < 2 || n > 24) {
    stop(sprintf("n must be an integer between 2 and 24, got %s", n))
  }
  n <- as.integer(n)

  th <- utils::modifyList(DEFAULT_THRESHOLDS, as.list(thresholds %||% list()))
  seed_lch <- hex_to_oklch(seed)
  background_rgb <- hex_to_srgb(background)

  rgbs <- switch(kind,
    sequential = .sequential_path(seed_lch, n, background_rgb),
    diverging = .diverging(seed_lch, n, background_rgb),
    categorical = .categorical(seed_lch, n)
  )

  seed_rgb <- hex_to_srgb(seed)
  if (kind == "sequential" && anchor == "exact") {
    dists <- apply(rgbs, 1, ciede2000, rgb2 = seed_rgb)
    rgbs[which.min(dists), ] <- seed_rgb
  }

  audit <- .audit(rgbs, kind, background_rgb, use, th)
  diag <- audit$diagnostics
  warnings <- audit$warnings
  diag$anchor <- if (kind == "categorical") "exact" else anchor
  diag$seed_nearest_stop_deltaE <- round(min(apply(rgbs, 1, ciede2000, rgb2 = seed_rgb)), 1)

  if (kind == "diverging") {
    warnings <- c(warnings, paste(
      "Diverging second pole derived as seed hue + 180 deg - a design assumption,",
      "not implied by the seed. Override by generating from the other pole too."
    ))
  }
  if (seed_lch[2] < 0.02) {
    warnings <- c(warnings, "Seed is near-neutral - hue is poorly defined; family hue is arbitrary.")
  }

  structure(
    list(
      hexes = apply(rgbs, 1, srgb_to_hex),
      kind = kind,
      seed = toupper(if (startsWith(seed, "#")) seed else paste0("#", seed)),
      background = background,
      use = use,
      diagnostics = diag,
      warnings = warnings
    ),
    class = "palettecore_result"
  )
}

`%||%` <- function(a, b) if (is.null(a)) b else a

#' @export
print.palettecore_result <- function(x, ...) {
  cat(x$kind, "palette from", x$seed, "\n")
  cat(paste(x$hexes, collapse = " "), "\n")
  for (w in x$warnings) cat("WARNING:", w, "\n")
  invisible(x)
}
