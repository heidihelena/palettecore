# Categorical palette from one seed, checked for a colour-blind reader.
#
# Reproduces the two-panel demo figure: a categorical cancer-incidence-style
# bar chart coloured with palettecore, shown as most readers see it and under
# simulated deuteranopia. The counts are illustrative, not real registry data.
#
#   install.packages("palettecore", repos = "https://heidihelena.r-universe.dev")

library(palettecore)
library(ggplot2)

seed <- "#B57EDC"   # lavender awareness colour; any chroma->=0.12 seed works

# Audit before you trust it: generate_palette() carries its own diagnostics.
pal <- generate_palette(seed, n = 8, kind = "categorical")
print(pal$warnings)                       # character(0) here = nothing flagged

df <- data.frame(
  type  = c("Breast","Prostate","Colorectal","Lung","Melanoma","Bladder","Kidney","Pancreas"),
  cases = c(5200, 5000, 3300, 2600, 1900, 1300, 1000, 1300)
)
df$type <- factor(df$type, levels = df$type[order(-df$cases)])

# What most readers see: one line does it, and audit warnings surface as R warnings.
ggplot(df, aes(type, cases, fill = type)) +
  geom_col(width = 0.72) +
  scale_fill_accessible(seed) +
  labs(x = NULL, y = "New cases per year (illustrative)") +
  theme_minimal(base_size = 13) +
  theme(legend.position = "none")

# What a reader with deuteranopia sees: simulate each fill, plot with identity.
sim <- vapply(pal$hexes, function(h) srgb_to_hex(simulate_cvd(hex_to_srgb(h), "deuteranopia")), "")
df$fill <- sim[as.integer(df$type)]
ggplot(df, aes(type, cases, fill = fill)) +
  geom_col(width = 0.72) +
  scale_fill_identity() +
  labs(x = NULL, y = "New cases per year (illustrative)",
       title = "Simulated deuteranopia: the categories still separate") +
  theme_minimal(base_size = 13)
