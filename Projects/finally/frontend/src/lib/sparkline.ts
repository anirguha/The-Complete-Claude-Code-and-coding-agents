/** SVG polyline points for a series, scaled to fit width x height with padding. */
export function sparklinePoints(values: number[], width: number, height: number, pad = 2): string {
  if (values.length < 2) return "";
  let min = Infinity;
  let max = -Infinity;
  for (const v of values) {
    if (v < min) min = v;
    if (v > max) max = v;
  }
  const range = max - min;
  const stepX = width / (values.length - 1);
  const usable = height - pad * 2;
  return values
    .map((v, i) => {
      const y = range === 0 ? height / 2 : pad + usable * (1 - (v - min) / range);
      return `${(i * stepX).toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}
