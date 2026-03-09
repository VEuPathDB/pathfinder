export interface DistributionEntry {
  value: string;
  count: number;
}

export interface ColumnHistogramBin {
  value: number;
  binStart: string;
  binEnd: string;
  binLabel: string;
}
