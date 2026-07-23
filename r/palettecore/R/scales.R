# ggplot2 scales. ggplot2 is in Suggests - these error clearly without it.

#' Discrete colour scale from an audited palettecore palette
#'
#' Generates the palette with generate_palette() and surfaces its audit
#' warnings via warning(), so an inaccessible combination never passes
#' silently into a figure.
#'
#' @param seed Seed colour as HEX.
#' @param kind Palette kind; "categorical" is the usual choice for discrete scales.
#' @param ... Passed to generate_palette() (background, use, thresholds, ...).
#' @export
scale_colour_accessible <- function(seed, kind = "categorical", ...) {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("scale_colour_accessible() requires ggplot2")
  }
  args <- list(...)
  ggplot2::discrete_scale(
    aesthetics = "colour",
    palette = function(n) {
      r <- do.call(generate_palette, c(list(seed = seed, n = n, kind = kind), args))
      for (w in r$warnings) warning(w, call. = FALSE)
      r$hexes
    }
  )
}

#' @rdname scale_colour_accessible
#' @export
scale_color_accessible <- scale_colour_accessible

#' Discrete fill scale from an audited palettecore palette
#'
#' @inheritParams scale_colour_accessible
#' @export
scale_fill_accessible <- function(seed, kind = "categorical", ...) {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("scale_fill_accessible() requires ggplot2")
  }
  args <- list(...)
  ggplot2::discrete_scale(
    aesthetics = "fill",
    palette = function(n) {
      r <- do.call(generate_palette, c(list(seed = seed, n = n, kind = kind), args))
      for (w in r$warnings) warning(w, call. = FALSE)
      r$hexes
    }
  )
}
