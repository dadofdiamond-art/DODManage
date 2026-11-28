(function () {
  "use strict";

  function entry(size, carat) {
    const str = String(carat).trim();
    const parts = str.split("-").map((p) => parseFloat(p.trim()));
    const min = parts[0];
    const max = parts.length > 1 && !Number.isNaN(parts[1]) ? parts[1] : min;
    return {
      size: String(size).trim(),
      carat: str,
      caratMin: min,
      caratMax: max,
      caratMid: (min + max) / 2
    };
  }

  const STONE_SIZE_CHART = {
    "Round": [
      entry("0.7", "0.001"), entry("0.8", "0.002"), entry("0.9", "0.003"),
      entry("1", "0.004"), entry("1.1", "0.006"), entry("1.2", "0.007"),
      entry("1.3", "0.01"), entry("1.4", "0.011"), entry("1.5", "0.014"),
      entry("1.6", "0.018"), entry("1.7", "0.021"), entry("1.8", "0.024"),
      entry("1.9", "0.025"), entry("2", "0.032"), entry("2.1", "0.035"),
      entry("2.2", "0.043"), entry("2.3", "0.047"), entry("2.4", "0.055"),
      entry("2.5", "0.058"), entry("2.6", "0.066"), entry("2.7", "0.076"),
      entry("2.8", "0.083"), entry("2.9", "0.09"), entry("3", "0.1"),
      entry("3.1", "0.12"), entry("3.2", "0.13"), entry("3.3", "0.14"),
      entry("3.4", "0.15"), entry("3.5", "0.16"), entry("3.6", "0.17"),
      entry("3.7", "0.18"), entry("3.8", "0.19"), entry("3.9", "0.2"),
      entry("4", "0.22"), entry("4.1", "0.26"), entry("4.25", "0.27"),
      entry("4.5", "0.33"), entry("4.75", "0.4"), entry("5", "0.42"),
      entry("5.5", "0.59"), entry("5.8", "0.65-0.70"), entry("6", "0.75"),
      entry("6.5", "0.80-0.90"), entry("7", "1.15-1.22"), entry("7.5", "1.40-1.45"),
      entry("8", "1.74-1.80"), entry("8.3", "1.95-2.10"), entry("8.5", "2.16-2.20"),
      entry("9", "2.45-2.50"), entry("9.5", "2.90-3.0"), entry("10", "3.47"),
      entry("10.5", "4.06"), entry("11", "4.67"), entry("11.5", "4.95-5.10"),
      entry("12", "6.08"), entry("13", "7.56"), entry("14", "9.81"),
      entry("15", "11.78"), entry("16", "14.41"), entry("17", "17"),
      entry("18", "19.85"), entry("19", "23.5"), entry("20", "27.17")
    ],
    "Baguette": [
      entry("1x1.25", "0.01"), entry("1x1.75", "0.01"), entry("1x2", "0.01"),
      entry("1x2.25", "0.02"), entry("1x2.75", "0.02"), entry("1x3", "0.03"),
      entry("1.25x1.5", "0.02"), entry("1.25x2", "0.02"), entry("1.25x2.5", "0.02"),
      entry("1.25x3", "0.03"), entry("1.25x4", "0.04"), entry("1.5x1.75", "0.02"),
      entry("1.5x2", "0.03"), entry("1.5x2.25", "0.03"), entry("1.5x2.5", "0.04"),
      entry("1.5x3", "0.04"), entry("1.5x3.5", "0.06"), entry("1.5x4", "0.070"),
      entry("1.5x4.5", "0.08"), entry("1.75x2", "0.03"), entry("1.75x2.5", "0.05"),
      entry("1.75x3", "0.05"), entry("2x2.5", "0.060"), entry("2x3", "0.070"),
      entry("2x3.5", "0.09"), entry("2x4", "0.11"), entry("2x4.5", "0.1"),
      entry("2x5", "0.13"), entry("2.5x3", "0.12"), entry("2.5x4", "0.16"),
      entry("2.5x5", "0.22"), entry("3x4", "0.22"), entry("3x5", "0.28"),
      entry("3x6", "0.33"), entry("4x6", "0.58"), entry("5x10", "1.71")
    ],
    "Oval": [
      entry("2X3", "0.06"), entry("2X4", "0.09"), entry("3X4", "0.17"),
      entry("3X5", "0.21"), entry("4x5", "0.36"), entry("4X6", "0.43"),
      entry("5X7", "0.82"), entry("6X8", "1.25"), entry("6X9", "1.45"),
      entry("7X9", "1.90"), entry("7X10", "2.10"), entry("7x11", "2.35"),
      entry("8X10", "2.79"), entry("8X11", "3.08"), entry("8X12", "3.40"),
      entry("9X11", "3.79"), entry("9X12", "4.28"), entry("9x13", "4.7"),
      entry("10X12", "5.05"), entry("10X14", "6.10")
    ],
    "Emerald": [
      entry("1.5x3", "0.04"), entry("2X3", "0.07"), entry("2X4", "0.10"),
      entry("3x4", "0.21"), entry("3X5", "0.28"), entry("4x5", "0.45"),
      entry("4X6", "0.6"), entry("5X7", "0.98"), entry("6X8", "1.60"),
      entry("6x9", "1.96"), entry("7X9", "2.32"), entry("7X10", "2.85"),
      entry("7x11", "3.2"), entry("8X10", "3.60"), entry("8X11", "4.13"),
      entry("8X12", "4.65"), entry("9X11", "4.80"), entry("9X12", "5.50"),
      entry("9x13", "6.00"), entry("10x12", "6.60"), entry("10X14", "8.2"),
      entry("12X14", "10.83"), entry("12X16", "12.36")
    ],
    "Triangle": [
      entry("3", "0.11"), entry("3.5", "0.13"), entry("4", "0.21"),
      entry("4.5", "0.29"), entry("5", "0.4"), entry("5.5", "0.5"),
      entry("6", "0.70"), entry("6.5", "0.92"), entry("7", "1.14"),
      entry("7.5", "1.43"), entry("8", "1.60"), entry("8.5", "1.90"),
      entry("9", "2.25"), entry("9.5", "2.68"), entry("10", "3.23")
    ],
    "Trillion": [
      entry("3", "0.10"), entry("3.5", "0.16"), entry("4", "0.24"),
      entry("4.5", "0.34"), entry("5", "0.48"), entry("5.5", "0.62"),
      entry("6", "0.81"), entry("6.5", "1.07"), entry("7", "1.32"),
      entry("7.5", "1.44"), entry("8", "1.81"), entry("8.5", "2.06"),
      entry("9", "2.70"), entry("9.5", "2.82"), entry("10", "3.27")
    ],
    "E. Cushion": [
      entry("4x6", "0.5"), entry("5x7", "0.9"), entry("6X8", "1.22"),
      entry("7X9", "1.93"), entry("8X10", "2.75"), entry("8x12", "3.60"),
      entry("9X11", "3.94"), entry("9X12", "5.22"), entry("10x12", "5.23")
    ],
    "Radiant": [
      entry("2x3", "0.06"), entry("2x4", "0.1"), entry("3X4", "0.2"),
      entry("3x5", "0.25"), entry("4x5", "0.44"), entry("4X6", "0.5"),
      entry("5X7", "1.00"), entry("6X8", "1.67"), entry("6x9", "1.85"),
      entry("7X9", "2.43"), entry("7X10", "2.72"), entry("7x11", "3.10"),
      entry("8X10", "3.5"), entry("8x11", "4"), entry("8X12", "4.3"),
      entry("9X11", "5.00"), entry("9X12", "5.45"), entry("9x13", "5.91"),
      entry("10X12", "6.34"), entry("10x14", "8.00")
    ],
    "Marquise": [
      entry("1.5x2.5", "0.02"), entry("1.5X3", "0.04"), entry("2x3", "0.05"),
      entry("2x3.5", "0.06"), entry("2X4", "0.08"), entry("2.5X4", "0.1"),
      entry("2.5X4.5", "0.13"), entry("2.5X5", "0.15"), entry("3X5", "0.18"),
      entry("3X6", "0.20"), entry("3.5X7", "0.35"), entry("4X8", "0.47"),
      entry("4.5x9", "0.72"), entry("5X10", "1.0"), entry("5.5x11", "1.3"),
      entry("6X12", "1.67"), entry("6.5X13", "2.10"), entry("7X14", "2.70"),
      entry("7.5x15", "3.35"), entry("8x16", "4"), entry("9x18", "5.7"),
      entry("10x12", "7.7")
    ],
    "Cushion": [
      entry("2", "0.04"), entry("2.5", "0.08"), entry("3X3", "0.12"),
      entry("3.5X3.5", "0.19"), entry("4X4", "0.3"), entry("4.5X4.5", "0.42"),
      entry("5X5", "0.60"), entry("5.5X5.5", "0.80"), entry("6X6", "1.00"),
      entry("6.5X6.5", "1.30"), entry("7X7", "1.73"), entry("7.5X7.5", "2.9"),
      entry("8X8", "2.40"), entry("8.5X8.5", "2.94"), entry("9X9", "3.50"),
      entry("9.5X9.5", "4.08"), entry("10X10", "4.87"), entry("10.5", "5.20"),
      entry("11X11", "6.34"), entry("12X12", "7.65")
    ],
    "Tapper": [
      entry("1x1.25x1.5", "0.01"), entry("1x1.5x1.75", "0.02"), entry("1x1.5x2", "0.02"),
      entry("1x1.5x2.5", "0.03"), entry("1x1.5x3", "0.030"), entry("1x1.5x3.5", "0.04"),
      entry("1x2x3", "0.05"), entry("1.5x2x2.5", "0.050"), entry("1.5x2x3", "0.06"),
      entry("1.5x2x3", "0.08"), entry("1.5x2x4", "0.10"), entry("1.5x2.5x4", "0.12"),
      entry("1.5x2.5x5", "0.17"), entry("2x2.5x5", "0.17"), entry("2x3x4", "0.17"),
      entry("2x3x5", "0.24"), entry("2x3x6", "0.27"), entry("2.5x3x5", "0.3"),
      entry("2.5x4x5", "0.17"), entry("2x4x5", "0.33"), entry("3x3.5x6", "0.50")
    ],
    "Asscher": [
      entry("2", "0.04"), entry("2.5", "0.08"), entry("3", "0.14"),
      entry("3.5", "0.23"), entry("4", "0.33"), entry("4.5", "0.49"),
      entry("5", "0.7"), entry("5.5", "0.88"), entry("6", "1.22"),
      entry("6.5", "1.5"), entry("7", "1.93"), entry("7.5", "2.35"),
      entry("8", "2.74"), entry("8.5", "3.15"), entry("9", "3.95"),
      entry("9.5", "4.5"), entry("10", "5.5"), entry("11", "6.98"),
      entry("12", "9.3")
    ],
    "Princess": [
      entry("1.3", "0.01"), entry("1.5", "0.02"), entry("1.75", "0.03"),
      entry("2X2", "0.05"), entry("2.5X2.5", "0.1"), entry("3X3", "0.2"),
      entry("3.5X3.5", "0.3"), entry("4X4", "0.37"), entry("4.5X4.5", "0.51"),
      entry("5X5", "0.67"), entry("5.5X5.5", "0.94"), entry("6X6", "1.18"),
      entry("6.5X6.5", "1.4"), entry("7X7", "1.94"), entry("7.5X7.5", "2.28"),
      entry("8X8", "2.78"), entry("8.5X8.5", "3.49"), entry("9X9", "3.94"),
      entry("9.5X9.5", "4.44"), entry("10X10", "5.47"), entry("11X11", "7.14"),
      entry("12X12", "9.5")
    ],
    "Heart": [
      entry("2x2", "0.03"), entry("2.5x2.5", "0.06"), entry("3X3", "0.10"),
      entry("3.5X3.5", "0.15"), entry("4X4", "0.24"), entry("4.5X4.5", "0.4"),
      entry("5X5", "0.47"), entry("5.5X5.5", "0.65"), entry("6X6", "0.9"),
      entry("6.5X6.5", "1.03"), entry("7X7", "1.3"), entry("7.5X7.5", "1.60"),
      entry("8X8", "1.88"), entry("8.5X8.5", "2.30"), entry("9X9", "2.74"),
      entry("9.5X9.5", "3.10"), entry("10X10", "3.6"), entry("10.5x10.5", "4.0"),
      entry("11X11", "4.56"), entry("11.5X11.5", "4.95"), entry("12X12", "6.4"),
      entry("12.5X12.5", "6.85"), entry("13X13", "8.4")
    ],
    "Pear": [
      entry("3X1.5", "0.033"), entry("2X3", "0.05"), entry("2X4", "0.08"),
      entry("2.5x3", "0.08"), entry("2.5x3.5", "0.09"), entry("2.5X4", "0.10"),
      entry("3.5x4.5", "0.22"), entry("3X4", "0.1"), entry("3X5", "0.20"),
      entry("4x5", "0.31"), entry("4X6", "0.4"), entry("5X7", "0.69"),
      entry("5X8", "0.85"), entry("6X8", "1.13"), entry("6X9", "1.29"),
      entry("7X9", "1.60"), entry("7X10", "1.87"), entry("7X11", "2.10"),
      entry("8X10", "2.5"), entry("8X11", "2.62"), entry("8X12", "2.95"),
      entry("9X11", "3.30"), entry("9X12", "3.60"), entry("9X13", "4.00"),
      entry("10X14", "5.30"), entry("10x15", "5.68")
    ]
  };

  function lookupStoneSizeByCarat(shape, totalCarat, quantity) {
    const rows = STONE_SIZE_CHART[shape];
    if (!rows || !rows.length) return null;
    const match = String(totalCarat || "").match(/(\d+(?:\.\d+)?)/);
    if (!match) return null;
    const total = parseFloat(match[1]);
    if (Number.isNaN(total) || total <= 0) return null;
    const qty = Math.max(1, parseInt(quantity, 10) || 1);
    const perStone = total / qty;

    // Exact range match first
    for (const item of rows) {
      if (perStone >= item.caratMin && perStone <= item.caratMax) {
        return item;
      }
    }
    // Nearest match
    let best = rows[0];
    let bestDiff = Math.abs(perStone - best.caratMid);
    for (const item of rows) {
      const diff = Math.abs(perStone - item.caratMid);
      if (diff < bestDiff) {
        best = item;
        bestDiff = diff;
      }
    }
    return best;
  }

  window.DOD_STONE_CHART = STONE_SIZE_CHART;
  window.lookupStoneSizeByCarat = lookupStoneSizeByCarat;
})();
